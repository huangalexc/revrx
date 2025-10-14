"""
FHIR Processing Background Tasks
Handles asynchronous processing of FHIR encounters from EHR systems
"""

from typing import Optional, Dict, Any
import structlog
from datetime import datetime

from app.core.database import prisma
from app.core.audit import create_audit_log
from app.core.encryption import encryption_service
from app.services.fhir.fhir_client import FhirClient, FhirAuthType
from app.services.fhir.encounter_service import FhirEncounterService
from app.services.fhir.note_service import FhirNoteService
from app.services.comprehend_medical import comprehend_medical_service
from app.services.phi_handler import phi_handler
from app.services.openai_service import openai_service
from app.services.snomed_crosswalk import get_crosswalk_service
from prisma import enums

logger = structlog.get_logger(__name__)


async def process_fhir_encounter(
    fhir_connection_id: str,
    fhir_encounter_id: str,
    user_id: str,
) -> Optional[str]:
    """
    Background task to process a FHIR encounter from EHR system

    HIPAA-compliant FHIR workflow:
    1. Fetch FHIR connection configuration
    2. Initialize FHIR client
    3. Fetch FHIR encounter metadata
    4. Fetch clinical notes (Composition/DocumentReference)
    5. Check for duplicates
    6. Detect and redact PHI
    7. Filter for clinical relevance
    8. Extract entities (ICD-10, SNOMED)
    9. Generate CPT codes via SNOMED crosswalk
    10. Generate coding suggestions via GPT-4o-mini
    11. Store results in database

    Args:
        fhir_connection_id: FhirConnection ID
        fhir_encounter_id: FHIR Encounter resource ID
        user_id: User ID who owns this connection

    Returns:
        Created Encounter ID if successful, None if failed

    Raises:
        Exception: If any step fails, error is logged and None is returned
    """
    processing_start_time = datetime.utcnow()
    encounter_id = None

    try:
        logger.info(
            "fhir_processing_started",
            fhir_connection_id=fhir_connection_id,
            fhir_encounter_id=fhir_encounter_id,
            user_id=user_id,
        )

        # Audit log: FHIR processing started
        await create_audit_log(
            action="FHIR_PROCESSING_STARTED",
            user_id=user_id,
            resource_type="FhirEncounter",
            resource_id=fhir_encounter_id,
            metadata={
                "fhir_connection_id": fhir_connection_id,
                "processing_start_time": processing_start_time.isoformat(),
            },
        )

        # Step 1: Fetch FHIR connection configuration
        logger.info("fetch_fhir_connection", fhir_connection_id=fhir_connection_id)

        fhir_connection = await prisma.fhirconnection.find_unique(
            where={"id": fhir_connection_id},
        )

        if not fhir_connection:
            raise ValueError(f"FHIR connection not found: {fhir_connection_id}")

        if not fhir_connection.isActive:
            raise ValueError(f"FHIR connection is not active: {fhir_connection_id}")

        if fhir_connection.userId != user_id:
            raise ValueError(f"FHIR connection does not belong to user: {user_id}")

        logger.info(
            "fhir_connection_retrieved",
            fhir_server_url=fhir_connection.fhirServerUrl,
            fhir_version=fhir_connection.fhirVersion,
            auth_type=fhir_connection.authType,
        )

        # Step 2: Initialize FHIR client
        logger.info("initialize_fhir_client")

        # Decrypt client secret if present
        client_secret = None
        if fhir_connection.clientSecretHash:
            try:
                client_secret = encryption_service.decrypt(fhir_connection.clientSecretHash)
            except Exception as e:
                logger.error("failed_to_decrypt_client_secret", error=str(e))
                raise ValueError("Failed to decrypt FHIR client secret")

        fhir_client = FhirClient(
            fhir_server_url=fhir_connection.fhirServerUrl,
            fhir_version=fhir_connection.fhirVersion,
            auth_type=FhirAuthType(fhir_connection.authType),
            client_id=fhir_connection.clientId,
            client_secret=client_secret,
            token_endpoint=fhir_connection.tokenEndpoint,
            scope=fhir_connection.scope,
        )

        # Step 3: Fetch FHIR encounter metadata
        logger.info("fetch_fhir_encounter_metadata", fhir_encounter_id=fhir_encounter_id)

        async with fhir_client:
            encounter_service = FhirEncounterService(fhir_client)

            fhir_encounter = await encounter_service.fetch_encounter_by_id(fhir_encounter_id)

            # Validate encounter has minimum required data
            is_valid, validation_error = encounter_service.validate_encounter_for_processing(
                fhir_encounter
            )

            if not is_valid:
                raise ValueError(f"FHIR encounter validation failed: {validation_error}")

            # Extract metadata
            encounter_metadata = encounter_service.extract_encounter_metadata(fhir_encounter)

            logger.info(
                "fhir_encounter_metadata_extracted",
                fhir_encounter_id=fhir_encounter_id,
                fhir_patient_id=encounter_metadata["fhir_patient_id"],
                fhir_provider_id=encounter_metadata["fhir_provider_id"],
                date_of_service=encounter_metadata["date_of_service"],
            )

            # Step 4: Fetch clinical notes
            logger.info("fetch_fhir_clinical_notes", fhir_encounter_id=fhir_encounter_id)

            note_service = FhirNoteService(fhir_client)

            clinical_notes = await note_service.fetch_clinical_notes(fhir_encounter_id)

            if not clinical_notes or len(clinical_notes) == 0:
                logger.warning(
                    "no_clinical_notes_found",
                    fhir_encounter_id=fhir_encounter_id,
                )
                raise ValueError(f"No clinical notes found for encounter: {fhir_encounter_id}")

            # Combine notes into single text
            combined_text = note_service.combine_notes(clinical_notes)

            if not combined_text or len(combined_text) < 10:
                raise ValueError(f"Combined clinical text too short: {len(combined_text)} chars")

            logger.info(
                "fhir_clinical_notes_retrieved",
                fhir_encounter_id=fhir_encounter_id,
                note_count=len(clinical_notes),
                combined_text_length=len(combined_text),
            )

        # Step 5: Check for duplicates
        logger.info("check_fhir_duplicate", fhir_encounter_id=fhir_encounter_id)

        existing_encounter = await prisma.encounter.find_unique(
            where={"fhirEncounterId": fhir_encounter_id},
        )

        if existing_encounter:
            logger.warning(
                "fhir_encounter_duplicate_found",
                fhir_encounter_id=fhir_encounter_id,
                existing_encounter_id=existing_encounter.id,
            )

            # Update last sync timestamp
            await prisma.fhirconnection.update(
                where={"id": fhir_connection_id},
                data={"lastSyncAt": datetime.utcnow()},
            )

            # Return existing encounter ID (skip processing)
            return existing_encounter.id

        # Step 6: Create encounter record
        logger.info("create_encounter_record", fhir_encounter_id=fhir_encounter_id)

        # Parse date of service
        date_of_service = None
        if encounter_metadata["date_of_service"]:
            from dateutil import parser as date_parser
            try:
                date_of_service = date_parser.parse(encounter_metadata["date_of_service"])
            except Exception as e:
                logger.warning(
                    "failed_to_parse_date_of_service",
                    date_text=encounter_metadata["date_of_service"],
                    error=str(e),
                )

        encounter = await prisma.encounter.create(
            data={
                "userId": user_id,
                "status": enums.EncounterStatus.PROCESSING,
                "processingStartedAt": processing_start_time,
                "encounterSource": enums.EncounterSource.FHIR,
                "fhirEncounterId": fhir_encounter_id,
                "fhirPatientId": encounter_metadata["fhir_patient_id"],
                "fhirProviderId": encounter_metadata["fhir_provider_id"],
                "fhirSourceSystem": fhir_connection.fhirServerUrl,
                "dateOfService": date_of_service,
                "encounterType": encounter_metadata["encounter_type"],
            }
        )

        encounter_id = encounter.id

        logger.info(
            "encounter_record_created",
            encounter_id=encounter_id,
            fhir_encounter_id=fhir_encounter_id,
        )

        # Audit log: Encounter created
        await create_audit_log(
            action="FHIR_ENCOUNTER_CREATED",
            user_id=user_id,
            resource_type="Encounter",
            resource_id=encounter_id,
            metadata={
                "fhir_encounter_id": fhir_encounter_id,
                "fhir_patient_id": encounter_metadata["fhir_patient_id"],
                "encounter_source": "FHIR",
            },
        )

        # Step 7: Detect and redact PHI
        logger.info("detect_and_redact_phi", encounter_id=encounter_id)

        phi_result = await phi_handler.process_clinical_note(
            encounter_id=encounter_id,
            clinical_text=combined_text,
            user_id=user_id,
        )

        logger.info(
            "phi_processing_completed",
            encounter_id=encounter_id,
            phi_detected=phi_result.phi_detected,
            phi_count=len(phi_result.phi_entities),
        )

        # Audit log: PHI detected
        await create_audit_log(
            action="PHI_DETECTED",
            user_id=user_id,
            resource_type="PhiMapping",
            resource_id=encounter_id,
            metadata={
                "phi_detected": phi_result.phi_detected,
                "phi_entity_count": len(phi_result.phi_entities),
                "phi_types": [e.type for e in phi_result.phi_entities] if phi_result.phi_entities else [],
            },
        )

        # Step 8: Filter for clinical relevance
        logger.info("filter_clinical_relevance", encounter_id=encounter_id)

        deidentified_text = phi_result.deidentified_text
        filtering_result = None
        provider_initials = None
        extracted_date_of_service = None

        try:
            filtering_result = await openai_service.filter_clinical_relevance(
                deidentified_text=deidentified_text
            )

            clinical_text_for_coding = filtering_result["filtered_text"]

            # Extract provider and date from placeholders (if not already from FHIR)
            if not encounter_metadata["fhir_provider_id"]:
                provider_placeholder = filtering_result.get("provider_placeholder")
                if provider_placeholder:
                    provider_mapping = next(
                        (m for m in phi_result.phi_mappings if m.token == f"[{provider_placeholder}]"),
                        None
                    )
                    if provider_mapping:
                        name_parts = provider_mapping.original.split()
                        if len(name_parts) >= 2:
                            initials = ''.join([part[0].upper() for part in name_parts[:2] if part])
                            if initials and len(initials) >= 2:
                                provider_initials = initials
                                logger.info(
                                    "provider_extracted_from_llm",
                                    provider_initials=provider_initials,
                                )

            if not date_of_service:
                service_date_placeholder = filtering_result.get("service_date_placeholder")
                if service_date_placeholder:
                    date_mapping = next(
                        (m for m in phi_result.phi_mappings if m.token == f"[{service_date_placeholder}]"),
                        None
                    )
                    if date_mapping:
                        from dateutil import parser as date_parser
                        try:
                            extracted_date_of_service = date_parser.parse(date_mapping.original)
                            logger.info(
                                "date_extracted_from_llm",
                                date_of_service=extracted_date_of_service.isoformat(),
                            )
                        except Exception as e:
                            logger.warning("failed_to_parse_llm_date", error=str(e))

            logger.info(
                "clinical_relevance_filtering_completed",
                encounter_id=encounter_id,
                original_length=filtering_result["original_length"],
                filtered_length=filtering_result["filtered_length"],
                reduction_pct=filtering_result["reduction_pct"],
            )

        except Exception as e:
            logger.warning(
                "clinical_relevance_filtering_failed",
                encounter_id=encounter_id,
                error=str(e),
            )
            clinical_text_for_coding = deidentified_text

        # Update encounter with extracted metadata
        update_data: Dict[str, Any] = {}
        if provider_initials:
            update_data["providerInitials"] = provider_initials
        if extracted_date_of_service:
            update_data["dateOfService"] = extracted_date_of_service

        if update_data:
            await prisma.encounter.update(
                where={"id": encounter_id},
                data=update_data,
            )

        # Step 8.5: Extract billed codes from FHIR Claims
        logger.info("extract_billed_codes_from_claims", encounter_id=encounter_id)

        try:
            from app.services.fhir.claims_service import FhirClaimsService

            # Re-use the fhir_client context from Step 4
            async with fhir_client:
                claims_service = FhirClaimsService(fhir_client)

                billed_codes = await claims_service.extract_billing_codes_for_encounter(
                    fhir_encounter_id
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
                                "source": "FHIR_CLAIM",
                            }
                        )
                    except Exception as e:
                        logger.warning(
                            "failed_to_store_billed_code",
                            encounter_id=encounter_id,
                            code=code_dict["code"],
                            error=str(e)
                        )

                logger.info(
                    "billed_codes_extracted_from_claims",
                    encounter_id=encounter_id,
                    billed_code_count=len(billed_codes)
                )

                # Audit log: Billed codes extracted
                await create_audit_log(
                    action="BILLED_CODES_EXTRACTED",
                    user_id=user_id,
                    resource_type="BillingCode",
                    resource_id=encounter_id,
                    metadata={
                        "billed_code_count": len(billed_codes),
                        "extraction_method": "FHIR_CLAIMS",
                    },
                )

        except Exception as e:
            logger.warning(
                "failed_to_extract_billed_codes_from_claims",
                encounter_id=encounter_id,
                error=str(e)
            )
            # Continue processing even if Claims extraction fails
            # (not all encounters have Claims in the EHR)

        # Step 9: Extract ICD-10 codes
        logger.info("extract_icd10_codes", encounter_id=encounter_id)

        icd10_entities = []
        try:
            icd10_entities = comprehend_medical_service.infer_icd10_cm(clinical_text_for_coding)

            logger.info(
                "icd10_codes_extracted",
                encounter_id=encounter_id,
                icd10_code_count=len(icd10_entities),
            )

            # Store ICD-10 codes
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
                        "failed_to_store_icd10_code",
                        encounter_id=encounter_id,
                        code=entity.code,
                        error=str(e),
                    )

        except Exception as e:
            logger.warning(
                "failed_to_extract_icd10_codes",
                encounter_id=encounter_id,
                error=str(e),
            )

        # Step 10: Extract SNOMED CT codes
        logger.info("extract_snomed_codes", encounter_id=encounter_id)

        snomed_entities = []
        try:
            snomed_entities = comprehend_medical_service.infer_snomed_ct(clinical_text_for_coding)

            logger.info(
                "snomed_codes_extracted",
                encounter_id=encounter_id,
                snomed_code_count=len(snomed_entities),
            )

            # Store SNOMED codes
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
                        "failed_to_store_snomed_code",
                        encounter_id=encounter_id,
                        code=entity.code,
                        error=str(e),
                    )

        except Exception as e:
            logger.warning(
                "failed_to_extract_snomed_codes",
                encounter_id=encounter_id,
                error=str(e),
            )

        # Step 11: Generate CPT codes via SNOMED crosswalk
        logger.info("generate_cpt_codes", encounter_id=encounter_id)

        cpt_codes = []
        try:
            crosswalk_service = await get_crosswalk_service()

            for snomed_entity in snomed_entities:
                cpt_mappings = await crosswalk_service.get_cpt_codes(snomed_entity.code)

                for cpt_code, description in cpt_mappings:
                    cpt_codes.append({
                        "code": cpt_code,
                        "description": description,
                        "source_snomed": snomed_entity.code,
                    })

            logger.info(
                "cpt_codes_generated",
                encounter_id=encounter_id,
                cpt_code_count=len(cpt_codes),
            )

        except Exception as e:
            logger.warning(
                "failed_to_generate_cpt_codes",
                encounter_id=encounter_id,
                error=str(e),
            )

        # Step 12: Generate coding suggestions via GPT-4o-mini
        logger.info("generate_coding_suggestions", encounter_id=encounter_id)

        try:
            # Prepare billed codes (CPT from crosswalk)
            billed_codes = [
                {
                    "code": cpt["code"],
                    "code_type": "CPT",
                    "description": cpt["description"],
                }
                for cpt in cpt_codes
            ]

            coding_suggestions = await openai_service.generate_coding_suggestions(
                clinical_text=clinical_text_for_coding,
                billed_codes=billed_codes,
            )

            # Store billing codes
            for suggestion in coding_suggestions:
                try:
                    await prisma.billingcode.create(
                        data={
                            "encounterId": encounter_id,
                            "code": suggestion.code,
                            "codeType": suggestion.code_type,
                            "description": suggestion.description,
                            "justification": suggestion.justification,
                            "confidence": suggestion.confidence,
                            "confidenceReason": suggestion.confidence_reason,
                            "supportingText": suggestion.supporting_text,
                            "incrementalRevenue": suggestion.incremental_revenue,
                        }
                    )
                except Exception as e:
                    logger.warning(
                        "failed_to_store_billing_code",
                        encounter_id=encounter_id,
                        code=suggestion.code,
                        error=str(e),
                    )

            logger.info(
                "coding_suggestions_generated",
                encounter_id=encounter_id,
                suggestion_count=len(coding_suggestions),
            )

        except Exception as e:
            logger.warning(
                "failed_to_generate_coding_suggestions",
                encounter_id=encounter_id,
                error=str(e),
            )

        # Step 13: Mark encounter as complete
        processing_completed_time = datetime.utcnow()
        processing_time = int((processing_completed_time - processing_start_time).total_seconds() * 1000)

        await prisma.encounter.update(
            where={"id": encounter_id},
            data={
                "status": enums.EncounterStatus.COMPLETE,
                "processingCompletedAt": processing_completed_time,
                "processingTime": processing_time,
            }
        )

        # Update FHIR connection last sync time
        await prisma.fhirconnection.update(
            where={"id": fhir_connection_id},
            data={
                "lastSyncAt": processing_completed_time,
                "lastError": None,
            },
        )

        logger.info(
            "fhir_processing_completed",
            encounter_id=encounter_id,
            fhir_encounter_id=fhir_encounter_id,
            processing_time_ms=processing_time,
        )

        # Audit log: Processing completed
        await create_audit_log(
            action="FHIR_PROCESSING_COMPLETED",
            user_id=user_id,
            resource_type="Encounter",
            resource_id=encounter_id,
            metadata={
                "fhir_encounter_id": fhir_encounter_id,
                "processing_time_ms": processing_time,
                "status": "COMPLETE",
            },
        )

        return encounter_id

    except Exception as e:
        logger.error(
            "fhir_processing_failed",
            fhir_encounter_id=fhir_encounter_id,
            encounter_id=encounter_id,
            error=str(e),
        )

        # Update encounter status to FAILED if it was created
        if encounter_id:
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
                    "failed_to_update_encounter_status",
                    encounter_id=encounter_id,
                    error=str(update_error),
                )

        # Update FHIR connection with error
        try:
            await prisma.fhirconnection.update(
                where={"id": fhir_connection_id},
                data={"lastError": str(e)},
            )
        except Exception as update_error:
            logger.error(
                "failed_to_update_fhir_connection_error",
                fhir_connection_id=fhir_connection_id,
                error=str(update_error),
            )

        # Audit log: Processing failed
        await create_audit_log(
            action="FHIR_PROCESSING_FAILED",
            user_id=user_id,
            resource_type="FhirEncounter",
            resource_id=fhir_encounter_id,
            metadata={
                "encounter_id": encounter_id,
                "error": str(e),
            },
        )

        return None
