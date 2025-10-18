"""
Async Report Processing Service
Handles background processing of encounter reports through the FHIR coding intelligence pipeline
"""

from typing import Optional, Dict, Any
import structlog
from datetime import datetime
import traceback
import asyncio

from app.core.database import prisma
from app.services.comprehend_medical import comprehend_medical_service
from app.services.phi_handler import phi_handler
from app.services.openai_service import openai_service
from app.services.snomed_crosswalk import get_crosswalk_service
from app.utils.icd10_filtering import get_diagnosis_entities, filter_icd10_codes, deduplicate_icd10_codes
from prisma import enums

logger = structlog.get_logger(__name__)

# Timeout constants (in seconds)
OPENAI_TIMEOUT = 120  # 2 minutes for AI analysis
COMPREHEND_TIMEOUT = 60  # 1 minute for AWS Comprehend Medical


async def update_report_progress(
    report_id: str,
    progress_percent: int,
    current_step: str
) -> None:
    """
    Update report processing progress in database

    Args:
        report_id: Report ID
        progress_percent: Current progress (0-100)
        current_step: Current processing step name
    """
    try:
        await prisma.report.update(
            where={"id": report_id},
            data={
                "progressPercent": progress_percent,
                "currentStep": current_step,
            }
        )
        logger.info(
            "Report progress updated",
            report_id=report_id,
            progress_percent=progress_percent,
            current_step=current_step
        )
    except Exception as e:
        logger.error(
            "Failed to update report progress",
            report_id=report_id,
            error=str(e)
        )


async def process_report_async(report_id: str, max_retries: int = 3) -> None:
    """
    Background task to process encounter and generate report

    Executes the full FHIR coding intelligence pipeline:
    1. PHI Detection & De-identification (0-20%)
    2. Clinical Relevance Filtering (20-40%)
    3. Code Inference (ICD-10 + SNOMED) (40-70%)
    4. AI Coding Analysis (2-prompt approach) (70-100%)
    5. Finalize Report

    Args:
        report_id: Report ID to process
        max_retries: Maximum retry attempts on failure (default: 3)

    Raises:
        Exception: If processing fails after max retries
    """
    start_time = datetime.now()

    try:
        # Mark as PROCESSING
        await prisma.report.update(
            where={"id": report_id},
            data={
                "status": enums.ReportStatus.PROCESSING,
                "processingStartedAt": start_time,
                "progressPercent": 0,
                "currentStep": "initializing"
            }
        )

        logger.info("Starting async report processing", report_id=report_id)

        # Fetch report with encounter data
        report = await prisma.report.find_unique(
            where={"id": report_id},
            include={
                "encounter": {
                    "include": {
                        "uploadedFiles": True,
                        "billingCodes": True,
                        "phiMapping": True
                    }
                }
            }
        )

        if not report:
            raise ValueError(f"Report {report_id} not found")

        encounter = report.encounter
        if not encounter:
            raise ValueError(f"Encounter not found for report {report_id}")

        # Get PHI mapping (should already exist from initial upload)
        phi_mapping = encounter.phiMapping
        if not phi_mapping:
            raise ValueError(f"PHI mapping not found for encounter {encounter.id}")

        deidentified_text = phi_mapping.deidentifiedText

        # ================================================================
        # STEP 1: PHI DETECTION (Already done, just update progress)
        # ================================================================
        await update_report_progress(report_id, 10, "phi_detection")
        logger.info("PHI detection step", report_id=report_id, phi_detected=phi_mapping.phiDetected)
        await update_report_progress(report_id, 20, "phi_detection_complete")

        # ================================================================
        # STEP 2: CLINICAL RELEVANCE FILTERING (20-40%)
        # ================================================================
        await update_report_progress(report_id, 30, "clinical_filtering")

        clinical_text_for_coding = deidentified_text
        encounter_type = None

        try:
            # Add timeout protection to prevent hanging
            filtering_result = await asyncio.wait_for(
                openai_service.filter_clinical_relevance(deidentified_text=deidentified_text),
                timeout=OPENAI_TIMEOUT
            )

            clinical_text_for_coding = filtering_result.get("filtered_text", deidentified_text)
            encounter_type = filtering_result.get("encounter_type")

            logger.info(
                "Clinical filtering complete",
                report_id=report_id,
                original_length=len(deidentified_text),
                filtered_length=len(clinical_text_for_coding),
                reduction_pct=filtering_result.get("reduction_pct", 0)
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Clinical filtering timed out, using full deidentified text",
                report_id=report_id,
                timeout_seconds=OPENAI_TIMEOUT
            )
            clinical_text_for_coding = deidentified_text
        except Exception as e:
            logger.warning(
                "Clinical filtering failed, using full deidentified text",
                report_id=report_id,
                error=str(e)
            )
            # Graceful degradation: use full text if filtering fails
            clinical_text_for_coding = deidentified_text

        await update_report_progress(report_id, 40, "clinical_filtering_complete")

        # ================================================================
        # STEP 3: CODE INFERENCE (40-70%)
        # ================================================================
        await update_report_progress(report_id, 50, "icd10_inference")

        deduplicated_icd10 = []
        snomed_entities = []

        try:
            # ICD-10 Code Inference with timeout protection
            icd10_entities = await asyncio.wait_for(
                asyncio.to_thread(comprehend_medical_service.infer_icd10_cm, clinical_text_for_coding),
                timeout=COMPREHEND_TIMEOUT
            )

            # Get medical entities for filtering with timeout protection
            medical_entities = await asyncio.wait_for(
                asyncio.to_thread(comprehend_medical_service.detect_entities_v2, clinical_text_for_coding),
                timeout=COMPREHEND_TIMEOUT
            )
            diagnosis_entities = get_diagnosis_entities(medical_entities)

            # Filter ICD-10 codes using diagnosis entities
            filtered_icd10, filter_stats = filter_icd10_codes(
                icd10_entities=icd10_entities,
                diagnosis_entities=diagnosis_entities,
                min_match_score=0.6
            )
            deduplicated_icd10 = deduplicate_icd10_codes(filtered_icd10)

            logger.info(
                "ICD-10 inference complete",
                report_id=report_id,
                total_codes=len(icd10_entities),
                filtered_codes=len(deduplicated_icd10)
            )
        except asyncio.TimeoutError:
            logger.warning(
                "ICD-10 inference timed out, continuing without extracted codes",
                report_id=report_id,
                timeout_seconds=COMPREHEND_TIMEOUT
            )
        except Exception as e:
            logger.warning(
                "ICD-10 inference failed, continuing without extracted codes",
                report_id=report_id,
                error=str(e)
            )
            # Graceful degradation: continue without ICD-10 codes

        await update_report_progress(report_id, 60, "snomed_inference")

        try:
            # SNOMED Code Inference with timeout protection
            snomed_entities = await asyncio.wait_for(
                asyncio.to_thread(comprehend_medical_service.infer_snomed_ct, clinical_text_for_coding),
                timeout=COMPREHEND_TIMEOUT
            )

            logger.info(
                "SNOMED inference complete",
                report_id=report_id,
                total_codes=len(snomed_entities)
            )
        except asyncio.TimeoutError:
            logger.warning(
                "SNOMED inference timed out, continuing without SNOMED codes",
                report_id=report_id,
                timeout_seconds=COMPREHEND_TIMEOUT
            )
        except Exception as e:
            logger.warning(
                "SNOMED inference failed, continuing without SNOMED codes",
                report_id=report_id,
                error=str(e)
            )
            # Graceful degradation: continue without SNOMED codes

        await update_report_progress(report_id, 70, "code_inference_complete")

        # ================================================================
        # STEP 4: PREPARE DATA FOR AI ANALYSIS
        # ================================================================

        # Get billed codes from encounter
        billing_codes = await prisma.billingcode.find_many(
            where={"encounterId": encounter.id}
        )

        billed_codes_for_llm = [
            {
                "code": bc.code,
                "code_type": bc.codeType,
                "description": bc.description or ""
            }
            for bc in billing_codes
        ]

        # Prepare extracted ICD-10 codes for LLM
        extracted_icd10_for_llm = [
            {
                "code": e.code,
                "description": e.description,
                "score": e.score
            }
            for e in deduplicated_icd10
        ] if deduplicated_icd10 else []

        # SNOMED to CPT suggestions (if crosswalk available)
        # For now, passing empty list as crosswalk is optional
        snomed_cpt_for_llm = []

        # ================================================================
        # STEP 5: AI CODING ANALYSIS (70-100%)
        # ================================================================
        await update_report_progress(report_id, 80, "ai_coding_analysis")

        # NEW: Get payer-specific fee schedule rates before AI analysis
        payer_rates = {}
        payer_id = encounter.payerId

        if payer_id:
            try:
                from app.services.fee_schedule_service import get_fee_schedule_service

                fee_schedule_service = await get_fee_schedule_service(prisma)

                # Get all CPT codes that might be suggested
                all_cpt_codes = []

                # Add codes from SNOMED crosswalk
                if snomed_cpt_for_llm:
                    all_cpt_codes.extend([s['cpt_code'] for s in snomed_cpt_for_llm])

                # Add codes from billed codes
                all_cpt_codes.extend([c['code'] for c in billed_codes_for_llm if c['code_type'] == 'CPT'])

                # Deduplicate
                all_cpt_codes = list(set(all_cpt_codes))

                if all_cpt_codes:
                    # Batch lookup rates
                    payer_rates = await fee_schedule_service.get_rates_batch(
                        cpt_codes=all_cpt_codes,
                        payer_id=payer_id
                    )

                    logger.info(
                        "Payer rates loaded for AI analysis",
                        report_id=report_id,
                        payer_id=payer_id,
                        total_codes=len(all_cpt_codes),
                        rates_found=sum(1 for r in payer_rates.values() if r is not None)
                    )
            except Exception as e:
                logger.warning(
                    "Failed to load payer rates",
                    report_id=report_id,
                    error=str(e)
                )

        # Use 2-prompt approach for reliability with timeout protection
        # AI analysis fails completely if this times out (not optional)
        try:
            coding_result = await asyncio.wait_for(
                openai_service.analyze_clinical_note(
                    clinical_note=clinical_text_for_coding,
                    billed_codes=billed_codes_for_llm,
                    extracted_icd10_codes=extracted_icd10_for_llm,
                    snomed_to_cpt_suggestions=snomed_cpt_for_llm,
                    encounter_type=encounter_type,
                    payer_rates=payer_rates if payer_rates else None
                ),
                timeout=OPENAI_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise Exception(f"AI coding analysis timed out after {OPENAI_TIMEOUT} seconds")

        logger.info(
            "AI coding analysis complete",
            report_id=report_id,
            suggested_codes=len(coding_result.suggested_codes),
            additional_codes=len(coding_result.additional_codes),
            tokens_used=coding_result.tokens_used,
            cost_usd=coding_result.cost_usd
        )

        await update_report_progress(report_id, 90, "ai_quality_analysis")

        logger.info(
            "AI quality analysis complete",
            report_id=report_id
        )

        # ================================================================
        # STEP 5.5: PAYER-SPECIFIC REVENUE BREAKDOWN (NEW)
        # ================================================================
        billed_revenue_estimate = 0.0
        suggested_revenue_estimate = 0.0
        optimized_revenue_estimate = 0.0
        auth_requirements = []
        denial_risks = []
        bundling_warnings = []

        if payer_id and payer_rates:
            try:
                logger.info(
                    "Calculating payer-specific revenue breakdown",
                    report_id=report_id,
                    payer_id=payer_id
                )

                # Calculate revenue for billed codes
                for billed_code in coding_result.billed_codes:
                    if billed_code.code_type == 'CPT':
                        rate = payer_rates.get(billed_code.code)
                        if rate:
                            # Use non-facility rate as primary, fall back to allowed amount
                            reimbursement = rate.non_facility_rate or rate.allowed_amount
                            billed_revenue_estimate += reimbursement

                            # Track authorization requirements
                            if rate.requires_auth:
                                auth_requirements.append({
                                    'code': billed_code.code,
                                    'description': billed_code.description,
                                    'criteria': rate.auth_criteria,
                                    'code_type': 'billed'
                                })

                # Calculate revenue for suggested codes (missing/additional codes from AI)
                for suggested_code in coding_result.suggested_codes:
                    if suggested_code.code_type == 'CPT':
                        rate = payer_rates.get(suggested_code.code)
                        if rate:
                            reimbursement = rate.non_facility_rate or rate.allowed_amount
                            suggested_revenue_estimate += reimbursement

                            # Track authorization requirements
                            if rate.requires_auth:
                                auth_requirements.append({
                                    'code': suggested_code.code,
                                    'description': suggested_code.description,
                                    'criteria': rate.auth_criteria,
                                    'code_type': 'suggested',
                                    'reasoning': suggested_code.reasoning
                                })

                # Calculate revenue for additional codes (upgrade opportunities)
                for additional_code in coding_result.additional_codes:
                    if additional_code.code_type == 'CPT':
                        rate = payer_rates.get(additional_code.code)
                        if rate:
                            reimbursement = rate.non_facility_rate or rate.allowed_amount
                            optimized_revenue_estimate += reimbursement

                            # Track authorization requirements
                            if rate.requires_auth:
                                auth_requirements.append({
                                    'code': additional_code.code,
                                    'description': additional_code.description,
                                    'criteria': rate.auth_criteria,
                                    'code_type': 'additional',
                                    'reasoning': additional_code.reasoning
                                })

                # Analyze denial risks
                # Check for codes without rates (payer may not cover)
                all_suggested_cpt = [c.code for c in coding_result.suggested_codes if c.code_type == 'CPT']
                all_suggested_cpt.extend([c.code for c in coding_result.additional_codes if c.code_type == 'CPT'])

                for code in all_suggested_cpt:
                    if code not in payer_rates or payer_rates[code] is None:
                        denial_risks.append({
                            'code': code,
                            'risk_type': 'no_rate_on_file',
                            'message': f'No reimbursement rate found for code {code}',
                            'severity': 'high'
                        })

                # Identify potential bundling issues
                # Note: Full NCCI edit checking is a future enhancement
                # For now, flag codes that may have bundling concerns based on rate data
                for code in all_suggested_cpt:
                    rate = payer_rates.get(code)
                    if rate and rate.bundling_rules:
                        bundling_warnings.append({
                            'code': code,
                            'warning': 'Bundling rules may apply',
                            'rules': rate.bundling_rules
                        })

                logger.info(
                    "Revenue breakdown calculated",
                    report_id=report_id,
                    billed_revenue=billed_revenue_estimate,
                    suggested_revenue=suggested_revenue_estimate,
                    optimized_revenue=optimized_revenue_estimate,
                    auth_requirements_count=len(auth_requirements),
                    denial_risks_count=len(denial_risks)
                )

            except Exception as e:
                logger.warning(
                    "Failed to calculate revenue breakdown",
                    report_id=report_id,
                    error=str(e)
                )
                # Non-critical, continue with report finalization

        # ================================================================
        # STEP 6: FINALIZE REPORT (90-100%)
        # ================================================================
        await update_report_progress(report_id, 95, "finalizing_report")

        # Calculate processing time
        processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Prepare data for database
        suggested_codes_json = [c.to_dict() for c in coding_result.suggested_codes]
        additional_codes_json = [c.to_dict() for c in coding_result.additional_codes]
        billed_codes_json = [c.to_dict() for c in coding_result.billed_codes]

        # Merge per-code revenue from RVU analysis into suggested codes
        if coding_result.rvu_analysis and coding_result.rvu_analysis.get("suggested_code_details"):
            rvu_details = coding_result.rvu_analysis["suggested_code_details"]
            # Create a lookup map by code
            rvu_map = {detail["code"]: detail["rvus"] for detail in rvu_details}

            # Add revenue_impact to each suggested code
            for code_dict in suggested_codes_json:
                code_value = code_dict.get("code")
                if code_value in rvu_map:
                    code_dict["revenue_impact"] = rvu_map[code_value]
                else:
                    code_dict["revenue_impact"] = 0.0

        extracted_icd10_json = [
            {
                "code": e.code,
                "description": e.description,
                "score": e.score,
                "category": e.category.value if hasattr(e.category, 'value') else str(e.category),
                "text": e.text
            }
            for e in deduplicated_icd10
        ] if deduplicated_icd10 else []

        extracted_snomed_json = [
            {
                "code": e.code,
                "description": e.description,
                "score": e.score,
                "category": e.category.value if hasattr(e.category, 'value') else str(e.category)
            }
            for e in snomed_entities
        ] if snomed_entities else []

        # Update report with complete results
        from prisma import Json

        # Prepare update data with base fields
        update_data = {
            "status": enums.ReportStatus.COMPLETE,
            "processingCompletedAt": datetime.now(),
            "processingTimeMs": processing_time_ms,
            "progressPercent": 100,
            "currentStep": "complete",
            "suggestedCodes": Json(suggested_codes_json),
            "billedCodes": Json(billed_codes_json),
            "extractedIcd10Codes": Json(extracted_icd10_json),
            "extractedSnomedCodes": Json(extracted_snomed_json),
            "incrementalRevenue": coding_result.total_incremental_revenue,
            "aiModel": coding_result.model_used,
            "confidenceScore": None,  # Can calculate average confidence if needed
        }

        # Add payer-specific revenue fields if available
        if payer_id:
            update_data["payerId"] = payer_id

        if payer_rates:
            update_data["billedRevenueEstimate"] = billed_revenue_estimate
            update_data["suggestedRevenueEstimate"] = suggested_revenue_estimate
            update_data["optimizedRevenueEstimate"] = optimized_revenue_estimate

            # Store authorization requirements, denial risks, and bundling warnings as JSON
            if auth_requirements:
                update_data["authRequirements"] = Json(auth_requirements)
            if denial_risks:
                update_data["payerDenialRisks"] = Json(denial_risks)
            if bundling_warnings:
                update_data["bundlingWarnings"] = Json(bundling_warnings)

        await prisma.report.update(
            where={"id": report_id},
            data=update_data
        )

        # Build comprehensive success log
        log_data = {
            "report_id": report_id,
            "processing_time_ms": processing_time_ms,
            "suggested_codes_count": len(coding_result.suggested_codes),
            "incremental_revenue": coding_result.total_incremental_revenue
        }

        # Add payer-specific metrics if available
        if payer_rates:
            log_data.update({
                "billed_revenue": billed_revenue_estimate,
                "suggested_revenue": suggested_revenue_estimate,
                "optimized_revenue": optimized_revenue_estimate,
                "total_revenue_opportunity": billed_revenue_estimate + suggested_revenue_estimate + optimized_revenue_estimate,
                "auth_requirements_count": len(auth_requirements),
                "denial_risks_count": len(denial_risks),
                "bundling_warnings_count": len(bundling_warnings)
            })

        logger.info("Report processing completed successfully", **log_data)

    except Exception as e:
        # Handle errors
        error_message = str(e)
        error_details = {
            "type": type(e).__name__,
            "message": error_message,
            "traceback": traceback.format_exc()
        }

        logger.error(
            "Report processing failed",
            report_id=report_id,
            error=error_message,
            error_type=type(e).__name__
        )

        # Get current retry count
        current_report = await prisma.report.find_unique(where={"id": report_id})
        retry_count = current_report.retryCount if current_report else 0

        # Update report with error
        from prisma import Json

        await prisma.report.update(
            where={"id": report_id},
            data={
                "status": enums.ReportStatus.FAILED,
                "errorMessage": error_message[:500],  # Truncate long messages
                "errorDetails": Json(error_details),
                "retryCount": retry_count + 1,
            }
        )

        # Retry if under max retries
        if retry_count < max_retries:
            retry_delay = 2 ** retry_count  # Exponential backoff: 1s, 2s, 4s
            logger.info(
                "Retrying report processing",
                report_id=report_id,
                retry_count=retry_count + 1,
                max_retries=max_retries,
                retry_delay_seconds=retry_delay
            )
            await asyncio.sleep(retry_delay)
            await process_report_async(report_id, max_retries)
        else:
            logger.error(
                "Report processing failed after max retries",
                report_id=report_id,
                retry_count=retry_count,
                max_retries=max_retries
            )
            raise
