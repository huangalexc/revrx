"""
FHIR Claims Service
Handles retrieval and extraction of billing codes from FHIR Claim resources
"""

from typing import Dict, List, Any, Optional
import structlog

from app.services.fhir.fhir_client import FhirClient, FhirClientError

logger = structlog.get_logger(__name__)


class FhirClaimsService:
    """
    Service for working with FHIR Claim resources

    Handles:
    - Fetching claims for an encounter
    - Extracting billing codes (CPT, ICD-10, HCPCS) from claims
    - Normalizing claim data for downstream processing
    """

    def __init__(self, fhir_client: FhirClient):
        """
        Initialize claims service

        Args:
            fhir_client: Configured FhirClient instance
        """
        self.fhir_client = fhir_client

    async def fetch_claims_for_encounter(
        self,
        encounter_id: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch all FHIR Claims associated with an encounter

        Args:
            encounter_id: FHIR Encounter ID (e.g., "Encounter/123")

        Returns:
            List of FHIR Claim resources

        Raises:
            FhirClientError: If fetch fails
        """
        logger.info("fetch_fhir_claims_for_encounter", encounter_id=encounter_id)

        try:
            # Search for claims by encounter reference
            # FHIR search: GET [base]/Claim?encounter=Encounter/123
            search_params = {
                "encounter": encounter_id if encounter_id.startswith("Encounter/") else f"Encounter/{encounter_id}"
            }

            claims = await self.fhir_client.search_resources("Claim", search_params)

            logger.info(
                "fetch_fhir_claims_success",
                encounter_id=encounter_id,
                claim_count=len(claims),
            )

            return claims

        except FhirClientError as e:
            logger.error(
                "fetch_fhir_claims_failed",
                encounter_id=encounter_id,
                error=str(e),
            )
            # Don't raise - return empty list if claims not found
            # (Not all encounters have claims in the EHR yet)
            return []

    def extract_billing_codes_from_claim(
        self,
        claim: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract billing codes from a FHIR Claim resource

        FHIR Claim structure:
        - diagnosis[].diagnosisCodeableConcept: ICD-10 codes
        - procedure[].procedureCodeableConcept: CPT/HCPCS codes
        - item[].productOrService: CPT/HCPCS codes (alternate location)

        Args:
            claim: FHIR Claim resource as dict

        Returns:
            List of dicts with keys: code, code_type, description
        """
        codes = []

        # Extract ICD-10 diagnosis codes
        diagnoses = claim.get("diagnosis", [])
        for diagnosis in diagnoses:
            diagnosis_codeable = diagnosis.get("diagnosisCodeableConcept", {})
            codings = diagnosis_codeable.get("coding", [])

            for coding in codings:
                # Check if this is an ICD-10 code
                system = coding.get("system", "")
                if "icd-10" in system.lower() or "icd10" in system.lower():
                    code = coding.get("code")
                    display = coding.get("display")

                    if code:
                        codes.append({
                            "code": code.replace(".", ""),  # Normalize: remove dots
                            "code_type": "ICD10",
                            "description": display,
                        })

        # Extract CPT/HCPCS procedure codes
        procedures = claim.get("procedure", [])
        for procedure in procedures:
            procedure_codeable = procedure.get("procedureCodeableConcept", {})
            codings = procedure_codeable.get("coding", [])

            for coding in codings:
                system = coding.get("system", "")
                code = coding.get("code")
                display = coding.get("display")

                if not code:
                    continue

                # Determine code type based on system URL or code pattern
                code_type = self._determine_code_type(system, code)

                if code_type:
                    codes.append({
                        "code": code,
                        "code_type": code_type,
                        "description": display,
                    })

        # Extract codes from claim items (alternate location)
        items = claim.get("item", [])
        for item in items:
            product_or_service = item.get("productOrService", {})
            codings = product_or_service.get("coding", [])

            for coding in codings:
                system = coding.get("system", "")
                code = coding.get("code")
                display = coding.get("display")

                if not code:
                    continue

                code_type = self._determine_code_type(system, code)

                if code_type:
                    codes.append({
                        "code": code,
                        "code_type": code_type,
                        "description": display,
                    })

        # Deduplicate by (code, code_type)
        seen = set()
        unique_codes = []
        for code_dict in codes:
            key = (code_dict["code"], code_dict["code_type"])
            if key not in seen:
                seen.add(key)
                unique_codes.append(code_dict)

        logger.debug(
            "billing_codes_extracted_from_claim",
            claim_id=claim.get("id"),
            code_count=len(unique_codes),
            cpt_count=len([c for c in unique_codes if c["code_type"] == "CPT"]),
            icd10_count=len([c for c in unique_codes if c["code_type"] == "ICD10"]),
            hcpcs_count=len([c for c in unique_codes if c["code_type"] == "HCPCS"]),
        )

        return unique_codes

    def _determine_code_type(self, system: str, code: str) -> Optional[str]:
        """
        Determine code type (CPT, ICD10, HCPCS) from FHIR coding system URL or code pattern

        Args:
            system: FHIR coding system URL (e.g., "http://www.ama-assn.org/go/cpt")
            code: The code value

        Returns:
            Code type string ("CPT", "ICD10", "HCPCS") or None if unknown
        """
        system_lower = system.lower()

        # Check system URL first
        if "cpt" in system_lower or "ama-assn" in system_lower:
            return "CPT"
        elif "icd-10" in system_lower or "icd10" in system_lower:
            return "ICD10"
        elif "hcpcs" in system_lower:
            return "HCPCS"

        # Fallback: Infer from code pattern
        # CPT: 5-digit numeric (e.g., 99393, 99214)
        if code.isdigit() and len(code) == 5:
            return "CPT"

        # ICD-10: Letter + digits (e.g., Z00.129, Z00129)
        if len(code) >= 3 and code[0].isalpha() and code[1:3].isdigit():
            return "ICD10"

        # HCPCS: Letter + 4 digits (e.g., J0585, A0426)
        if len(code) == 5 and code[0].isalpha() and code[1:].isdigit():
            return "HCPCS"

        logger.warning(
            "unknown_code_type",
            system=system,
            code=code,
        )
        return None

    async def extract_billing_codes_for_encounter(
        self,
        encounter_id: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch all claims for an encounter and extract billing codes

        Args:
            encounter_id: FHIR Encounter ID

        Returns:
            List of dicts with keys: code, code_type, description
        """
        logger.info(
            "extract_billing_codes_for_encounter_start",
            encounter_id=encounter_id
        )

        # Fetch claims
        claims = await self.fetch_claims_for_encounter(encounter_id)

        if not claims:
            logger.info(
                "no_claims_found_for_encounter",
                encounter_id=encounter_id
            )
            return []

        # Extract codes from all claims
        all_codes = []
        for claim in claims:
            codes = self.extract_billing_codes_from_claim(claim)
            all_codes.extend(codes)

        # Deduplicate across all claims
        seen = set()
        unique_codes = []
        for code_dict in all_codes:
            key = (code_dict["code"], code_dict["code_type"])
            if key not in seen:
                seen.add(key)
                unique_codes.append(code_dict)

        logger.info(
            "billing_codes_extracted_for_encounter",
            encounter_id=encounter_id,
            claim_count=len(claims),
            total_code_count=len(unique_codes),
            cpt_count=len([c for c in unique_codes if c["code_type"] == "CPT"]),
            icd10_count=len([c for c in unique_codes if c["code_type"] == "ICD10"]),
            hcpcs_count=len([c for c in unique_codes if c["code_type"] == "HCPCS"]),
        )

        return unique_codes
