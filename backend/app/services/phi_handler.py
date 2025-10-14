"""
PHI Handler Service
De-identifies PHI from clinical notes and provides reversible masking
"""

from typing import Dict, List, Tuple, Optional, Any
import structlog
from datetime import datetime
import uuid

from app.services.comprehend_medical import (
    comprehend_medical_service,
    PHIEntity,
)
from app.core.encryption import encryption_service
from app.core.database import prisma


logger = structlog.get_logger(__name__)


class PHIMapping:
    """Represents a mapping between original PHI and its token"""

    def __init__(self, original: str, token: str, entity_type: str, index: int):
        self.original = original
        self.token = token
        self.entity_type = entity_type
        self.index = index  # Index in case of duplicate types

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original,
            "token": self.token,
            "entity_type": self.entity_type,
            "index": self.index,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PHIMapping":
        return PHIMapping(
            original=data["original"],
            token=data["token"],
            entity_type=data["entity_type"],
            index=data["index"],
        )


class DeidentificationResult:
    """Result of PHI de-identification process"""

    def __init__(
        self,
        original_text: str,
        deidentified_text: str,
        phi_entities: List[PHIEntity],
        phi_mappings: List[PHIMapping],
        phi_detected: bool,
    ):
        self.original_text = original_text
        self.deidentified_text = deidentified_text
        self.phi_entities = phi_entities
        self.phi_mappings = phi_mappings
        self.phi_detected = phi_detected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deidentified_text": self.deidentified_text,
            "phi_detected": self.phi_detected,
            "phi_count": len(self.phi_entities),
            "phi_entities": [e.to_dict() for e in self.phi_entities],
            "phi_mappings": [m.to_dict() for m in self.phi_mappings],
        }


class PHIHandler:
    """
    Service for handling PHI detection and de-identification

    Provides:
    - PHI detection using Amazon Comprehend Medical
    - Reversible de-identification with token replacement
    - Encrypted storage of PHI mappings
    - Re-identification for report generation
    """

    def __init__(self):
        self.comprehend = comprehend_medical_service
        self.encryption = encryption_service

    def detect_and_deidentify(self, text: str) -> DeidentificationResult:
        """
        Detect PHI and create de-identified version of text

        Args:
            text: Clinical note text

        Returns:
            DeidentificationResult with masked text and mappings

        Process:
        1. Detect PHI using Comprehend Medical
        2. Sort entities by offset (reverse order for replacement)
        3. Replace each PHI entity with a token like [NAME_1], [DATE_1]
        4. Create mapping of tokens to original values
        """
        logger.info("Starting PHI detection and de-identification", text_length=len(text))

        # Detect PHI entities
        phi_entities = self.comprehend.detect_phi(text)

        if not phi_entities:
            logger.info("No PHI detected in text")
            return DeidentificationResult(
                original_text=text,
                deidentified_text=text,
                phi_entities=[],
                phi_mappings=[],
                phi_detected=False,
            )

        # Sort entities by offset in reverse order (to preserve offsets during replacement)
        sorted_entities = sorted(phi_entities, key=lambda e: e.begin_offset, reverse=True)

        # Track entity type counts for unique token generation
        type_counts: Dict[str, int] = {}
        phi_mappings: List[PHIMapping] = []
        deidentified_text = text

        # Replace each entity with a token
        for entity in sorted_entities:
            # Get count for this entity type
            entity_type = entity.type
            if entity_type not in type_counts:
                type_counts[entity_type] = 0
            type_counts[entity_type] += 1

            # Create token
            token = f"[{entity_type}_{type_counts[entity_type]}]"

            # Replace in text
            start = entity.begin_offset
            end = entity.end_offset
            deidentified_text = (
                deidentified_text[:start] + token + deidentified_text[end:]
            )

            # Create mapping
            mapping = PHIMapping(
                original=entity.text,
                token=token,
                entity_type=entity_type,
                index=type_counts[entity_type],
            )
            phi_mappings.append(mapping)

        # Reverse mappings to match original order
        phi_mappings.reverse()

        logger.info(
            "PHI de-identification completed",
            phi_count=len(phi_entities),
            unique_types=len(type_counts),
        )

        return DeidentificationResult(
            original_text=text,
            deidentified_text=deidentified_text,
            phi_entities=phi_entities,
            phi_mappings=phi_mappings,
            phi_detected=True,
        )

    def reidentify(self, deidentified_text: str, phi_mappings: List[PHIMapping]) -> str:
        """
        Restore original PHI in de-identified text

        Args:
            deidentified_text: Text with PHI tokens
            phi_mappings: List of PHI mappings

        Returns:
            Text with original PHI restored
        """
        logger.info("Re-identifying PHI", mapping_count=len(phi_mappings))

        reidentified_text = deidentified_text

        # Replace tokens with original values
        # Sort by token to ensure consistent replacement order
        sorted_mappings = sorted(phi_mappings, key=lambda m: m.token, reverse=True)

        for mapping in sorted_mappings:
            reidentified_text = reidentified_text.replace(mapping.token, mapping.original)

        logger.info("PHI re-identification completed")
        return reidentified_text

    async def store_phi_mapping(
        self, encounter_id: str, result: DeidentificationResult
    ) -> None:
        """
        Store PHI mapping in database with encryption

        Args:
            encounter_id: Encounter ID
            result: De-identification result with mappings

        Stores:
        - Encrypted PHI mapping (token → original)
        - De-identified text
        - PHI detection metadata
        """
        logger.info(
            "Storing PHI mapping",
            encounter_id=encounter_id,
            phi_count=len(result.phi_entities),
        )

        # Create mapping dictionary for encryption
        mapping_dict = {
            "mappings": [m.to_dict() for m in result.phi_mappings],
            "entities": [e.to_dict() for e in result.phi_entities],
            "created_at": datetime.utcnow().isoformat(),
        }

        # Encrypt the mapping
        encrypted_mapping = self.encryption.encrypt_json(mapping_dict)

        # Store in database
        await prisma.phimapping.create(
            data={
                "encounterId": encounter_id,
                "encryptedMapping": encrypted_mapping,
                "phiDetected": result.phi_detected,
                "phiEntityCount": len(result.phi_entities),
                "deidentifiedText": result.deidentified_text,
            }
        )

        logger.info("PHI mapping stored successfully", encounter_id=encounter_id)

    async def retrieve_phi_mapping(self, encounter_id: str) -> Optional[DeidentificationResult]:
        """
        Retrieve and decrypt PHI mapping from database

        Args:
            encounter_id: Encounter ID

        Returns:
            DeidentificationResult with mappings, or None if not found
        """
        logger.info("Retrieving PHI mapping", encounter_id=encounter_id)

        # Fetch from database
        phi_mapping_record = await prisma.phimapping.find_unique(
            where={"encounterId": encounter_id}
        )

        if not phi_mapping_record:
            logger.warning("PHI mapping not found", encounter_id=encounter_id)
            return None

        # Decrypt the mapping
        try:
            mapping_dict = self.encryption.decrypt_json(
                phi_mapping_record.encryptedMapping
            )

            # Reconstruct PHI entities
            phi_entities = [
                PHIEntity(
                    text=e["text"],
                    category=e["category"],
                    type=e["type"],
                    score=e["score"],
                    begin_offset=e["begin_offset"],
                    end_offset=e["end_offset"],
                    traits=e.get("traits", []),
                )
                for e in mapping_dict["entities"]
            ]

            # Reconstruct PHI mappings
            phi_mappings = [
                PHIMapping.from_dict(m) for m in mapping_dict["mappings"]
            ]

            # Create result
            result = DeidentificationResult(
                original_text="",  # Original text not stored
                deidentified_text=phi_mapping_record.deidentifiedText,
                phi_entities=phi_entities,
                phi_mappings=phi_mappings,
                phi_detected=phi_mapping_record.phiDetected,
            )

            logger.info("PHI mapping retrieved successfully", encounter_id=encounter_id)
            return result

        except Exception as e:
            logger.error(
                "Failed to decrypt PHI mapping",
                encounter_id=encounter_id,
                error=str(e),
            )
            raise

    async def get_deidentified_text(self, encounter_id: str) -> Optional[str]:
        """
        Get de-identified text for an encounter

        Args:
            encounter_id: Encounter ID

        Returns:
            De-identified text, or None if not found
        """
        phi_mapping_record = await prisma.phimapping.find_unique(
            where={"encounterId": encounter_id}
        )

        if not phi_mapping_record:
            return None

        return phi_mapping_record.deidentifiedText

    async def process_clinical_note(
        self, encounter_id: str, clinical_text: str, user_id: str
    ) -> DeidentificationResult:
        """
        Complete PHI processing workflow for a clinical note

        Args:
            encounter_id: Encounter ID
            clinical_text: Raw clinical note text
            user_id: User ID for audit logging

        Returns:
            DeidentificationResult

        Process:
        1. Detect and de-identify PHI
        2. Store encrypted mapping in database
        3. Log PHI access in audit log
        """
        logger.info(
            "Processing clinical note for PHI",
            encounter_id=encounter_id,
            text_length=len(clinical_text),
        )

        # Detect and de-identify
        result = self.detect_and_deidentify(clinical_text)

        # Store mapping
        await self.store_phi_mapping(encounter_id, result)

        # Audit log PHI access (skip for now due to field compatibility issue)
        # TODO: Fix audit log creation
        logger.info(
            "PHI detected",
            encounter_id=encounter_id,
            phi_count=len(result.phi_entities),
            phi_types=list(set(e.type for e in result.phi_entities))
        )

        logger.info(
            "Clinical note PHI processing completed",
            encounter_id=encounter_id,
            phi_detected=result.phi_detected,
        )

        return result

    def get_phi_statistics(self, result: DeidentificationResult) -> Dict[str, Any]:
        """
        Get statistics about PHI detected

        Args:
            result: De-identification result

        Returns:
            Dictionary with PHI statistics
        """
        phi_by_type = {}
        for entity in result.phi_entities:
            entity_type = entity.type
            if entity_type not in phi_by_type:
                phi_by_type[entity_type] = {
                    "count": 0,
                    "examples": [],
                    "avg_confidence": 0.0,
                }

            phi_by_type[entity_type]["count"] += 1
            phi_by_type[entity_type]["examples"].append(entity.text)

        # Calculate average confidence per type
        for entity_type in phi_by_type:
            entities_of_type = [e for e in result.phi_entities if e.type == entity_type]
            avg_conf = sum(e.score for e in entities_of_type) / len(entities_of_type)
            phi_by_type[entity_type]["avg_confidence"] = round(avg_conf, 3)

        return {
            "phi_detected": result.phi_detected,
            "total_phi_count": len(result.phi_entities),
            "unique_phi_types": len(phi_by_type),
            "phi_by_type": phi_by_type,
        }


# Export singleton instance
phi_handler = PHIHandler()
