"""
Amazon Comprehend Medical Service
Handles PHI detection and medical entity extraction from clinical notes
"""

from typing import List, Dict, Any, Optional
import structlog
import boto3
from botocore.exceptions import ClientError, BotoCoreError

from app.core.config import settings


logger = structlog.get_logger(__name__)


class PHIEntity:
    """Represents a detected PHI entity"""

    def __init__(
        self,
        text: str,
        category: str,
        type: str,
        score: float,
        begin_offset: int,
        end_offset: int,
        traits: Optional[List[Dict]] = None
    ):
        self.text = text
        self.category = category  # e.g., "PROTECTED_HEALTH_INFORMATION"
        self.type = type  # e.g., "NAME", "DATE", "ID", "PHONE_OR_FAX"
        self.score = score  # Confidence score 0-1
        self.begin_offset = begin_offset
        self.end_offset = end_offset
        self.traits = traits or []

    def __repr__(self):
        return f"PHIEntity(text='{self.text}', type={self.type}, score={self.score:.3f})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "text": self.text,
            "category": self.category,
            "type": self.type,
            "score": self.score,
            "begin_offset": self.begin_offset,
            "end_offset": self.end_offset,
            "traits": self.traits,
        }


class ICD10Entity:
    """Represents an ICD-10-CM code extracted from clinical text"""

    def __init__(
        self,
        code: str,
        description: str,
        score: float,
        text: str,
        begin_offset: int,
        end_offset: int,
        category: str,
        type: str,
        traits: Optional[List[Dict]] = None,
        attributes: Optional[List[Dict]] = None,
        icd10_cm_concepts: Optional[List[Dict]] = None
    ):
        self.code = code  # ICD-10-CM code (e.g., "M54.5")
        self.description = description  # Human-readable description
        self.score = score  # Confidence score 0-1
        self.text = text  # Original text that triggered this code
        self.begin_offset = begin_offset  # Offset in original text
        self.end_offset = end_offset
        self.category = category  # e.g., "MEDICAL_CONDITION"
        self.type = type  # e.g., "DX_NAME"
        self.traits = traits or []
        self.attributes = attributes or []
        self.icd10_cm_concepts = icd10_cm_concepts or []  # Multiple possible codes

    def __repr__(self):
        return f"ICD10Entity(code='{self.code}', description='{self.description}', score={self.score:.3f})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "code": self.code,
            "description": self.description,
            "score": self.score,
            "text": self.text,
            "begin_offset": self.begin_offset,
            "end_offset": self.end_offset,
            "category": self.category,
            "type": self.type,
            "traits": self.traits,
            "attributes": self.attributes,
            "icd10_cm_concepts": self.icd10_cm_concepts,
        }


class SNOMEDEntity:
    """Represents a SNOMED CT procedure code extracted from clinical text"""

    def __init__(
        self,
        code: str,
        description: str,
        score: float,
        text: str,
        begin_offset: int,
        end_offset: int,
        category: str,
        type: str,
        traits: Optional[List[Dict]] = None,
        attributes: Optional[List[Dict]] = None,
        snomed_ct_concepts: Optional[List[Dict]] = None
    ):
        self.code = code  # SNOMED CT code (e.g., "241607001")
        self.description = description  # Human-readable description
        self.score = score  # Confidence score 0-1
        self.text = text  # Original text that triggered this code
        self.begin_offset = begin_offset  # Offset in original text
        self.end_offset = end_offset
        self.category = category  # e.g., "TEST_TREATMENT_PROCEDURE"
        self.type = type  # e.g., "PROCEDURE_NAME"
        self.traits = traits or []
        self.attributes = attributes or []
        self.snomed_ct_concepts = snomed_ct_concepts or []  # Multiple possible codes

    def __repr__(self):
        return f"SNOMEDEntity(code='{self.code}', description='{self.description}', score={self.score:.3f})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "code": self.code,
            "description": self.description,
            "score": self.score,
            "text": self.text,
            "begin_offset": self.begin_offset,
            "end_offset": self.end_offset,
            "category": self.category,
            "type": self.type,
            "traits": self.traits,
            "attributes": self.attributes,
            "snomed_ct_concepts": self.snomed_ct_concepts,
        }


class MedicalEntity:
    """Represents a detected medical entity"""

    def __init__(
        self,
        text: str,
        category: str,
        type: str,
        score: float,
        begin_offset: int,
        end_offset: int,
        attributes: Optional[List[Dict]] = None,
        traits: Optional[List[Dict]] = None
    ):
        self.text = text
        self.category = category  # e.g., "MEDICAL_CONDITION", "MEDICATION"
        self.type = type  # e.g., "DX_NAME", "GENERIC_NAME"
        self.score = score
        self.begin_offset = begin_offset
        self.end_offset = end_offset
        self.attributes = attributes or []
        self.traits = traits or []

    def __repr__(self):
        return f"MedicalEntity(text='{self.text}', category={self.category}, type={self.type})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "text": self.text,
            "category": self.category,
            "type": self.type,
            "score": self.score,
            "begin_offset": self.begin_offset,
            "end_offset": self.end_offset,
            "attributes": self.attributes,
            "traits": self.traits,
        }


class ComprehendMedicalService:
    """
    Service for interacting with Amazon Comprehend Medical API
    Detects PHI and medical entities in clinical text
    """

    def __init__(self):
        """Initialize Comprehend Medical client"""
        try:
            self.client = boto3.client(
                "comprehendmedical",
                region_name=settings.AWS_COMPREHEND_MEDICAL_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            logger.info(
                "Comprehend Medical client initialized",
                region=settings.AWS_COMPREHEND_MEDICAL_REGION
            )
        except Exception as e:
            logger.error("Failed to initialize Comprehend Medical client", error=str(e))
            raise

    def detect_phi(self, text: str) -> List[PHIEntity]:
        """
        Detect Protected Health Information (PHI) in clinical text

        Uses Amazon Comprehend Medical DetectPHI API to identify:
        - Patient names
        - Dates (birth dates, admission dates)
        - Phone numbers and fax numbers
        - Email addresses
        - Medical record numbers
        - Social security numbers
        - Account numbers
        - License numbers
        - URLs
        - IP addresses
        - Locations (addresses, cities, states, zip codes)

        Args:
            text: Clinical text to analyze (max 20,000 bytes)

        Returns:
            List of PHIEntity objects

        Raises:
            ValueError: If text is empty or too large
            ClientError: If AWS API call fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Check size limit (20KB for Comprehend Medical)
        text_bytes = len(text.encode('utf-8'))
        if text_bytes > 20000:
            raise ValueError(f"Text too large: {text_bytes} bytes (max 20000)")

        try:
            logger.info("Detecting PHI", text_length=len(text), text_bytes=text_bytes)

            response = self.client.detect_phi(Text=text)

            entities = []
            for entity_data in response.get("Entities", []):
                entity = PHIEntity(
                    text=entity_data.get("Text", ""),
                    category=entity_data.get("Category", ""),
                    type=entity_data.get("Type", ""),
                    score=entity_data.get("Score", 0.0),
                    begin_offset=entity_data.get("BeginOffset", 0),
                    end_offset=entity_data.get("EndOffset", 0),
                    traits=entity_data.get("Traits", []),
                )
                entities.append(entity)

            logger.info(
                "PHI detection completed",
                entity_count=len(entities),
                model_version=response.get("ModelVersion"),
            )

            return entities

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(
                "AWS Comprehend Medical API error",
                error_code=error_code,
                error_message=error_message,
            )
            raise

        except Exception as e:
            logger.error("Unexpected error during PHI detection", error=str(e))
            raise

    def infer_icd10_cm(self, text: str) -> List[ICD10Entity]:
        """
        Infer ICD-10-CM codes from clinical text

        Uses Amazon Comprehend Medical InferICD10CM API to identify:
        - ICD-10-CM diagnosis codes
        - Associated confidence scores
        - Text snippets that support each code
        - Multiple code suggestions per entity

        Args:
            text: Clinical text to analyze (max 10,000 bytes)

        Returns:
            List of ICD10Entity objects with codes and descriptions

        Raises:
            ValueError: If text is empty or too large
            ClientError: If AWS API call fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Check size limit (10KB for InferICD10CM)
        text_bytes = len(text.encode('utf-8'))
        if text_bytes > 10000:
            raise ValueError(f"Text too large: {text_bytes} bytes (max 10000)")

        try:
            logger.info(
                "Inferring ICD-10-CM codes",
                text_length=len(text),
                text_bytes=text_bytes
            )

            response = self.client.infer_icd10_cm(Text=text)

            entities = []
            for entity_data in response.get("Entities", []):
                # Get the top ICD-10-CM concept (highest confidence)
                icd10_concepts = entity_data.get("ICD10CMConcepts", [])

                if not icd10_concepts:
                    # Skip entities without ICD-10 codes
                    continue

                # Use the first (highest confidence) code as primary
                top_concept = icd10_concepts[0]

                entity = ICD10Entity(
                    code=top_concept.get("Code", ""),
                    description=top_concept.get("Description", ""),
                    score=top_concept.get("Score", 0.0),
                    text=entity_data.get("Text", ""),
                    begin_offset=entity_data.get("BeginOffset", 0),
                    end_offset=entity_data.get("EndOffset", 0),
                    category=entity_data.get("Category", ""),
                    type=entity_data.get("Type", ""),
                    traits=entity_data.get("Traits", []),
                    attributes=entity_data.get("Attributes", []),
                    icd10_cm_concepts=icd10_concepts,  # Store all suggested codes
                )
                entities.append(entity)

            logger.info(
                "ICD-10-CM inference completed",
                entity_count=len(entities),
                total_entities_in_response=len(response.get("Entities", [])),
                model_version=response.get("ModelVersion"),
            )

            return entities

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(
                "AWS Comprehend Medical API error (InferICD10CM)",
                error_code=error_code,
                error_message=error_message,
            )
            raise

        except Exception as e:
            logger.error("Unexpected error during ICD-10-CM inference", error=str(e))
            raise

    def infer_snomed_ct(self, text: str) -> List[SNOMEDEntity]:
        """
        Infer SNOMED CT procedure codes from clinical text

        Uses Amazon Comprehend Medical InferSNOMEDCT API to identify:
        - SNOMED CT procedure codes
        - Associated confidence scores
        - Text snippets that support each code
        - Multiple code suggestions per entity

        Args:
            text: Clinical text to analyze (max 10,000 bytes)

        Returns:
            List of SNOMEDEntity objects with codes and descriptions

        Raises:
            ValueError: If text is empty or too large
            ClientError: If AWS API call fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Check size limit (10KB for InferSNOMEDCT)
        text_bytes = len(text.encode('utf-8'))
        if text_bytes > 10000:
            raise ValueError(f"Text too large: {text_bytes} bytes (max 10000)")

        try:
            logger.info(
                "Inferring SNOMED CT codes",
                text_length=len(text),
                text_bytes=text_bytes
            )

            response = self.client.infer_snomedct(Text=text)

            entities = []
            for entity_data in response.get("Entities", []):
                # Get the SNOMED CT concepts
                snomed_concepts = entity_data.get("SNOMEDCTConcepts", [])

                if not snomed_concepts:
                    # Skip entities without SNOMED codes
                    continue

                # Use the first (highest confidence) code as primary
                top_concept = snomed_concepts[0]

                entity = SNOMEDEntity(
                    code=top_concept.get("Code", ""),
                    description=top_concept.get("Description", ""),
                    score=top_concept.get("Score", 0.0),
                    text=entity_data.get("Text", ""),
                    begin_offset=entity_data.get("BeginOffset", 0),
                    end_offset=entity_data.get("EndOffset", 0),
                    category=entity_data.get("Category", ""),
                    type=entity_data.get("Type", ""),
                    traits=entity_data.get("Traits", []),
                    attributes=entity_data.get("Attributes", []),
                    snomed_ct_concepts=snomed_concepts,  # Store all suggested codes
                )
                entities.append(entity)

            logger.info(
                "SNOMED CT inference completed",
                entity_count=len(entities),
                total_entities_in_response=len(response.get("Entities", [])),
                model_version=response.get("ModelVersion"),
            )

            return entities

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(
                "AWS Comprehend Medical API error (InferSNOMEDCT)",
                error_code=error_code,
                error_message=error_message,
            )
            raise

        except Exception as e:
            logger.error("Unexpected error during SNOMED CT inference", error=str(e))
            raise

    def detect_entities_v2(self, text: str) -> List[MedicalEntity]:
        """
        Detect medical entities in clinical text

        Uses Amazon Comprehend Medical DetectEntities-v2 API to identify:
        - Medical conditions (diagnoses, symptoms, signs)
        - Medications (generic names, brand names, dosages)
        - Tests, treatments, and procedures
        - Anatomy (body parts, systems)
        - Time expressions related to medical events

        Args:
            text: Clinical text to analyze (max 20,000 bytes)

        Returns:
            List of MedicalEntity objects

        Raises:
            ValueError: If text is empty or too large
            ClientError: If AWS API call fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Check size limit
        text_bytes = len(text.encode('utf-8'))
        if text_bytes > 20000:
            raise ValueError(f"Text too large: {text_bytes} bytes (max 20000)")

        try:
            logger.info(
                "Detecting medical entities",
                text_length=len(text),
                text_bytes=text_bytes
            )

            response = self.client.detect_entities_v2(Text=text)

            entities = []
            for entity_data in response.get("Entities", []):
                entity = MedicalEntity(
                    text=entity_data.get("Text", ""),
                    category=entity_data.get("Category", ""),
                    type=entity_data.get("Type", ""),
                    score=entity_data.get("Score", 0.0),
                    begin_offset=entity_data.get("BeginOffset", 0),
                    end_offset=entity_data.get("EndOffset", 0),
                    attributes=entity_data.get("Attributes", []),
                    traits=entity_data.get("Traits", []),
                )
                entities.append(entity)

            logger.info(
                "Medical entity detection completed",
                entity_count=len(entities),
                model_version=response.get("ModelVersion"),
            )

            return entities

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(
                "AWS Comprehend Medical API error",
                error_code=error_code,
                error_message=error_message,
            )
            raise

        except Exception as e:
            logger.error("Unexpected error during medical entity detection", error=str(e))
            raise

    def analyze_text(
        self, text: str
    ) -> Dict[str, Any]:
        """
        Comprehensive analysis: detect both PHI and medical entities

        Args:
            text: Clinical text to analyze

        Returns:
            Dictionary containing:
            - phi_entities: List of PHI entities
            - medical_entities: List of medical entities
            - phi_detected: Boolean indicating if PHI was found
            - phi_count: Number of PHI entities detected
            - medical_entity_count: Number of medical entities detected

        Raises:
            ValueError: If text is invalid
            ClientError: If AWS API call fails
        """
        try:
            # Detect PHI
            phi_entities = self.detect_phi(text)

            # Detect medical entities
            medical_entities = self.detect_entities_v2(text)

            result = {
                "phi_entities": [entity.to_dict() for entity in phi_entities],
                "medical_entities": [entity.to_dict() for entity in medical_entities],
                "phi_detected": len(phi_entities) > 0,
                "phi_count": len(phi_entities),
                "medical_entity_count": len(medical_entities),
            }

            logger.info(
                "Text analysis completed",
                phi_count=result["phi_count"],
                medical_entity_count=result["medical_entity_count"],
            )

            return result

        except Exception as e:
            logger.error("Error during text analysis", error=str(e))
            raise

    def get_phi_by_type(self, phi_entities: List[PHIEntity]) -> Dict[str, List[PHIEntity]]:
        """
        Group PHI entities by type

        Args:
            phi_entities: List of PHI entities

        Returns:
            Dictionary mapping PHI type to list of entities
        """
        phi_by_type = {}
        for entity in phi_entities:
            if entity.type not in phi_by_type:
                phi_by_type[entity.type] = []
            phi_by_type[entity.type].append(entity)

        return phi_by_type

    def get_medical_entities_by_category(
        self, medical_entities: List[MedicalEntity]
    ) -> Dict[str, List[MedicalEntity]]:
        """
        Group medical entities by category

        Args:
            medical_entities: List of medical entities

        Returns:
            Dictionary mapping category to list of entities
        """
        entities_by_category = {}
        for entity in medical_entities:
            if entity.category not in entities_by_category:
                entities_by_category[entity.category] = []
            entities_by_category[entity.category].append(entity)

        return entities_by_category


# Export singleton instance
comprehend_medical_service = ComprehendMedicalService()
