"""
FHIR Encounter Service
Handles retrieval and metadata extraction from FHIR Encounter resources
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import structlog

from app.services.fhir.fhir_client import FhirClient, FhirClientError

logger = structlog.get_logger(__name__)


class FhirEncounterService:
    """
    Service for working with FHIR Encounter resources

    Handles:
    - Fetching encounters from FHIR API
    - Extracting encounter metadata (patient, provider, date of service)
    - Normalizing encounter data for downstream processing
    """

    def __init__(self, fhir_client: FhirClient):
        """
        Initialize encounter service

        Args:
            fhir_client: Configured FhirClient instance
        """
        self.fhir_client = fhir_client

    async def fetch_encounter_by_id(self, encounter_id: str) -> Dict[str, Any]:
        """
        Fetch a single FHIR Encounter by ID

        Args:
            encounter_id: FHIR Encounter ID

        Returns:
            FHIR Encounter resource as dict

        Raises:
            FhirClientError: If fetch fails
        """
        logger.info("fetch_fhir_encounter", encounter_id=encounter_id)

        try:
            encounter = await self.fhir_client.get_resource("Encounter", encounter_id)

            logger.info(
                "fetch_fhir_encounter_success",
                encounter_id=encounter_id,
                status=encounter.get("status"),
            )

            return encounter

        except FhirClientError as e:
            logger.error(
                "fetch_fhir_encounter_failed",
                encounter_id=encounter_id,
                error=str(e),
            )
            raise

    async def fetch_encounters(
        self,
        patient_id: Optional[str] = None,
        date_range: Optional[Tuple[str, str]] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch FHIR Encounters matching search criteria

        Args:
            patient_id: Filter by patient ID (e.g., "Patient/123")
            date_range: Filter by date range as (start_date, end_date) in ISO format
            status: Filter by status (e.g., "finished")
            limit: Maximum number of encounters to return

        Returns:
            List of FHIR Encounter resources

        Raises:
            FhirClientError: If search fails
        """
        logger.info(
            "fetch_fhir_encounters",
            patient_id=patient_id,
            date_range=date_range,
            status=status,
            limit=limit,
        )

        # Build search parameters
        params: Dict[str, Any] = {}

        if patient_id:
            params["patient"] = patient_id

        if date_range:
            start_date, end_date = date_range
            params["date"] = f"ge{start_date}"
            if end_date:
                params["date"] = f"ge{start_date}&date=le{end_date}"

        if status:
            params["status"] = status

        if limit:
            params["_count"] = limit

        try:
            encounters = await self.fhir_client.search_resources("Encounter", params)

            logger.info(
                "fetch_fhir_encounters_success",
                count=len(encounters),
                patient_id=patient_id,
            )

            return encounters

        except FhirClientError as e:
            logger.error(
                "fetch_fhir_encounters_failed",
                patient_id=patient_id,
                error=str(e),
            )
            raise

    def extract_encounter_metadata(self, encounter: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract standardized metadata from FHIR Encounter resource

        Extracts:
        - Patient ID
        - Provider ID
        - Date of Service
        - Encounter type
        - Encounter status

        Args:
            encounter: FHIR Encounter resource

        Returns:
            Dictionary with extracted metadata
        """
        encounter_id = encounter.get("id")

        logger.info("extract_encounter_metadata", encounter_id=encounter_id)

        metadata = {
            "fhir_encounter_id": encounter_id,
            "fhir_patient_id": self._extract_patient_id(encounter),
            "fhir_provider_id": self._extract_provider_id(encounter),
            "date_of_service": self._extract_date_of_service(encounter),
            "encounter_type": self._extract_encounter_type(encounter),
            "encounter_class": self._extract_encounter_class(encounter),
            "status": encounter.get("status"),
            "raw_encounter": encounter,
        }

        logger.info(
            "extract_encounter_metadata_success",
            encounter_id=encounter_id,
            patient_id=metadata["fhir_patient_id"],
            provider_id=metadata["fhir_provider_id"],
            date_of_service=metadata["date_of_service"],
        )

        return metadata

    def _extract_patient_id(self, encounter: Dict[str, Any]) -> Optional[str]:
        """
        Extract patient ID from encounter.subject.reference

        FHIR format: {"reference": "Patient/123"} or {"reference": "http://...Patient/123"}

        Args:
            encounter: FHIR Encounter resource

        Returns:
            Patient ID or None
        """
        try:
            subject = encounter.get("subject", {})
            reference = subject.get("reference", "")

            if not reference:
                logger.warning("extract_patient_id_missing", encounter_id=encounter.get("id"))
                return None

            # Handle both relative and absolute references
            # "Patient/123" or "http://fhir.example.com/Patient/123"
            if "/" in reference:
                patient_id = reference.split("/")[-1]
                return patient_id

            return reference

        except Exception as e:
            logger.error(
                "extract_patient_id_error",
                encounter_id=encounter.get("id"),
                error=str(e),
            )
            return None

    def _extract_provider_id(self, encounter: Dict[str, Any]) -> Optional[str]:
        """
        Extract provider ID from encounter.participant[].individual.reference

        Looks for participant with type "practitioner" or "primary performer"

        Args:
            encounter: FHIR Encounter resource

        Returns:
            Provider/Practitioner ID or None
        """
        try:
            participants = encounter.get("participant", [])

            if not participants:
                logger.warning(
                    "extract_provider_id_no_participants",
                    encounter_id=encounter.get("id"),
                )
                return None

            # Try to find primary practitioner
            for participant in participants:
                # Check if participant has individual reference
                individual = participant.get("individual", {})
                reference = individual.get("reference", "")

                if not reference:
                    continue

                # Check if this is a practitioner
                if "Practitioner" in reference:
                    # Check for primary performer type
                    types = participant.get("type", [])
                    for type_coding in types:
                        codings = type_coding.get("coding", [])
                        for coding in codings:
                            if coding.get("code") in ("PPRF", "ATND", "primary"):
                                # Primary performer found
                                provider_id = reference.split("/")[-1]
                                return provider_id

                    # If no specific type, use first practitioner
                    provider_id = reference.split("/")[-1]
                    return provider_id

            # Fallback: use first participant with individual reference
            for participant in participants:
                individual = participant.get("individual", {})
                reference = individual.get("reference", "")
                if reference:
                    provider_id = reference.split("/")[-1]
                    logger.info(
                        "extract_provider_id_fallback",
                        encounter_id=encounter.get("id"),
                        provider_id=provider_id,
                    )
                    return provider_id

            logger.warning(
                "extract_provider_id_not_found",
                encounter_id=encounter.get("id"),
            )
            return None

        except Exception as e:
            logger.error(
                "extract_provider_id_error",
                encounter_id=encounter.get("id"),
                error=str(e),
            )
            return None

    def _extract_date_of_service(self, encounter: Dict[str, Any]) -> Optional[str]:
        """
        Extract date of service from encounter.period.start

        Args:
            encounter: FHIR Encounter resource

        Returns:
            ISO 8601 date string (YYYY-MM-DD) or None
        """
        try:
            period = encounter.get("period", {})
            start_datetime = period.get("start")

            if not start_datetime:
                logger.warning(
                    "extract_date_of_service_missing",
                    encounter_id=encounter.get("id"),
                )
                return None

            # Parse ISO datetime and extract date
            # FHIR uses ISO 8601: "2024-01-15T10:30:00Z"
            if "T" in start_datetime:
                date_part = start_datetime.split("T")[0]
            else:
                date_part = start_datetime

            return date_part

        except Exception as e:
            logger.error(
                "extract_date_of_service_error",
                encounter_id=encounter.get("id"),
                error=str(e),
            )
            return None

    def _extract_encounter_type(self, encounter: Dict[str, Any]) -> Optional[str]:
        """
        Extract encounter type from encounter.type

        Args:
            encounter: FHIR Encounter resource

        Returns:
            Human-readable encounter type or None
        """
        try:
            types = encounter.get("type", [])

            if not types:
                return None

            # Get first type coding
            first_type = types[0]
            codings = first_type.get("coding", [])

            if not codings:
                # Try text if no coding
                return first_type.get("text")

            # Get display or code from first coding
            first_coding = codings[0]
            return first_coding.get("display") or first_coding.get("code")

        except Exception as e:
            logger.error(
                "extract_encounter_type_error",
                encounter_id=encounter.get("id"),
                error=str(e),
            )
            return None

    def _extract_encounter_class(self, encounter: Dict[str, Any]) -> Optional[str]:
        """
        Extract encounter class (inpatient, outpatient, emergency, etc.)

        Args:
            encounter: FHIR Encounter resource

        Returns:
            Encounter class display or code
        """
        try:
            class_element = encounter.get("class", {})

            if not class_element:
                return None

            # Handle both FHIR R4 and R5 formats
            if isinstance(class_element, dict):
                # R4: class is a Coding
                return class_element.get("display") or class_element.get("code")
            elif isinstance(class_element, list):
                # R5: class is an array of CodeableConcept
                if class_element:
                    first_class = class_element[0]
                    codings = first_class.get("coding", [])
                    if codings:
                        return codings[0].get("display") or codings[0].get("code")

            return None

        except Exception as e:
            logger.error(
                "extract_encounter_class_error",
                encounter_id=encounter.get("id"),
                error=str(e),
            )
            return None

    def validate_encounter_for_processing(self, encounter: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate that encounter has minimum required data for processing

        Args:
            encounter: FHIR Encounter resource

        Returns:
            Tuple of (is_valid, error_message)
        """
        encounter_id = encounter.get("id")

        if not encounter_id:
            return False, "Encounter missing ID"

        metadata = self.extract_encounter_metadata(encounter)

        # Check for required fields
        if not metadata["fhir_patient_id"]:
            return False, f"Encounter {encounter_id} missing patient reference"

        if not metadata["date_of_service"]:
            logger.warning(
                "validate_encounter_missing_date",
                encounter_id=encounter_id,
                message="Date of service missing - will fallback to LLM extraction",
            )
            # Date can be extracted by LLM later, so not a blocker

        if not metadata["fhir_provider_id"]:
            logger.warning(
                "validate_encounter_missing_provider",
                encounter_id=encounter_id,
                message="Provider missing - will fallback to LLM extraction",
            )
            # Provider can be extracted by LLM later, so not a blocker

        logger.info(
            "validate_encounter_success",
            encounter_id=encounter_id,
        )

        return True, None
