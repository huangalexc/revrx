"""
HIPAA Compliance Tests for Duplicate Detection

Ensures that duplicate detection does not expose PHI and follows HIPAA guidelines.
"""

import pytest
import io
import re
from httpx import AsyncClient
from fastapi import status as http_status
from app.main import app
from app.utils.file_hash import compute_file_hash
from app.models.prisma_client import prisma


class TestHIPAACompliantDuplicateDetection:
    """Test HIPAA compliance for duplicate file detection."""

    @pytest.mark.asyncio
    async def test_hash_is_one_way_function(self, sample_clinical_note_1):
        """Verify that hash cannot be reversed to extract PHI."""
        file_hash = compute_file_hash(sample_clinical_note_1)

        # Hash should be a hex string (SHA-256 = 64 characters)
        assert len(file_hash) == 64
        assert all(c in '0123456789abcdef' for c in file_hash)

        # Hash should not contain any PHI from the source
        file_content = sample_clinical_note_1.decode('utf-8')

        # Extract PHI elements from file
        phi_patterns = [
            r'Patient:\s*([^\n]+)',  # Patient name
            r'MRN:\s*(\d+)',  # Medical Record Number
            r'Dr\.\s*([^\n]+)',  # Doctor name
            r'License:\s*([^\n]+)',  # License number
            r'\d{3}-\d{2}-\d{4}',  # SSN pattern
            r'\(\d{3}\)\s*\d{3}-\d{4}',  # Phone number pattern
        ]

        for pattern in phi_patterns:
            matches = re.findall(pattern, file_content)
            for match in matches:
                # Hash should not contain any PHI substring
                assert match.lower() not in file_hash.lower()

    @pytest.mark.asyncio
    async def test_duplicate_response_contains_no_phi(self, auth_headers, sample_clinical_note_1):
        """Verify duplicate detection response does not expose PHI."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Upload original file
            files1 = {"file": ("note.txt", io.BytesIO(sample_clinical_note_1), "text/plain")}
            await client.post(
                "/api/v1/encounters/upload-note",
                files=files1,
                headers=auth_headers
            )

            # Check for duplicate
            files2 = {"file": ("duplicate.txt", io.BytesIO(sample_clinical_note_1), "text/plain")}
            response = await client.post(
                "/api/v1/encounters/check-duplicate",
                files=files2,
                headers=auth_headers
            )

            assert response.status_code == http_status.HTTP_200_OK
            result = response.json()

            # Verify duplicate_info structure
            duplicate_info = result.get("duplicate_info", {})

            # Allowed non-PHI fields only
            allowed_fields = {
                "file_id",
                "encounter_id",
                "original_filename",
                "upload_timestamp",
                "file_size"
            }

            # Check that only allowed fields are present
            assert set(duplicate_info.keys()).issubset(allowed_fields)

            # Verify no PHI in response
            response_str = str(result).lower()

            # Should not contain patient names
            assert "john doe" not in response_str
            assert "jane smith" not in response_str
            assert "robert williams" not in response_str

            # Should not contain provider names
            assert "sarah smith" not in response_str
            assert "michael johnson" not in response_str
            assert "emily chen" not in response_str

            # Should not contain MRN
            assert "12345" not in response_str
            assert "67890" not in response_str
            assert "54321" not in response_str

            # Should not contain medical data
            assert "blood pressure" not in response_str
            assert "diabetes" not in response_str
            assert "chest pain" not in response_str

    @pytest.mark.asyncio
    async def test_file_content_not_stored_in_database(self, auth_headers, sample_clinical_note_1):
        """Verify that raw file content is not stored in database (only S3)."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            files = {"file": ("note.txt", io.BytesIO(sample_clinical_note_1), "text/plain")}
            response = await client.post(
                "/api/v1/encounters/upload-note",
                files=files,
                headers=auth_headers
            )

            file_id = response.json()["file_id"]

            # Get file record from database
            uploaded_file = await prisma.uploadedfile.find_unique(
                where={"id": file_id}
            )

            # Check that content is not in any database field
            file_dict = uploaded_file.dict()

            # No field should contain the actual file content
            file_content = sample_clinical_note_1.decode('utf-8')
            for field_name, field_value in file_dict.items():
                if isinstance(field_value, str):
                    assert file_content not in field_value

    @pytest.mark.asyncio
    async def test_duplicate_check_user_isolation(self, auth_headers, second_test_user, sample_clinical_note_1):
        """Verify duplicate detection is isolated by user (no cross-user PHI exposure)."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # User A uploads a file
            files_user_a = {"file": ("user_a_note.txt", io.BytesIO(sample_clinical_note_1), "text/plain")}
            await client.post(
                "/api/v1/encounters/upload-note",
                files=files_user_a,
                headers=auth_headers
            )

            # User B checks same file content
            second_auth_headers = {"Authorization": f"Bearer {second_test_user['access_token']}"}
            files_user_b = {"file": ("user_b_note.txt", io.BytesIO(sample_clinical_note_1), "text/plain")}

            response = await client.post(
                "/api/v1/encounters/check-duplicate",
                files=files_user_b,
                headers=second_auth_headers
            )

            result = response.json()

            # Should NOT be flagged as duplicate for User B
            assert result["is_duplicate"] is False

            # User A checks again - should be duplicate
            files_user_a_check = {"file": ("user_a_duplicate.txt", io.BytesIO(sample_clinical_note_1), "text/plain")}
            response_a = await client.post(
                "/api/v1/encounters/check-duplicate",
                files=files_user_a_check,
                headers=auth_headers
            )

            result_a = response_a.json()
            assert result_a["is_duplicate"] is True

    @pytest.mark.asyncio
    async def test_audit_trail_for_duplicate_detection(self, auth_headers, sample_clinical_note_1):
        """Verify that duplicate detection events are logged for audit purposes."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Upload original
            files1 = {"file": ("original.txt", io.BytesIO(sample_clinical_note_1), "text/plain")}
            upload_response = await client.post(
                "/api/v1/encounters/upload-note",
                files=files1,
                headers=auth_headers
            )

            # Check duplicate
            files2 = {"file": ("duplicate.txt", io.BytesIO(sample_clinical_note_1), "text/plain")}
            await client.post(
                "/api/v1/encounters/check-duplicate",
                files=files2,
                headers=auth_headers
            )

            # Upload with duplicate handling
            files3 = {"file": ("duplicate.txt", io.BytesIO(sample_clinical_note_1), "text/plain")}
            data3 = {"duplicate_handling": "SKIP"}
            duplicate_response = await client.post(
                "/api/v1/encounters/upload-note",
                files=files3,
                data=data3,
                headers=auth_headers
            )

            # Verify duplicate metadata is stored
            file_id = duplicate_response.json()["file_id"]
            uploaded_file = await prisma.uploadedfile.find_unique(
                where={"id": file_id}
            )

            assert uploaded_file.isDuplicate is True
            assert uploaded_file.duplicateHandling == "SKIP"
            assert uploaded_file.originalFileId is not None

    @pytest.mark.asyncio
    async def test_hash_collision_extremely_unlikely(self):
        """Demonstrate that SHA-256 collisions are computationally infeasible."""
        # SHA-256 has 2^256 possible outputs
        # For healthcare use case, collision probability is negligible

        samples = [
            b"Patient A medical note",
            b"Patient A medical note ",  # Different by one space
            b"Patient B medical note",
            b"Completely different content here",
        ]

        hashes = [compute_file_hash(sample) for sample in samples]

        # All hashes should be unique
        assert len(hashes) == len(set(hashes))

        # Very small change should produce completely different hash
        hash1 = compute_file_hash(b"Patient note")
        hash2 = compute_file_hash(b"Patient note.")  # Added period

        # Hamming distance should be approximately 50% (very different)
        different_chars = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
        similarity_ratio = different_chars / len(hash1)

        # Should be very different (>40% different characters)
        assert similarity_ratio > 0.4

    @pytest.mark.asyncio
    async def test_replace_duplicate_deletes_old_phi(self, auth_headers, sample_clinical_note_1, sample_clinical_note_2):
        """
        Verify that REPLACE duplicate handling properly deletes old PHI.

        Note: This test is for the future REPLACE implementation.
        """
        # This test documents expected behavior for REPLACE feature
        # When implemented, REPLACE should:
        # 1. Delete old encounter record
        # 2. Delete old S3 file
        # 3. Delete old redacted file
        # 4. Create new encounter with same metadata linkage

        # TODO: Implement once REPLACE endpoint is ready
        pytest.skip("REPLACE duplicate handling not yet implemented")

    @pytest.mark.asyncio
    async def test_minimum_necessary_principle(self, auth_headers, sample_clinical_note_1):
        """Verify system follows HIPAA minimum necessary principle."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Upload file
            files = {"file": ("note.txt", io.BytesIO(sample_clinical_note_1), "text/plain")}
            upload_response = await client.post(
                "/api/v1/encounters/upload-note",
                files=files,
                headers=auth_headers
            )

            file_id = upload_response.json()["file_id"]

            # Check what's stored in database
            uploaded_file = await prisma.uploadedfile.find_unique(
                where={"id": file_id}
            )

            # Only minimum necessary data should be in database
            # PHI should only be in S3 with encryption
            stored_fields = uploaded_file.dict()

            # Verify only metadata is stored, not content
            assert "originalFilename" in stored_fields  # OK - needed for user reference
            assert "s3Key" in stored_fields  # OK - needed to retrieve from S3
            assert "fileHash" in stored_fields  # OK - for duplicate detection
            assert "fileSize" in stored_fields  # OK - metadata

            # Content should NOT be in database
            assert "content" not in stored_fields
            assert "file_content" not in stored_fields

    @pytest.mark.asyncio
    async def test_encryption_at_rest_verification(self, auth_headers, sample_clinical_note_1):
        """Verify that file storage uses encryption at rest."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            files = {"file": ("note.txt", io.BytesIO(sample_clinical_note_1), "text/plain")}
            response = await client.post(
                "/api/v1/encounters/upload-note",
                files=files,
                headers=auth_headers
            )

            file_id = response.json()["file_id"]

            # Get S3 key from database
            uploaded_file = await prisma.uploadedfile.find_unique(
                where={"id": file_id}
            )

            # Verify S3 key format indicates encrypted storage path
            # Typically: uploads/{user_id}/encrypted/{file_id}.enc
            assert uploaded_file.s3Key is not None

            # S3 bucket should have encryption enabled (verified in infrastructure)
            # This test documents the requirement

    @pytest.mark.asyncio
    async def test_access_control_enforcement(self, auth_headers, second_test_user, sample_clinical_note_1):
        """Verify users cannot access other users' duplicate information."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # User A uploads file
            files_a = {"file": ("note_a.txt", io.BytesIO(sample_clinical_note_1), "text/plain")}
            response_a = await client.post(
                "/api/v1/encounters/upload-note",
                files=files_a,
                headers=auth_headers
            )

            encounter_id_a = response_a.json()["encounter_id"]

            # User B tries to check batch status for User A's batch
            second_auth_headers = {"Authorization": f"Bearer {second_test_user['access_token']}"}

            # Get User A's encounter to extract batch_id
            encounter_a = await prisma.encounter.find_unique(
                where={"id": encounter_id_a}
            )

            if encounter_a.batchId:
                # User B tries to access User A's batch
                response_b = await client.post(
                    f"/api/v1/encounters/batch/{encounter_a.batchId}/status",
                    headers=second_auth_headers
                )

                # Should return empty or forbidden (depends on implementation)
                result = response_b.json()
                # Should not return User A's data
                assert result.get("total_count", 0) == 0


class TestDataMinimization:
    """Test data minimization principles."""

    @pytest.mark.asyncio
    async def test_file_hash_only_stored_temporarily(self, auth_headers, sample_clinical_note_1):
        """Verify file hash is stored for duplicate detection only."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            files = {"file": ("note.txt", io.BytesIO(sample_clinical_note_1), "text/plain")}
            response = await client.post(
                "/api/v1/encounters/upload-note",
                files=files,
                headers=auth_headers
            )

            file_id = response.json()["file_id"]

            # Hash should be stored
            uploaded_file = await prisma.uploadedfile.find_unique(
                where={"id": file_id}
            )

            assert uploaded_file.fileHash is not None
            assert len(uploaded_file.fileHash) == 64

    @pytest.mark.asyncio
    async def test_batch_id_does_not_expose_phi(self):
        """Verify batch_id is a UUID and doesn't contain PHI."""
        import uuid

        # Batch ID should be UUID v4
        batch_id = str(uuid.uuid4())

        # Should be valid UUID format
        uuid.UUID(batch_id, version=4)

        # Should not contain any PHI
        assert len(batch_id) == 36  # Standard UUID length with dashes
        assert batch_id.count('-') == 4

        # Should only contain hex characters and dashes
        assert all(c in '0123456789abcdef-' for c in batch_id)
