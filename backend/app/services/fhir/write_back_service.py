"""
FHIR Write-Back Service (Optional)
Handles writing coding suggestions back to FHIR server as Claim or DocumentReference resources
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import structlog

from app.services.fhir.fhir_client import FhirClient, FhirClientError

logger = structlog.get_logger(__name__)


class FhirWriteBackService:
    """
    Service for writing coding suggestions back to FHIR server

    Handles:
    - Creating FHIR Claim resources with suggested codes
    - Creating DocumentReference resources with coding reports
    - Updating Encounter.diagnosis with suggested ICD-10 codes

    Note: This is an optional feature that requires write permissions to FHIR server
    """

    def __init__(self, fhir_client: FhirClient):
        """
        Initialize write-back service

        Args:
            fhir_client: Configured FhirClient instance with write permissions
        """
        self.fhir_client = fhir_client

    async def create_claim_resource(
        self,
        encounter_id: str,
        patient_id: str,
        provider_id: Optional[str],
        icd10_codes: List[Dict[str, Any]],
        cpt_codes: List[Dict[str, Any]],
        date_of_service: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a FHIR Claim resource with suggested billing codes

        Args:
            encounter_id: FHIR Encounter ID
            patient_id: FHIR Patient ID
            provider_id: FHIR Practitioner ID
            icd10_codes: List of suggested ICD-10 codes with descriptions
            cpt_codes: List of suggested CPT codes with descriptions
            date_of_service: Date of service (ISO format)

        Returns:
            Created Claim resource

        Raises:
            FhirClientError: If claim creation fails
        """
        logger.info(
            "create_fhir_claim",
            encounter_id=encounter_id,
            patient_id=patient_id,
            icd10_count=len(icd10_codes),
            cpt_count=len(cpt_codes),
        )

        # Build Claim resource
        claim = {
            "resourceType": "Claim",
            "status": "draft",  # Draft until reviewed by provider
            "type": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/claim-type",
                        "code": "professional",
                        "display": "Professional",
                    }
                ]
            },
            "use": "claim",
            "patient": {"reference": f"Patient/{patient_id}"},
            "created": datetime.utcnow().isoformat() + "Z",
            "provider": {"reference": f"Practitioner/{provider_id}"} if provider_id else None,
            "priority": {
                "coding": [
                    {
                        "code": "normal",
                    }
                ]
            },
            "insurance": [
                {
                    "sequence": 1,
                    "focal": True,
                    "coverage": {
                        "reference": "Coverage/unknown",  # Would need to be populated
                    },
                }
            ],
        }

        # Add diagnosis (ICD-10 codes)
        if icd10_codes:
            claim["diagnosis"] = []
            for idx, code in enumerate(icd10_codes, start=1):
                claim["diagnosis"].append(
                    {
                        "sequence": idx,
                        "diagnosisCodeableConcept": {
                            "coding": [
                                {
                                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                                    "code": code["code"],
                                    "display": code.get("description", ""),
                                }
                            ],
                            "text": code.get("justification", ""),
                        },
                    }
                )

        # Add procedure/service items (CPT codes)
        if cpt_codes:
            claim["item"] = []
            for idx, code in enumerate(cpt_codes, start=1):
                claim["item"].append(
                    {
                        "sequence": idx,
                        "productOrService": {
                            "coding": [
                                {
                                    "system": "http://www.ama-assn.org/go/cpt",
                                    "code": code["code"],
                                    "display": code.get("description", ""),
                                }
                            ],
                            "text": code.get("justification", ""),
                        },
                        "servicedDate": date_of_service,
                    }
                )

        # Add reference to encounter
        if encounter_id:
            claim["item"] = claim.get("item", [])
            if claim["item"]:
                claim["item"][0]["encounter"] = [{"reference": f"Encounter/{encounter_id}"}]

        # Add extension for AI-generated codes
        claim["extension"] = [
            {
                "url": "http://revrx.com/fhir/StructureDefinition/ai-generated-codes",
                "valueBoolean": True,
            }
        ]

        try:
            created_claim = await self.fhir_client.create_resource("Claim", claim)

            logger.info(
                "create_fhir_claim_success",
                claim_id=created_claim.get("id"),
                encounter_id=encounter_id,
            )

            return created_claim

        except FhirClientError as e:
            logger.error(
                "create_fhir_claim_failed",
                encounter_id=encounter_id,
                error=str(e),
            )
            raise

    async def create_document_reference(
        self,
        encounter_id: str,
        patient_id: str,
        report_content: str,
        report_format: str = "text/plain",
        title: str = "AI Coding Review Report",
    ) -> Dict[str, Any]:
        """
        Create a FHIR DocumentReference with coding suggestions as attachment

        Args:
            encounter_id: FHIR Encounter ID
            patient_id: FHIR Patient ID
            report_content: Report content (plain text, JSON, or Base64 PDF)
            report_format: MIME type (text/plain, application/json, application/pdf)
            title: Document title

        Returns:
            Created DocumentReference resource

        Raises:
            FhirClientError: If document creation fails
        """
        logger.info(
            "create_fhir_document_reference",
            encounter_id=encounter_id,
            patient_id=patient_id,
            format=report_format,
        )

        # Build DocumentReference
        document_ref = {
            "resourceType": "DocumentReference",
            "status": "current",
            "type": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "11506-3",
                        "display": "Progress note",
                    }
                ],
                "text": "AI Coding Review Report",
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "date": datetime.utcnow().isoformat() + "Z",
            "description": title,
            "content": [
                {
                    "attachment": {
                        "contentType": report_format,
                        "data": report_content,  # Base64 if binary, or raw text
                        "title": title,
                        "creation": datetime.utcnow().isoformat() + "Z",
                    }
                }
            ],
        }

        # Add context reference to encounter
        if encounter_id:
            document_ref["context"] = {
                "encounter": [{"reference": f"Encounter/{encounter_id}"}],
            }

        try:
            created_doc_ref = await self.fhir_client.create_resource(
                "DocumentReference",
                document_ref,
            )

            logger.info(
                "create_fhir_document_reference_success",
                doc_ref_id=created_doc_ref.get("id"),
                encounter_id=encounter_id,
            )

            return created_doc_ref

        except FhirClientError as e:
            logger.error(
                "create_fhir_document_reference_failed",
                encounter_id=encounter_id,
                error=str(e),
            )
            raise

    async def update_encounter_diagnosis(
        self,
        encounter_id: str,
        icd10_codes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Update FHIR Encounter.diagnosis with suggested ICD-10 codes

        Args:
            encounter_id: FHIR Encounter ID
            icd10_codes: List of suggested ICD-10 codes

        Returns:
            Updated Encounter resource

        Raises:
            FhirClientError: If update fails
        """
        logger.info(
            "update_fhir_encounter_diagnosis",
            encounter_id=encounter_id,
            icd10_count=len(icd10_codes),
        )

        try:
            # First, fetch the current encounter
            encounter = await self.fhir_client.get_resource("Encounter", encounter_id)

            # Build diagnosis array
            diagnosis_list = []
            for idx, code in enumerate(icd10_codes, start=1):
                diagnosis_list.append(
                    {
                        "condition": {
                            "coding": [
                                {
                                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                                    "code": code["code"],
                                    "display": code.get("description", ""),
                                }
                            ],
                            "text": code.get("justification", ""),
                        },
                        "use": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/diagnosis-role",
                                    "code": "billing",
                                    "display": "Billing",
                                }
                            ]
                        },
                        "rank": idx,
                    }
                )

            # Update encounter with new diagnosis
            encounter["diagnosis"] = diagnosis_list

            # Add extension to indicate AI-generated
            encounter.setdefault("extension", []).append(
                {
                    "url": "http://revrx.com/fhir/StructureDefinition/ai-generated-diagnosis",
                    "valueBoolean": True,
                }
            )

            # Update the encounter
            updated_encounter = await self.fhir_client.update_resource(
                "Encounter",
                encounter_id,
                encounter,
            )

            logger.info(
                "update_fhir_encounter_diagnosis_success",
                encounter_id=encounter_id,
                diagnosis_count=len(diagnosis_list),
            )

            return updated_encounter

        except FhirClientError as e:
            logger.error(
                "update_fhir_encounter_diagnosis_failed",
                encounter_id=encounter_id,
                error=str(e),
            )
            raise

    async def write_back_coding_suggestions(
        self,
        encounter_id: str,
        patient_id: str,
        provider_id: Optional[str],
        icd10_codes: List[Dict[str, Any]],
        cpt_codes: List[Dict[str, Any]],
        date_of_service: Optional[str],
        write_claim: bool = True,
        write_diagnosis: bool = False,
        write_document: bool = False,
        report_content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Write coding suggestions back to FHIR server

        Supports multiple write-back strategies:
        - Create Claim resource (draft for review)
        - Update Encounter.diagnosis
        - Create DocumentReference with report

        Args:
            encounter_id: FHIR Encounter ID
            patient_id: FHIR Patient ID
            provider_id: FHIR Practitioner ID
            icd10_codes: List of ICD-10 code suggestions
            cpt_codes: List of CPT code suggestions
            date_of_service: Date of service
            write_claim: Whether to create Claim resource
            write_diagnosis: Whether to update Encounter.diagnosis
            write_document: Whether to create DocumentReference
            report_content: Report content for DocumentReference

        Returns:
            Dictionary with results of each write-back operation
        """
        logger.info(
            "write_back_coding_suggestions",
            encounter_id=encounter_id,
            write_claim=write_claim,
            write_diagnosis=write_diagnosis,
            write_document=write_document,
        )

        results = {
            "claim": None,
            "encounter": None,
            "document_reference": None,
            "errors": [],
        }

        # Create Claim resource
        if write_claim:
            try:
                claim = await self.create_claim_resource(
                    encounter_id=encounter_id,
                    patient_id=patient_id,
                    provider_id=provider_id,
                    icd10_codes=icd10_codes,
                    cpt_codes=cpt_codes,
                    date_of_service=date_of_service,
                )
                results["claim"] = {
                    "id": claim.get("id"),
                    "status": "success",
                }
            except Exception as e:
                logger.error("write_back_claim_failed", error=str(e))
                results["errors"].append(f"Claim creation failed: {e}")

        # Update Encounter diagnosis
        if write_diagnosis and icd10_codes:
            try:
                encounter = await self.update_encounter_diagnosis(
                    encounter_id=encounter_id,
                    icd10_codes=icd10_codes,
                )
                results["encounter"] = {
                    "id": encounter.get("id"),
                    "status": "success",
                }
            except Exception as e:
                logger.error("write_back_diagnosis_failed", error=str(e))
                results["errors"].append(f"Encounter diagnosis update failed: {e}")

        # Create DocumentReference
        if write_document and report_content:
            try:
                doc_ref = await self.create_document_reference(
                    encounter_id=encounter_id,
                    patient_id=patient_id,
                    report_content=report_content,
                    report_format="application/json",
                    title="AI Coding Review Report",
                )
                results["document_reference"] = {
                    "id": doc_ref.get("id"),
                    "status": "success",
                }
            except Exception as e:
                logger.error("write_back_document_failed", error=str(e))
                results["errors"].append(f"DocumentReference creation failed: {e}")

        logger.info(
            "write_back_coding_suggestions_complete",
            encounter_id=encounter_id,
            results=results,
        )

        return results
