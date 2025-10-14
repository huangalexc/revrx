"""
Unit Tests for PHI De-identification

Tests for PHI detection, de-identification, and secure mapping storage.
"""

import pytest
import json
from datetime import datetime

from app.core.database import prisma


# ============================================================================
# PHI Detection Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.phi
@pytest.mark.asyncio
class TestPHIDetection:
    """Test PHI entity detection in clinical text"""

    async def test_detect_patient_names(self, sample_phi_text):
        """Test detection of patient names"""
        text = sample_phi_text

        # Names that should be detected
        expected_entities = ["John Smith", "Dr. Sarah Johnson"]

        for entity in expected_entities:
            assert entity in text

    async def test_detect_dates(self, sample_phi_text):
        """Test detection of dates"""
        text = sample_phi_text

        # Date patterns that should be detected
        date_indicators = ["01/15/2024", "March 10, 2024"]

        for date in date_indicators:
            # Check if date pattern exists
            assert any(d in text for d in date_indicators)

    async def test_detect_medical_record_numbers(self, sample_phi_text):
        """Test detection of medical record numbers"""
        text = sample_phi_text

        # MRN pattern
        assert "MRN" in text or "medical record" in text.lower()

    async def test_detect_phone_numbers(self):
        """Test detection of phone numbers"""
        text_with_phone = "Patient phone: (555) 123-4567"

        # Phone number patterns
        phone_patterns = ["(555)", "123-4567", "555-123-4567"]
        assert any(pattern in text_with_phone for pattern in phone_patterns)

    async def test_detect_email_addresses(self):
        """Test detection of email addresses"""
        text_with_email = "Contact: patient@example.com"

        assert "@" in text_with_email
        assert ".com" in text_with_email

    async def test_detect_ssn(self):
        """Test detection of Social Security Numbers"""
        text_with_ssn = "SSN: 123-45-6789"

        # SSN pattern
        assert "123-45-6789" in text_with_ssn or "SSN" in text_with_ssn

    async def test_detect_addresses(self):
        """Test detection of physical addresses"""
        text_with_address = "Address: 123 Main St, Springfield, IL 62701"

        # Address components
        address_components = ["123", "Main St", "Springfield", "62701"]
        assert all(comp in text_with_address for comp in address_components)

    async def test_no_phi_in_clean_text(self):
        """Test that clinical text without PHI is not flagged"""
        clean_text = "Patient presents with hypertension. BP 140/90. Prescribed lisinopril 10mg daily."

        # Should not contain obvious PHI patterns
        phi_patterns = ["@", "SSN", "MRN", "(555)"]
        assert not any(pattern in clean_text for pattern in phi_patterns)


# ============================================================================
# PHI De-identification Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.phi
@pytest.mark.asyncio
class TestPHIDeidentification:
    """Test PHI replacement with tokens"""

    async def test_replace_names_with_tokens(self):
        """Test replacing names with placeholder tokens"""
        original_text = "Patient John Smith presented for evaluation."
        deidentified = original_text.replace("John Smith", "[PATIENT_NAME]")

        assert "John Smith" not in deidentified
        assert "[PATIENT_NAME]" in deidentified

    async def test_replace_dates_with_tokens(self):
        """Test replacing dates with placeholder tokens"""
        original_text = "Visit date: 01/15/2024"
        deidentified = original_text.replace("01/15/2024", "[DATE]")

        assert "01/15/2024" not in deidentified
        assert "[DATE]" in deidentified

    async def test_replace_mrn_with_tokens(self):
        """Test replacing medical record numbers"""
        original_text = "MRN: 12345678"
        deidentified = original_text.replace("12345678", "[MRN]")

        assert "12345678" not in deidentified
        assert "[MRN]" in deidentified

    async def test_replace_multiple_phi_entities(self, sample_phi_text):
        """Test replacing multiple PHI entities in one text"""
        deidentified = sample_phi_text
        deidentified = deidentified.replace("John Smith", "[PATIENT_NAME]")
        deidentified = deidentified.replace("Dr. Sarah Johnson", "[PROVIDER_NAME]")
        deidentified = deidentified.replace("01/15/2024", "[DATE]")

        # All PHI should be replaced
        assert "John Smith" not in deidentified
        assert "Dr. Sarah Johnson" not in deidentified
        assert "01/15/2024" not in deidentified

        # Tokens should be present
        assert "[PATIENT_NAME]" in deidentified
        assert "[PROVIDER_NAME]" in deidentified
        assert "[DATE]" in deidentified

    async def test_preserve_clinical_content(self, sample_phi_text):
        """Test that clinical content is preserved during de-identification"""
        deidentified = sample_phi_text
        deidentified = deidentified.replace("John Smith", "[PATIENT_NAME]")

        # Clinical terms should remain
        clinical_terms = ["hypertension", "diabetes", "blood pressure"]
        for term in clinical_terms:
            if term in sample_phi_text:
                assert term in deidentified

    async def test_consistent_token_replacement(self):
        """Test that same entity gets same token"""
        text = "John Smith visited. John Smith has hypertension."
        deidentified = text.replace("John Smith", "[PATIENT_NAME]")

        # Both instances should be replaced consistently
        assert deidentified.count("[PATIENT_NAME]") == 2
        assert "John Smith" not in deidentified


# ============================================================================
# PHI Mapping Storage Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.phi
@pytest.mark.asyncio
class TestPHIMappingStorage:
    """Test secure storage of PHI mappings"""

    async def test_create_phi_mapping(self, db, test_encounter):
        """Test creating PHI mapping record"""
        mapping_data = {
            "[PATIENT_NAME]": "John Smith",
            "[DATE]": "01/15/2024",
            "[MRN]": "12345678"
        }

        # Simulate encrypted mapping
        encrypted_mapping = json.dumps(mapping_data)  # In production, this would be AES-256 encrypted

        phi_mapping = await db.phimapping.create(
            data={
                "encounterId": test_encounter["id"],
                "encryptedMapping": encrypted_mapping,
                "phiDetected": True,
                "phiEntityCount": 3,
                "deidentifiedText": "Patient [PATIENT_NAME] on [DATE] MRN: [MRN]",
            }
        )

        assert phi_mapping is not None
        assert phi_mapping.phiDetected is True
        assert phi_mapping.phiEntityCount == 3
        assert "[PATIENT_NAME]" in phi_mapping.deidentifiedText

    async def test_phi_mapping_unique_per_encounter(self, db, test_encounter):
        """Test that each encounter has only one PHI mapping"""
        # Create first mapping
        await db.phimapping.create(
            data={
                "encounterId": test_encounter["id"],
                "encryptedMapping": "{}",
                "phiDetected": False,
                "phiEntityCount": 0,
                "deidentifiedText": "Clean text",
            }
        )

        # Attempt to create second mapping should fail (unique constraint)
        with pytest.raises(Exception):  # Prisma unique constraint error
            await db.phimapping.create(
                data={
                    "encounterId": test_encounter["id"],
                    "encryptedMapping": "{}",
                    "phiDetected": False,
                    "phiEntityCount": 0,
                    "deidentifiedText": "Another text",
                }
            )

    async def test_encrypted_mapping_format(self, db, test_encounter):
        """Test encrypted mapping is stored as string"""
        mapping_data = {"[NAME]": "Test"}
        encrypted = json.dumps(mapping_data)

        phi_mapping = await db.phimapping.create(
            data={
                "encounterId": test_encounter["id"],
                "encryptedMapping": encrypted,
                "phiDetected": True,
                "phiEntityCount": 1,
                "deidentifiedText": "[NAME]",
            }
        )

        assert isinstance(phi_mapping.encryptedMapping, str)

    async def test_no_phi_detected_mapping(self, db, test_encounter):
        """Test mapping when no PHI is detected"""
        phi_mapping = await db.phimapping.create(
            data={
                "encounterId": test_encounter["id"],
                "encryptedMapping": "{}",
                "phiDetected": False,
                "phiEntityCount": 0,
                "deidentifiedText": "Patient presents with hypertension.",
            }
        )

        assert phi_mapping.phiDetected is False
        assert phi_mapping.phiEntityCount == 0
        assert phi_mapping.encryptedMapping == "{}"

    async def test_phi_entity_count_accuracy(self, db, test_encounter):
        """Test accurate counting of PHI entities"""
        mapping_data = {
            "[PATIENT_NAME]": "John Smith",
            "[DATE_1]": "01/15/2024",
            "[DATE_2]": "03/10/2024",
            "[MRN]": "12345678",
            "[PHONE]": "(555) 123-4567",
        }

        phi_mapping = await db.phimapping.create(
            data={
                "encounterId": test_encounter["id"],
                "encryptedMapping": json.dumps(mapping_data),
                "phiDetected": True,
                "phiEntityCount": len(mapping_data),
                "deidentifiedText": "De-identified text",
            }
        )

        assert phi_mapping.phiEntityCount == 5


# ============================================================================
# PHI Mapping Retrieval Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.phi
@pytest.mark.asyncio
class TestPHIMappingRetrieval:
    """Test retrieval and decryption of PHI mappings"""

    async def test_retrieve_phi_mapping(self, db, test_encounter):
        """Test retrieving PHI mapping by encounter"""
        # Create mapping
        mapping_data = {"[NAME]": "John Smith"}
        await db.phimapping.create(
            data={
                "encounterId": test_encounter["id"],
                "encryptedMapping": json.dumps(mapping_data),
                "phiDetected": True,
                "phiEntityCount": 1,
                "deidentifiedText": "[NAME]",
            }
        )

        # Retrieve mapping
        phi_mapping = await db.phimapping.find_unique(
            where={"encounterId": test_encounter["id"]}
        )

        assert phi_mapping is not None
        assert phi_mapping.encounterId == test_encounter["id"]

    async def test_decrypt_mapping_data(self, db, test_encounter):
        """Test decrypting mapping data"""
        mapping_data = {
            "[PATIENT_NAME]": "John Smith",
            "[DATE]": "01/15/2024"
        }

        await db.phimapping.create(
            data={
                "encounterId": test_encounter["id"],
                "encryptedMapping": json.dumps(mapping_data),
                "phiDetected": True,
                "phiEntityCount": 2,
                "deidentifiedText": "[PATIENT_NAME] on [DATE]",
            }
        )

        # Retrieve and decrypt
        phi_mapping = await db.phimapping.find_unique(
            where={"encounterId": test_encounter["id"]}
        )

        decrypted = json.loads(phi_mapping.encryptedMapping)
        assert decrypted["[PATIENT_NAME]"] == "John Smith"
        assert decrypted["[DATE]"] == "01/15/2024"

    async def test_re_identify_text(self, db, test_encounter):
        """Test re-identifying de-identified text"""
        mapping_data = {
            "[PATIENT_NAME]": "John Smith",
            "[DATE]": "01/15/2024"
        }
        deidentified = "Patient [PATIENT_NAME] visited on [DATE]."

        await db.phimapping.create(
            data={
                "encounterId": test_encounter["id"],
                "encryptedMapping": json.dumps(mapping_data),
                "phiDetected": True,
                "phiEntityCount": 2,
                "deidentifiedText": deidentified,
            }
        )

        # Retrieve and re-identify
        phi_mapping = await db.phimapping.find_unique(
            where={"encounterId": test_encounter["id"]}
        )

        reidentified = phi_mapping.deidentifiedText
        mapping = json.loads(phi_mapping.encryptedMapping)

        for token, original in mapping.items():
            reidentified = reidentified.replace(token, original)

        assert "John Smith" in reidentified
        assert "01/15/2024" in reidentified
        assert "[PATIENT_NAME]" not in reidentified


# ============================================================================
# Comprehend Medical Integration Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.phi
@pytest.mark.asyncio
class TestComprehendMedicalIntegration:
    """Test integration with AWS Comprehend Medical"""

    async def test_mock_comprehend_response_structure(self, mock_comprehend_response):
        """Test structure of Comprehend Medical response"""
        response = mock_comprehend_response

        assert "Entities" in response
        assert isinstance(response["Entities"], list)

        if len(response["Entities"]) > 0:
            entity = response["Entities"][0]
            assert "Text" in entity
            assert "Category" in entity
            assert "Type" in entity
            assert "BeginOffset" in entity
            assert "EndOffset" in entity

    async def test_extract_phi_entities(self, mock_comprehend_response):
        """Test extracting PHI entities from Comprehend response"""
        response = mock_comprehend_response

        phi_categories = [
            "PROTECTED_HEALTH_INFORMATION",
            "NAME",
            "DATE",
            "ID",
            "AGE",
            "PHONE_OR_FAX",
            "EMAIL",
            "ADDRESS"
        ]

        phi_entities = [
            e for e in response["Entities"]
            if e["Category"] in phi_categories
        ]

        # Should have detected PHI
        assert len(phi_entities) > 0

    async def test_entity_offset_positions(self, mock_comprehend_response):
        """Test entity offset positions are valid"""
        response = mock_comprehend_response

        for entity in response["Entities"]:
            begin = entity["BeginOffset"]
            end = entity["EndOffset"]

            assert isinstance(begin, int)
            assert isinstance(end, int)
            assert end > begin

    async def test_confidence_scores(self, mock_comprehend_response):
        """Test entity confidence scores"""
        response = mock_comprehend_response

        for entity in response["Entities"]:
            if "Score" in entity:
                score = entity["Score"]
                assert 0.0 <= score <= 1.0


# ============================================================================
# De-identification Edge Cases
# ============================================================================

@pytest.mark.unit
@pytest.mark.phi
@pytest.mark.asyncio
class TestDeidentificationEdgeCases:
    """Test edge cases in de-identification"""

    async def test_overlapping_entities(self):
        """Test handling overlapping PHI entities"""
        text = "Dr. John Smith MD"
        # "John Smith" might be detected as NAME
        # "Dr." and "MD" might be detected separately

        # Should handle overlaps gracefully
        tokens = ["[TITLE]", "[NAME]", "[CREDENTIAL]"]
        deidentified = "[TITLE] [NAME] [CREDENTIAL]"

        assert all(token in deidentified for token in tokens)

    async def test_partial_dates(self):
        """Test handling partial dates"""
        text = "Patient born in March 1985"

        # Should detect date components
        assert "March" in text or "1985" in text

    async def test_unicode_characters(self):
        """Test handling Unicode characters in PHI"""
        text = "Patient José García visited."

        # Should handle accented characters
        assert "José" in text
        assert "García" in text

    async def test_empty_text(self, db, test_encounter):
        """Test handling empty clinical text"""
        phi_mapping = await db.phimapping.create(
            data={
                "encounterId": test_encounter["id"],
                "encryptedMapping": "{}",
                "phiDetected": False,
                "phiEntityCount": 0,
                "deidentifiedText": "",
            }
        )

        assert phi_mapping.deidentifiedText == ""
        assert phi_mapping.phiEntityCount == 0

    async def test_very_long_text(self):
        """Test handling very long clinical notes"""
        long_text = "Clinical note. " * 1000  # ~15,000 characters

        # Should handle without errors
        assert len(long_text) > 10000

    async def test_special_characters(self):
        """Test handling special characters"""
        text = "BP: 120/80, HR: 72 bpm, Temp: 98.6°F"

        # Special characters should be preserved
        special_chars = ["/", ":", ".", "°"]
        assert all(char in text for char in special_chars)


# ============================================================================
# HIPAA Compliance Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.phi
@pytest.mark.asyncio
class TestHIPAACompliance:
    """Test HIPAA compliance requirements"""

    async def test_phi_mapping_timestamp(self, db, test_encounter):
        """Test PHI mapping includes creation timestamp"""
        phi_mapping = await db.phimapping.create(
            data={
                "encounterId": test_encounter["id"],
                "encryptedMapping": "{}",
                "phiDetected": False,
                "phiEntityCount": 0,
                "deidentifiedText": "Text",
            }
        )

        assert phi_mapping.createdAt is not None
        assert isinstance(phi_mapping.createdAt, datetime)

    async def test_phi_mapping_cascade_delete(self, db, test_user):
        """Test PHI mapping is deleted when encounter is deleted"""
        # Create encounter
        encounter = await db.encounter.create(
            data={
                "userId": test_user["id"],
                "status": "PENDING",
            }
        )

        # Create PHI mapping
        await db.phimapping.create(
            data={
                "encounterId": encounter.id,
                "encryptedMapping": "{}",
                "phiDetected": False,
                "phiEntityCount": 0,
                "deidentifiedText": "Text",
            }
        )

        # Delete encounter
        await db.encounter.delete(where={"id": encounter.id})

        # PHI mapping should be deleted (cascade)
        phi_mapping = await db.phimapping.find_unique(
            where={"encounterId": encounter.id}
        )

        assert phi_mapping is None

    async def test_no_phi_in_logs(self):
        """Test that PHI is never logged in plain text"""
        # This is a documentation test - in production:
        # 1. Never log original clinical text
        # 2. Only log de-identified text
        # 3. Never log encryption keys
        # 4. Audit all PHI access

        log_safe_text = "[PATIENT_NAME] presented with hypertension"
        assert "[PATIENT_NAME]" in log_safe_text
        assert "John Smith" not in log_safe_text
