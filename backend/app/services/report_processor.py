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

        # Use 2-prompt approach for reliability with timeout protection
        # AI analysis fails completely if this times out (not optional)
        try:
            coding_result = await asyncio.wait_for(
                openai_service.analyze_clinical_note_v2(
                    clinical_note=clinical_text_for_coding,
                    billed_codes=billed_codes_for_llm,
                    extracted_icd10_codes=extracted_icd10_for_llm,
                    snomed_to_cpt_suggestions=snomed_cpt_for_llm,
                    encounter_type=encounter_type
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

        await prisma.report.update(
            where={"id": report_id},
            data={
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
        )

        logger.info(
            "Report processing completed successfully",
            report_id=report_id,
            processing_time_ms=processing_time_ms,
            suggested_codes_count=len(coding_result.suggested_codes),
            incremental_revenue=coding_result.total_incremental_revenue
        )

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
