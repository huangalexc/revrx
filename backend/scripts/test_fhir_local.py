"""
Test FHIR Processing with Local Synthetic Data
Tests the complete FHIR processing pipeline using Synthea synthetic data
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import prisma
from app.services.fhir.encounter_service import FhirEncounterService
from app.services.fhir.note_service import FhirNoteService
from app.tasks.fhir_processing import process_fhir_encounter
from app.services.phi_handler import phi_handler
from app.services.openai_service import openai_service
from app.services.comprehend_medical import comprehend_medical_service
import structlog

logger = structlog.get_logger(__name__)


class LocalFhirClient:
    """
    Mock FHIR client that reads from local JSON files instead of API
    Mimics the real FhirClient interface for testing
    """

    def __init__(self, bundle_path: str):
        """
        Initialize with path to FHIR Bundle JSON file

        Args:
            bundle_path: Path to Synthea FHIR bundle JSON file
        """
        self.bundle_path = Path(bundle_path)
        self.bundle_data = None
        self.resources = {}

        logger.info("local_fhir_client_initialized", bundle_path=str(self.bundle_path))

    async def __aenter__(self):
        """Load bundle data"""
        await self.load_bundle()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup"""
        pass

    async def load_bundle(self):
        """Load and parse FHIR bundle from file"""
        logger.info("loading_fhir_bundle", path=str(self.bundle_path))

        with open(self.bundle_path, 'r') as f:
            self.bundle_data = json.load(f)

        # Index resources by type and ID
        for entry in self.bundle_data.get("entry", []):
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType")
            resource_id = resource.get("id")

            if resource_type and resource_id:
                if resource_type not in self.resources:
                    self.resources[resource_type] = {}
                self.resources[resource_type][resource_id] = resource

        logger.info(
            "fhir_bundle_loaded",
            resource_types=list(self.resources.keys()),
            total_resources=sum(len(r) for r in self.resources.values()),
        )

    async def authenticate(self) -> str:
        """Mock authentication (not needed for local files)"""
        return "local-mock-token"

    async def get_resource(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        """
        Get a single FHIR resource by type and ID

        Args:
            resource_type: FHIR resource type (e.g., "Encounter")
            resource_id: Resource ID (can include urn:uuid: prefix)

        Returns:
            FHIR resource as dict
        """
        logger.info("get_resource", resource_type=resource_type, resource_id=resource_id)

        if resource_type not in self.resources:
            raise ValueError(f"Resource type not found: {resource_type}")

        # Strip urn:uuid: prefix if present
        clean_id = resource_id.replace("urn:uuid:", "")

        if clean_id not in self.resources[resource_type]:
            raise ValueError(f"Resource not found: {resource_type}/{resource_id}")

        return self.resources[resource_type][clean_id]

    async def search_resources(
        self,
        resource_type: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search FHIR resources with query parameters

        Args:
            resource_type: FHIR resource type
            params: Search parameters (e.g., {"encounter": "Encounter/123"})

        Returns:
            List of matching FHIR resources
        """
        logger.info("search_resources", resource_type=resource_type, params=params)

        if resource_type not in self.resources:
            return []

        all_resources = list(self.resources[resource_type].values())

        # Apply filters
        if params:
            filtered = []
            for resource in all_resources:
                match = True

                # Filter by encounter reference
                if "encounter" in params:
                    encounter_ref = params["encounter"]
                    # Extract ID from reference
                    encounter_id = encounter_ref.split("/")[-1]

                    # Check if resource has encounter reference matching
                    # Handle different FHIR resource structures:
                    # - Direct reference: Procedure, Condition (encounter.reference)
                    # - Item array: Claim (item[].encounter[])
                    # - Context array: DocumentReference (context.encounter[])

                    has_match = False

                    # Check direct encounter reference (Procedure, Condition, DiagnosticReport)
                    resource_encounter = resource.get("encounter", {}).get("reference", "")
                    if encounter_id in resource_encounter:
                        has_match = True

                    # For Claims, check item[].encounter[] array
                    if not has_match and resource_type == "Claim":
                        items = resource.get("item", [])
                        for item in items:
                            item_encounters = item.get("encounter", [])
                            for enc_ref in item_encounters:
                                if encounter_id in enc_ref.get("reference", ""):
                                    has_match = True
                                    break
                            if has_match:
                                break

                    # For DocumentReference, check context.encounter[] array
                    if not has_match and resource_type == "DocumentReference":
                        context = resource.get("context", {})
                        context_encounters = context.get("encounter", [])
                        for enc_ref in context_encounters:
                            if encounter_id in enc_ref.get("reference", ""):
                                has_match = True
                                break

                    if not has_match:
                        match = False

                if match:
                    filtered.append(resource)

            return filtered

        return all_resources


async def test_encounter_metadata_extraction(encounter_id: str, bundle_path: str):
    """Test extraction of encounter metadata"""
    logger.info("TEST: Encounter Metadata Extraction", encounter_id=encounter_id)

    async with LocalFhirClient(bundle_path) as client:
        encounter_service = FhirEncounterService(client)

        # Fetch encounter
        encounter = await encounter_service.fetch_encounter_by_id(encounter_id)

        # Extract metadata
        metadata = encounter_service.extract_encounter_metadata(encounter)

        logger.info(
            "encounter_metadata_extracted",
            fhir_encounter_id=metadata["fhir_encounter_id"],
            fhir_patient_id=metadata["fhir_patient_id"],
            fhir_provider_id=metadata["fhir_provider_id"],
            date_of_service=metadata["date_of_service"],
            encounter_type=metadata["encounter_type"],
            encounter_class=metadata["encounter_class"],
            status=metadata["status"],
        )

        # Validate
        is_valid, error = encounter_service.validate_encounter_for_processing(encounter)
        logger.info("encounter_validation", is_valid=is_valid, error=error)

        return metadata


async def test_clinical_notes_extraction(encounter_id: str, bundle_path: str):
    """Test extraction of clinical notes from DocumentReference and Composition"""
    logger.info("TEST: Clinical Notes Extraction", encounter_id=encounter_id)

    async with LocalFhirClient(bundle_path) as client:
        note_service = FhirNoteService(client)

        # Search for clinical notes
        notes = await note_service.fetch_clinical_notes(encounter_id)

        logger.info("clinical_notes_found", count=len(notes))

        if notes:
            combined_text = note_service.combine_notes(notes)
            logger.info(
                "clinical_notes_combined",
                text_length=len(combined_text),
                text_preview=combined_text[:200] if combined_text else "No text",
            )
            return combined_text
        else:
            logger.warning("no_clinical_notes_found", encounter_id=encounter_id)
            return None


async def test_conditions_and_procedures(encounter_id: str, bundle_path: str):
    """Test retrieval of Conditions and Procedures for an encounter"""
    logger.info("TEST: Conditions and Procedures", encounter_id=encounter_id)

    async with LocalFhirClient(bundle_path) as client:
        # Search for conditions
        conditions = await client.search_resources(
            "Condition",
            {"encounter": f"Encounter/{encounter_id}"},
        )

        logger.info("conditions_found", count=len(conditions))
        for condition in conditions:
            code = condition.get("code", {}).get("coding", [{}])[0]
            logger.info(
                "condition",
                code=code.get("code"),
                display=code.get("display"),
                system=code.get("system"),
            )

        # Search for procedures
        procedures = await client.search_resources(
            "Procedure",
            {"encounter": f"Encounter/{encounter_id}"},
        )

        logger.info("procedures_found", count=len(procedures))
        for procedure in procedures:
            code = procedure.get("code", {}).get("coding", [{}])[0]
            logger.info(
                "procedure",
                code=code.get("code"),
                display=code.get("display"),
                system=code.get("system"),
            )

        return {
            "conditions": conditions,
            "procedures": procedures,
        }


async def test_phi_detection(clinical_text: str, patient_data: Dict[str, Any]):
    """Test PHI detection on clinical text (without database storage)"""
    logger.info("TEST: PHI Detection", text_length=len(clinical_text) if clinical_text else 0)

    if not clinical_text:
        logger.warning("no_clinical_text_for_phi_detection")
        return None

    # Run PHI detection directly (without database storage)
    result = phi_handler.detect_and_deidentify(clinical_text)

    logger.info(
        "phi_detection_complete",
        phi_detected=result.phi_detected,
        phi_count=len(result.phi_entities),
        deidentified_length=len(result.deidentified_text),
    )

    # Log PHI entities found
    logger.info("\nPHI Entities Detected:")
    for i, entity in enumerate(result.phi_entities[:15], 1):  # Show first 15
        logger.info(
            f"  {i}. PHI Entity",
            type=entity.type,
            text=entity.text,
            score=f"{entity.score:.3f}",
            category=entity.category,
        )

    # Show de-identified text preview
    logger.info("\nDe-identified Text Preview:")
    logger.info(result.deidentified_text[:500])

    return result


async def test_full_pipeline(encounter_id: str, bundle_path: str):
    """Test the complete FHIR processing pipeline"""
    logger.info("=" * 80)
    logger.info("TEST: Full FHIR Processing Pipeline")
    logger.info("=" * 80)

    # Step 1: Metadata Extraction
    logger.info("\n--- Step 1: Encounter Metadata Extraction ---")
    metadata = await test_encounter_metadata_extraction(encounter_id, bundle_path)

    # Step 2: Clinical Notes Extraction
    logger.info("\n--- Step 2: Clinical Notes Extraction ---")
    clinical_text = await test_clinical_notes_extraction(encounter_id, bundle_path)

    # Step 3: Conditions and Procedures
    logger.info("\n--- Step 3: Conditions and Procedures ---")
    clinical_data = await test_conditions_and_procedures(encounter_id, bundle_path)

    # Step 4: PHI Detection (if we have clinical text)
    if clinical_text:
        logger.info("\n--- Step 4: PHI Detection and Redaction ---")
        async with LocalFhirClient(bundle_path) as client:
            patient = await client.get_resource("Patient", metadata["fhir_patient_id"])
            phi_result = await test_phi_detection(clinical_text, patient)
    else:
        # Generate synthetic clinical note from encounter data
        logger.info("\n--- No DocumentReference found, generating synthetic note ---")
        clinical_text = generate_synthetic_note(metadata, clinical_data)
        logger.info("synthetic_note_generated", text_length=len(clinical_text))

        async with LocalFhirClient(bundle_path) as client:
            patient = await client.get_resource("Patient", metadata["fhir_patient_id"])
            phi_result = await test_phi_detection(clinical_text, patient)

    logger.info("\n" + "=" * 80)
    logger.info("Pipeline Test Complete")
    logger.info("=" * 80)


def generate_synthetic_note(metadata: Dict[str, Any], clinical_data: Dict[str, Any]) -> str:
    """Generate a synthetic clinical note from structured FHIR data"""
    lines = []

    lines.append("CLINICAL NOTE")
    lines.append("=" * 60)
    lines.append("")

    # Date of service
    if metadata.get("date_of_service"):
        lines.append(f"Date of Service: {metadata['date_of_service']}")

    # Provider
    if metadata.get("fhir_provider_id"):
        lines.append(f"Provider: {metadata['fhir_provider_id']}")

    lines.append("")
    lines.append("CHIEF COMPLAINT:")
    lines.append(f"{metadata.get('encounter_type', 'General visit')}")
    lines.append("")

    # Conditions/Diagnoses
    if clinical_data.get("conditions"):
        lines.append("ASSESSMENT:")
        for condition in clinical_data["conditions"]:
            code = condition.get("code", {}).get("coding", [{}])[0]
            display = code.get("display", "Unknown condition")
            lines.append(f"- {display}")
        lines.append("")

    # Procedures
    if clinical_data.get("procedures"):
        lines.append("PROCEDURES:")
        for procedure in clinical_data["procedures"]:
            code = procedure.get("code", {}).get("coding", [{}])[0]
            display = code.get("display", "Unknown procedure")
            lines.append(f"- {display}")
        lines.append("")

    lines.append("PLAN:")
    lines.append("- Continue current treatment")
    lines.append("- Follow up as needed")

    return "\n".join(lines)


async def main():
    """Main test runner"""
    # Configuration
    BUNDLE_PATH = "/Users/alexander/code/revrx/synthetic_data/synthea_fhir4_100/Adam631_Gusikowski974_296e9f96-4897-f44b-39d3-1127e65f9e80.json"
    ENCOUNTER_ID = "296e9f96-4897-f44b-851e-f3731baf64d8"

    logger.info("Starting FHIR Local Testing")
    logger.info("Bundle:", bundle_path=BUNDLE_PATH)
    logger.info("Encounter ID:", encounter_id=ENCOUNTER_ID)

    try:
        # Connect to database
        await prisma.connect()
        logger.info("Database connected")

        # Run full pipeline test
        await test_full_pipeline(ENCOUNTER_ID, BUNDLE_PATH)

    except Exception as e:
        logger.error("Test failed", error=str(e), exc_info=True)
        raise
    finally:
        # Cleanup
        await prisma.disconnect()
        logger.info("Database disconnected")


if __name__ == "__main__":
    asyncio.run(main())
