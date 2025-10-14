"""
PHI Processing Background Tasks
Handles asynchronous PHI detection, redaction, and file deletion for HIPAA compliance
"""

from typing import Optional
import structlog
from datetime import datetime

from app.core.database import prisma
from app.core.storage import storage_service
from app.core.audit import create_audit_log
from app.services.comprehend_medical import comprehend_medical_service
from app.services.phi_handler import phi_handler
from app.services.openai_service import OpenAIService
from app.services.snomed_crosswalk import get_crosswalk_service
from app.utils.text_extraction import extract_text
from app.utils.icd10_filtering import get_diagnosis_entities, filter_icd10_codes, deduplicate_icd10_codes
from app.services.task_queue import queue_report_processing
from prisma import enums

logger = structlog.get_logger(__name__)


async def process_encounter_phi(encounter_id: str) -> None:
    """
    Background task to process PHI in uploaded clinical notes

    HIPAA-compliant workflow:
    1. Fetch encounter and uploaded file
    2. Download original file from S3
    3. Extract text from file
    4. Detect PHI using Amazon Comprehend Medical
    5. Redact PHI and create de-identified text
    6. Store redacted text in PhiMapping (encrypted)
    7. Delete original file from S3 (HIPAA requirement)
    8. Update encounter status to COMPLETED

    Args:
        encounter_id: Encounter ID to process

    Raises:
        Exception: If any step fails, encounter status is set to FAILED
    """
    processing_start_time = datetime.utcnow()

    try:
        logger.info("Starting PHI processing", encounter_id=encounter_id)

        # Update encounter status to PROCESSING
        await prisma.encounter.update(
            where={"id": encounter_id},
            data={
                "status": enums.EncounterStatus.PROCESSING,
                "processingStartedAt": processing_start_time,
            }
        )

        # Audit log: PHI processing started
        await create_audit_log(
            action="PHI_PROCESSING_STARTED",
            user_id=None,  # Will get from encounter after fetch
            resource_type="Encounter",
            resource_id=encounter_id,
            metadata={"processing_start_time": processing_start_time.isoformat()},
        )

        # Step 1: Fetch encounter and uploaded file
        encounter = await prisma.encounter.find_unique(
            where={"id": encounter_id},
            include={"uploadedFiles": True, "user": True}
        )

        if not encounter:
            raise ValueError(f"Encounter not found: {encounter_id}")

        if not encounter.uploadedFiles or len(encounter.uploadedFiles) == 0:
            raise ValueError(f"No uploaded files found for encounter: {encounter_id}")

        # Get the first uploaded file (clinical note)
        uploaded_file = encounter.uploadedFiles[0]
        file_path = uploaded_file.filePath

        logger.info(
            "Encounter and file retrieved",
            encounter_id=encounter_id,
            file_path=file_path,
            user_id=encounter.userId
        )

        # Step 2: Get extracted text (either from database or S3)
        if uploaded_file.extractedText:
            # Use pre-extracted text from database
            extracted_text = uploaded_file.extractedText
            logger.info("Using pre-extracted text from database", text_length=len(extracted_text))
        else:
            # Download file from S3 and extract text
            logger.info("Downloading file from S3", file_path=file_path)
            file_content = await storage_service.download_file(file_path)

            # Extract text from file
            file_ext = uploaded_file.fileName.split('.')[-1].lower()
            logger.info("Extracting text from downloaded file", file_type=file_ext, file_size=len(file_content))

            extracted_text = extract_text(file_content, file_ext)

            if not extracted_text or len(extracted_text) < 10:
                raise ValueError(f"Extracted text is too short or empty: {len(extracted_text)} chars")

            logger.info("Text extracted successfully", text_length=len(extracted_text))

        # Step 4-6: Detect PHI, redact, and store in PhiMapping
        logger.info("Detecting and de-identifying PHI", encounter_id=encounter_id)

        result = await phi_handler.process_clinical_note(
            encounter_id=encounter_id,
            clinical_text=extracted_text,
            user_id=encounter.userId
        )

        logger.info(
            "PHI processing completed",
            encounter_id=encounter_id,
            phi_detected=result.phi_detected,
            phi_count=len(result.phi_entities)
        )

        # Audit log: PHI detected
        await create_audit_log(
            action="PHI_DETECTED",
            user_id=encounter.userId,
            resource_type="PhiMapping",
            resource_id=encounter_id,
            metadata={
                "phi_detected": result.phi_detected,
                "phi_entity_count": len(result.phi_entities),
                "phi_types": [e.type for e in result.phi_entities] if result.phi_entities else [],
            },
        )

        # Step 6.05: Extract search/matching metadata
        logger.info("Extracting search metadata", encounter_id=encounter_id)

        # Calculate SHA-256 hash of filename
        import hashlib
        filename_hash = hashlib.sha256(uploaded_file.fileName.encode()).hexdigest()

        # Initialize metadata (will be set after clinical filtering)
        provider_initials = None
        date_of_service = None

        # Step 6.1: Filter for clinical relevance using GPT-4o-mini
        logger.info("Filtering text for clinical relevance", encounter_id=encounter_id)

        deidentified_text = result.deidentified_text
        filtering_result = None

        try:
            from app.services.openai_service import openai_service

            filtering_result = await openai_service.filter_clinical_relevance(
                deidentified_text=deidentified_text
            )

            # Use filtered text for subsequent processing
            clinical_text_for_coding = filtering_result["filtered_text"]

            # Extract provider and service date using placeholders identified by LLM
            provider_placeholder = filtering_result.get("provider_placeholder")
            service_date_placeholder = filtering_result.get("service_date_placeholder")

            if provider_placeholder:
                # Find the PHI mapping for this placeholder
                provider_mapping = next(
                    (m for m in result.phi_mappings if m.token == f"[{provider_placeholder}]"),
                    None
                )
                if provider_mapping:
                    # Extract initials from provider name
                    name_parts = provider_mapping.original.split()
                    if len(name_parts) >= 2:
                        initials = ''.join([part[0].upper() for part in name_parts[:2] if part])
                        if initials and len(initials) >= 2:
                            provider_initials = initials
                            logger.info("Provider extracted from LLM placeholder", placeholder=provider_placeholder, name=provider_mapping.original, initials=provider_initials)

            if service_date_placeholder:
                # Find the PHI mapping for this placeholder
                date_mapping = next(
                    (m for m in result.phi_mappings if m.token == f"[{service_date_placeholder}]"),
                    None
                )
                if date_mapping:
                    # Parse the date
                    from dateutil import parser as date_parser
                    try:
                        parsed_date = date_parser.parse(date_mapping.original)
                        date_of_service = parsed_date
                        logger.info("Service date extracted from LLM placeholder", placeholder=service_date_placeholder, date_text=date_mapping.original, date=date_of_service.isoformat())
                    except Exception as e:
                        logger.warning("Failed to parse service date", date_text=date_mapping.original, error=str(e))

            logger.info(
                "Clinical relevance filtering completed",
                encounter_id=encounter_id,
                original_length=filtering_result["original_length"],
                filtered_length=filtering_result["filtered_length"],
                reduction_pct=filtering_result["reduction_pct"],
                provider_placeholder=provider_placeholder,
                service_date_placeholder=service_date_placeholder,
                provider_initials=provider_initials,
                date_of_service=date_of_service.isoformat() if date_of_service else None,
                tokens_used=filtering_result["tokens_used"],
                cost_usd=filtering_result["cost_usd"],
            )

        except Exception as e:
            logger.warning(
                "Clinical relevance filtering failed, using full deidentified text",
                encounter_id=encounter_id,
                error=str(e)
            )
            # Fallback: use full deidentified text if filtering fails
            clinical_text_for_coding = deidentified_text

        # Step 6.3: Extract ICD-10 codes using Comprehend Medical
        logger.info("Extracting ICD-10 codes", encounter_id=encounter_id)

        icd10_entities = []
        try:
            icd10_entities = comprehend_medical_service.infer_icd10_cm(clinical_text_for_coding)
            logger.info(
                "ICD-10 codes extracted",
                encounter_id=encounter_id,
                icd10_code_count=len(icd10_entities)
            )

            # Store ICD-10 codes in database
            for entity in icd10_entities:
                try:
                    await prisma.icd10code.create(
                        data={
                            "encounterId": encounter_id,
                            "code": entity.code,
                            "description": entity.description,
                            "category": entity.category,
                            "type": entity.type,
                            "score": entity.score,
                            "beginOffset": entity.begin_offset,
                            "endOffset": entity.end_offset,
                            "text": entity.text,
                        }
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to store ICD-10 code",
                        encounter_id=encounter_id,
                        code=entity.code,
                        error=str(e)
                    )

            logger.info(
                "ICD-10 codes stored in database",
                encounter_id=encounter_id,
                stored_count=len(icd10_entities)
            )

        except Exception as e:
            logger.warning(
                "Failed to extract ICD-10 codes",
                encounter_id=encounter_id,
                error=str(e)
            )

        # Step 6.4: Extract SNOMED CT codes using Comprehend Medical
        logger.info("Extracting SNOMED CT codes", encounter_id=encounter_id)

        snomed_entities = []
        try:
            snomed_entities = comprehend_medical_service.infer_snomed_ct(clinical_text_for_coding)
            logger.info(
                "SNOMED CT codes extracted",
                encounter_id=encounter_id,
                snomed_code_count=len(snomed_entities)
            )

            # Store SNOMED codes in database
            for entity in snomed_entities:
                try:
                    await prisma.snomedcode.create(
                        data={
                            "encounterId": encounter_id,
                            "code": entity.code,
                            "description": entity.description,
                            "category": entity.category,
                            "type": entity.type,
                            "score": entity.score,
                            "beginOffset": entity.begin_offset,
                            "endOffset": entity.end_offset,
                            "text": entity.text,
                        }
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to store SNOMED code",
                        encounter_id=encounter_id,
                        code=entity.code,
                        error=str(e)
                    )

            logger.info(
                "SNOMED codes stored in database",
                encounter_id=encounter_id,
                stored_count=len(snomed_entities)
            )

        except Exception as e:
            logger.warning(
                "Failed to extract SNOMED CT codes",
                encounter_id=encounter_id,
                error=str(e)
            )

        # Step 6.45: Perform SNOMED to CPT crosswalk
        logger.info("Performing SNOMED to CPT crosswalk", encounter_id=encounter_id)

        cpt_suggestions_from_crosswalk = []
        try:
            if snomed_entities and medical_entities:
                # Get procedure entities from DetectEntitiesV2 (score > 0.5)
                from app.utils.icd10_filtering import get_procedure_entities, filter_snomed_codes

                procedure_entities = get_procedure_entities(
                    medical_entities,
                    min_score=0.5
                )

                logger.info(
                    "Procedure entities extracted from DetectEntitiesV2",
                    encounter_id=encounter_id,
                    procedure_entities_count=len(procedure_entities),
                    procedure_texts=[e.text for e in procedure_entities[:5]]  # Log first 5
                )

                # Filter SNOMED codes using fuzzy text matching
                filtered_snomed_entities, snomed_filter_stats = filter_snomed_codes(
                    snomed_entities=snomed_entities,
                    procedure_entities=procedure_entities,
                    min_match_score=0.5
                )

                logger.info(
                    "SNOMED codes filtered for crosswalk",
                    encounter_id=encounter_id,
                    **snomed_filter_stats
                )

                if filtered_snomed_entities:
                    # Get crosswalk service
                    crosswalk_service = await get_crosswalk_service(prisma)

                    # Extract unique SNOMED codes from filtered entities
                    snomed_codes = list(set([e.code for e in filtered_snomed_entities]))

                    # Batch lookup CPT mappings
                    crosswalk_results = await crosswalk_service.get_cpt_mappings_batch(
                        snomed_codes=snomed_codes,
                        min_confidence=0.5  # Include medium and high confidence mappings
                    )

                    # Convert to suggestion format for LLM
                    for snomed_code, mappings in crosswalk_results.items():
                        # Find the SNOMED entity for context (from filtered list)
                        snomed_entity = next((e for e in filtered_snomed_entities if e.code == snomed_code), None)

                        for mapping in mappings[:3]:  # Top 3 CPT codes per SNOMED code
                            cpt_suggestions_from_crosswalk.append({
                                "cpt_code": mapping.cpt_code,
                                "description": mapping.cpt_description,
                                "source": "SNOMED_CROSSWALK",
                                "confidence": mapping.confidence,
                                "mapping_type": mapping.mapping_type,
                                "snomed_code": snomed_code,
                                "snomed_description": mapping.snomed_description,
                                "snomed_text": snomed_entity.text if snomed_entity else None,
                                "aws_confidence": snomed_entity.score if snomed_entity else None,
                            })

                    logger.info(
                        "SNOMED to CPT crosswalk completed",
                        encounter_id=encounter_id,
                        snomed_codes_count=len(snomed_codes),
                        cpt_suggestions_count=len(cpt_suggestions_from_crosswalk)
                    )

                    # Log crosswalk metrics
                    metrics = crosswalk_service.get_metrics()
                    logger.info(
                        "crosswalk_service_metrics",
                        encounter_id=encounter_id,
                        **metrics
                    )
                else:
                    logger.info(
                        "No high-confidence SNOMED procedure codes for crosswalk",
                        encounter_id=encounter_id
                    )

        except Exception as e:
            logger.warning(
                "Failed to perform SNOMED to CPT crosswalk",
                encounter_id=encounter_id,
                error=str(e)
            )

        # Step 6.45: Extract additional medical entities (medications, tests, etc.)
        logger.info("Extracting additional medical entities", encounter_id=encounter_id)

        medical_entities = []
        try:
            medical_entities = comprehend_medical_service.detect_entities_v2(clinical_text_for_coding)

            # Group entities by category for logging
            entities_by_category = {}
            for entity in medical_entities:
                if entity.category not in entities_by_category:
                    entities_by_category[entity.category] = 0
                entities_by_category[entity.category] += 1

            logger.info(
                "Medical entities extracted",
                encounter_id=encounter_id,
                total_entity_count=len(medical_entities),
                entities_by_category=entities_by_category
            )
        except Exception as e:
            logger.warning(
                "Failed to extract medical entities",
                encounter_id=encounter_id,
                error=str(e)
            )

        # Step 6.5: Filter ICD-10 codes using diagnosis entities
        logger.info("Filtering ICD-10 codes using diagnosis entities", encounter_id=encounter_id)

        filtered_icd10_entities = icd10_entities  # Default to all if filtering fails
        try:
            if medical_entities and icd10_entities:
                # Extract diagnosis entities (DIAGNOSIS trait, no NEGATION)
                diagnosis_entities = get_diagnosis_entities(medical_entities)

                logger.info(
                    "Diagnosis entities extracted",
                    encounter_id=encounter_id,
                    diagnosis_count=len(diagnosis_entities),
                    diagnosis_texts=[e.text for e in diagnosis_entities]
                )

                # Filter ICD-10 codes to match diagnoses
                # Use 0.6 threshold to require strong text match (filters out weak correlations)
                filtered_icd10_entities, filter_stats = filter_icd10_codes(
                    icd10_entities=icd10_entities,
                    diagnosis_entities=diagnosis_entities,
                    min_match_score=0.6
                )

                # Deduplicate filtered codes
                filtered_icd10_entities = deduplicate_icd10_codes(filtered_icd10_entities)

                logger.info(
                    "ICD-10 codes filtered",
                    encounter_id=encounter_id,
                    **filter_stats,
                    final_count=len(filtered_icd10_entities)
                )
            else:
                logger.info(
                    "Skipping ICD-10 filtering (no entities or codes)",
                    encounter_id=encounter_id,
                    has_medical_entities=bool(medical_entities),
                    has_icd10_entities=bool(icd10_entities)
                )

        except Exception as e:
            logger.warning(
                "ICD-10 filtering failed, using all extracted codes",
                encounter_id=encounter_id,
                error=str(e)
            )

        logger.info("PHI processing and code extraction complete", encounter_id=encounter_id)

        # Step 6.6: Extract billed codes from clinical text (file upload workflow only)
        # For FHIR workflow, billed codes are extracted from Claims resources
        if encounter.encounterSource != enums.EncounterSource.FHIR:
            logger.info("Extracting billed codes from clinical text", encounter_id=encounter_id)

            try:
                from app.services.code_extraction import extract_billed_codes

                billed_codes = await extract_billed_codes(
                    clinical_text=extracted_text,  # Use original text (not de-identified)
                    encounter_id=encounter_id,
                    only_billed=True  # Only extract codes with "billed" context
                )

                # Store billed codes in BillingCode table
                for code_dict in billed_codes:
                    try:
                        await prisma.billingcode.create(
                            data={
                                "encounterId": encounter_id,
                                "code": code_dict["code"],
                                "codeType": code_dict["code_type"],
                                "description": code_dict.get("description"),
                                "source": "EXTRACTED_FROM_TEXT",
                            }
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to store billed code",
                            encounter_id=encounter_id,
                            code=code_dict["code"],
                            error=str(e)
                        )

                logger.info(
                    "Billed codes extracted and stored",
                    encounter_id=encounter_id,
                    billed_code_count=len(billed_codes)
                )

                # Audit log: Billed codes extracted
                await create_audit_log(
                    action="BILLED_CODES_EXTRACTED",
                    user_id=encounter.userId,
                    resource_type="BillingCode",
                    resource_id=encounter_id,
                    metadata={
                        "billed_code_count": len(billed_codes),
                        "extraction_method": "REGEX_TEXT_EXTRACTION",
                    },
                )

            except Exception as e:
                logger.warning(
                    "Failed to extract billed codes from text",
                    encounter_id=encounter_id,
                    error=str(e)
                )
        else:
            logger.info(
                "Skipping text-based billed code extraction (FHIR workflow)",
                encounter_id=encounter_id,
                encounter_source=encounter.encounterSource
            )

        # Always use async path: Create PENDING report and queue for background processing
        from prisma import Json

        report_data = {
            "encounterId": encounter_id,
            "status": enums.ReportStatus.PENDING,
            "progressPercent": 0,
            "currentStep": "queued",
            # Empty initial data - will be populated by async worker
            "billedCodes": Json([]),
            "suggestedCodes": Json([]),
            "extractedIcd10Codes": Json([]),
            "extractedSnomedCodes": Json([]),
            "cptSuggestions": Json([]),
            "incrementalRevenue": 0.0,
            "aiModel": "gpt-4o-mini",
        }

        report = await prisma.report.create(data=report_data)

        # Queue for async processing
        queue_report_processing(report.id)

        logger.info(
            "Report queued for async processing",
            encounter_id=encounter_id,
            report_id=report.id,
            mode="async"
        )

        # Remove legacy sync path - all reports now processed async
        if False:  # Keep error handling structure but never execute
            try:
                pass  # Sync path removed
            except Exception as e:
                logger.error(
                    "Report generation failed (legacy path)",
                    encounter_id=encounter_id,
                    error=str(e)
                )
                # Don't fail the entire PHI processing if report generation fails
                # User can retry report generation later

        # Audit log: Report queued for async processing
        # Note: Detailed metrics will be logged by the async processor when complete
        await create_audit_log(
            action="REPORT_QUEUED",
            user_id=encounter.userId,
            resource_type="Report",
            resource_id=report.id,
            metadata={
                "encounter_id": encounter_id,
                "processing_mode": "async",
            },
        )

        # Step 7: Delete original file from S3 (HIPAA requirement)
        logger.info("Deleting original file from S3", file_path=file_path)
        await storage_service.delete_file(file_path)

        # Update uploaded file record to indicate deletion
        await prisma.uploadedfile.update(
            where={"id": uploaded_file.id},
            data={
                "filePath": f"deleted://{encounter_id}/{uploaded_file.fileName}",
            }
        )

        logger.info("Original file deleted from S3", encounter_id=encounter_id)

        # Audit log: File deletion (HIPAA compliance)
        await create_audit_log(
            action="FILE_DELETED",
            user_id=encounter.userId,
            resource_type="UploadedFile",
            resource_id=uploaded_file.id,
            metadata={
                "encounter_id": encounter_id,
                "original_file_path": file_path,
                "file_name": uploaded_file.fileName,
                "reason": "HIPAA_COMPLIANCE_PHI_REMOVAL",
            },
        )

        # Step 8: Update encounter status to COMPLETED
        processing_end_time = datetime.utcnow()
        processing_time_ms = int((processing_end_time - processing_start_time).total_seconds() * 1000)

        # Prepare encounter update data
        encounter_update_data = {
            "status": enums.EncounterStatus.COMPLETE,
            "processingCompletedAt": processing_end_time,
            "processingTime": processing_time_ms,
            "fileHash": filename_hash,
        }

        # Add optional fields if extracted
        if provider_initials:
            encounter_update_data["providerInitials"] = provider_initials
        if date_of_service:
            encounter_update_data["dateOfService"] = date_of_service
        if filtering_result and filtering_result.get("encounter_type"):
            encounter_update_data["encounterType"] = filtering_result["encounter_type"]

        await prisma.encounter.update(
            where={"id": encounter_id},
            data=encounter_update_data
        )

        logger.info(
            "PHI processing completed successfully",
            encounter_id=encounter_id,
            processing_time_ms=processing_time_ms,
            phi_detected=result.phi_detected
        )

        # Audit log: PHI processing completed
        await create_audit_log(
            action="PHI_PROCESSING_COMPLETED",
            user_id=encounter.userId,
            resource_type="Encounter",
            resource_id=encounter_id,
            metadata={
                "processing_time_ms": processing_time_ms,
                "phi_detected": result.phi_detected,
                "status": "success",
            },
        )

    except Exception as e:
        # Log error
        logger.error(
            "PHI processing failed",
            encounter_id=encounter_id,
            error=str(e),
            error_type=type(e).__name__
        )

        # Update encounter status to FAILED
        try:
            await prisma.encounter.update(
                where={"id": encounter_id},
                data={
                    "status": enums.EncounterStatus.FAILED,
                    "errorMessage": str(e),
                    "processingCompletedAt": datetime.utcnow(),
                }
            )
        except Exception as update_error:
            logger.error(
                "Failed to update encounter status to FAILED",
                encounter_id=encounter_id,
                error=str(update_error)
            )

        # Re-raise exception for background task error handling
        raise


async def reprocess_encounter_phi(encounter_id: str) -> None:
    """
    Retry PHI processing for a failed encounter

    Args:
        encounter_id: Encounter ID to reprocess
    """
    logger.info("Retrying PHI processing", encounter_id=encounter_id)

    # Increment retry count
    encounter = await prisma.encounter.find_unique(where={"id": encounter_id})

    if not encounter:
        raise ValueError(f"Encounter not found: {encounter_id}")

    await prisma.encounter.update(
        where={"id": encounter_id},
        data={"retryCount": encounter.retryCount + 1}
    )

    # Process again
    await process_encounter_phi(encounter_id)
