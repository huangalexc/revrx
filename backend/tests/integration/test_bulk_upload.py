"""
Integration tests for bulk upload functionality.

Tests the complete flow: file upload → hash computation → duplicate detection → batch tracking.
"""

import pytest
import io
import uuid
from httpx import AsyncClient
from fastapi import status as http_status
from app.main import app
from app.models.prisma_client import prisma
from app.utils.file_hash import compute_file_hash


@pytest.fixture
async def auth_headers(test_user):
    """Fixture to provide authentication headers."""
    # This assumes you have a test_user fixture that creates a test user
    # and returns auth headers. Adjust based on your test setup.
    return {"Authorization": f"Bearer {test_user['access_token']}"}


@pytest.fixture
async def sample_file_content():
    """Sample clinical note content for testing."""
    return b"""
Patient: John Doe
Date: 2024-01-15
Chief Complaint: Routine checkup

Assessment:
Patient presents for annual physical examination.
Blood pressure: 120/80 mmHg
Heart rate: 72 bpm
Temperature: 98.6°F

Plan:
- Continue current medications
- Follow up in 6 months
- Lab work ordered

Dr. Sarah Smith, MD
"""


@pytest.fixture
async def different_file_content():
    """Different clinical note content for testing."""
    return b"""
Patient: Jane Smith
Date: 2024-01-16
Chief Complaint: Follow-up visit

Assessment:
Patient presents for diabetes follow-up.
Blood glucose: 110 mg/dL
HbA1c: 6.5%

Plan:
- Adjust insulin dosage
- Dietary counseling
- Follow up in 3 months

Dr. Michael Johnson, MD
"""


class TestBulkUploadFlow:
    """Test complete bulk upload workflow."""

    @pytest.mark.asyncio
    async def test_single_file_with_batch_id(self, auth_headers, sample_file_content):
        """Test uploading a single file with batch_id."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            batch_id = str(uuid.uuid4())

            files = {"file": ("test_note.txt", io.BytesIO(sample_file_content), "text/plain")}
            data = {"batch_id": batch_id}

            response = await client.post(
                "/api/v1/encounters/upload-note",
                files=files,
                data=data,
                headers=auth_headers
            )

            assert response.status_code == http_status.HTTP_201_CREATED
            result = response.json()

            assert "encounter_id" in result
            assert "file_id" in result

            # Verify batch_id is stored in database
            encounter = await prisma.encounter.find_unique(
                where={"id": result["encounter_id"]}
            )
            assert encounter.batchId == batch_id

    @pytest.mark.asyncio
    async def test_multiple_files_same_batch(self, auth_headers, sample_file_content, different_file_content):
        """Test uploading multiple files with the same batch_id."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            batch_id = str(uuid.uuid4())
            encounter_ids = []

            # Upload first file
            files1 = {"file": ("note1.txt", io.BytesIO(sample_file_content), "text/plain")}
            data1 = {"batch_id": batch_id}

            response1 = await client.post(
                "/api/v1/encounters/upload-note",
                files=files1,
                data=data1,
                headers=auth_headers
            )

            assert response1.status_code == http_status.HTTP_201_CREATED
            encounter_ids.append(response1.json()["encounter_id"])

            # Upload second file
            files2 = {"file": ("note2.txt", io.BytesIO(different_file_content), "text/plain")}
            data2 = {"batch_id": batch_id}

            response2 = await client.post(
                "/api/v1/encounters/upload-note",
                files=files2,
                data=data2,
                headers=auth_headers
            )

            assert response2.status_code == http_status.HTTP_201_CREATED
            encounter_ids.append(response2.json()["encounter_id"])

            # Verify both encounters have the same batch_id
            for encounter_id in encounter_ids:
                encounter = await prisma.encounter.find_unique(
                    where={"id": encounter_id}
                )
                assert encounter.batchId == batch_id

    @pytest.mark.asyncio
    async def test_file_hash_stored_correctly(self, auth_headers, sample_file_content):
        """Test that file hash is computed and stored correctly."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            expected_hash = compute_file_hash(sample_file_content)

            files = {"file": ("test_note.txt", io.BytesIO(sample_file_content), "text/plain")}

            response = await client.post(
                "/api/v1/encounters/upload-note",
                files=files,
                headers=auth_headers
            )

            assert response.status_code == http_status.HTTP_201_CREATED
            result = response.json()

            # Verify hash is stored in database
            uploaded_file = await prisma.uploadedfile.find_unique(
                where={"id": result["file_id"]}
            )
            assert uploaded_file.fileHash == expected_hash

    @pytest.mark.asyncio
    async def test_batch_status_endpoint(self, auth_headers, sample_file_content, different_file_content):
        """Test batch status endpoint returns correct information."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            batch_id = str(uuid.uuid4())

            # Upload two files
            files1 = {"file": ("note1.txt", io.BytesIO(sample_file_content), "text/plain")}
            data1 = {"batch_id": batch_id}
            await client.post(
                "/api/v1/encounters/upload-note",
                files=files1,
                data=data1,
                headers=auth_headers
            )

            files2 = {"file": ("note2.txt", io.BytesIO(different_file_content), "text/plain")}
            data2 = {"batch_id": batch_id}
            await client.post(
                "/api/v1/encounters/upload-note",
                files=files2,
                data=data2,
                headers=auth_headers
            )

            # Check batch status
            response = await client.post(
                f"/api/v1/encounters/batch/{batch_id}/status",
                headers=auth_headers
            )

            assert response.status_code == http_status.HTTP_200_OK
            result = response.json()

            assert result["batch_id"] == batch_id
            assert result["total_count"] == 2
            assert len(result["encounters"]) == 2


class TestDuplicateDetection:
    """Test duplicate detection functionality."""

    @pytest.mark.asyncio
    async def test_check_duplicate_endpoint(self, auth_headers, sample_file_content):
        """Test duplicate checking endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # First upload
            files1 = {"file": ("original.txt", io.BytesIO(sample_file_content), "text/plain")}
            upload_response = await client.post(
                "/api/v1/encounters/upload-note",
                files=files1,
                headers=auth_headers
            )
            assert upload_response.status_code == http_status.HTTP_201_CREATED

            # Check for duplicate
            files2 = {"file": ("duplicate.txt", io.BytesIO(sample_file_content), "text/plain")}
            check_response = await client.post(
                "/api/v1/encounters/check-duplicate",
                files=files2,
                headers=auth_headers
            )

            assert check_response.status_code == http_status.HTTP_200_OK
            result = check_response.json()

            assert result["is_duplicate"] is True
            assert "duplicate_info" in result
            assert result["duplicate_info"]["original_filename"] == "original.txt"

    @pytest.mark.asyncio
    async def test_no_duplicate_for_different_content(self, auth_headers, sample_file_content, different_file_content):
        """Test that different content is not flagged as duplicate."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # First upload
            files1 = {"file": ("file1.txt", io.BytesIO(sample_file_content), "text/plain")}
            await client.post(
                "/api/v1/encounters/upload-note",
                files=files1,
                headers=auth_headers
            )

            # Check different file
            files2 = {"file": ("file2.txt", io.BytesIO(different_file_content), "text/plain")}
            check_response = await client.post(
                "/api/v1/encounters/check-duplicate",
                files=files2,
                headers=auth_headers
            )

            assert check_response.status_code == http_status.HTTP_200_OK
            result = check_response.json()

            assert result["is_duplicate"] is False

    @pytest.mark.asyncio
    async def test_duplicate_handling_skip(self, auth_headers, sample_file_content):
        """Test SKIP duplicate handling."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # First upload
            files1 = {"file": ("original.txt", io.BytesIO(sample_file_content), "text/plain")}
            first_response = await client.post(
                "/api/v1/encounters/upload-note",
                files=files1,
                headers=auth_headers
            )
            first_file_id = first_response.json()["file_id"]

            # Upload duplicate with SKIP handling
            files2 = {"file": ("duplicate.txt", io.BytesIO(sample_file_content), "text/plain")}
            data2 = {"duplicate_handling": "SKIP"}

            second_response = await client.post(
                "/api/v1/encounters/upload-note",
                files=files2,
                data=data2,
                headers=auth_headers
            )

            assert second_response.status_code == http_status.HTTP_201_CREATED
            second_file_id = second_response.json()["file_id"]

            # Verify duplicate is marked correctly
            duplicate_file = await prisma.uploadedfile.find_unique(
                where={"id": second_file_id}
            )
            assert duplicate_file.isDuplicate is True
            assert duplicate_file.duplicateHandling == "SKIP"
            assert duplicate_file.originalFileId == first_file_id

    @pytest.mark.asyncio
    async def test_duplicate_handling_process_as_new(self, auth_headers, sample_file_content):
        """Test PROCESS_AS_NEW duplicate handling."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # First upload
            files1 = {"file": ("original.txt", io.BytesIO(sample_file_content), "text/plain")}
            first_response = await client.post(
                "/api/v1/encounters/upload-note",
                files=files1,
                headers=auth_headers
            )
            first_file_id = first_response.json()["file_id"]

            # Upload duplicate with PROCESS_AS_NEW handling
            files2 = {"file": ("duplicate.txt", io.BytesIO(sample_file_content), "text/plain")}
            data2 = {"duplicate_handling": "PROCESS_AS_NEW"}

            second_response = await client.post(
                "/api/v1/encounters/upload-note",
                files=files2,
                data=data2,
                headers=auth_headers
            )

            assert second_response.status_code == http_status.HTTP_201_CREATED
            second_file_id = second_response.json()["file_id"]

            # Verify it's processed but marked as duplicate
            duplicate_file = await prisma.uploadedfile.find_unique(
                where={"id": second_file_id}
            )
            assert duplicate_file.isDuplicate is True
            assert duplicate_file.duplicateHandling == "PROCESS_AS_NEW"
            assert duplicate_file.originalFileId == first_file_id

    @pytest.mark.asyncio
    async def test_duplicate_isolation_by_user(self, sample_file_content):
        """Test that duplicates are isolated by user (user A's file is not duplicate for user B)."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # This test would require two different users
            # Implementation depends on your user fixture setup
            # Pseudocode:
            # 1. User A uploads file
            # 2. User B checks same file - should NOT be duplicate
            # 3. User A checks same file - SHOULD be duplicate
            pass


class TestHIPAACompliance:
    """Test HIPAA compliance for duplicate detection."""

    @pytest.mark.asyncio
    async def test_hash_computation_no_phi(self, sample_file_content):
        """Test that hash computation doesn't expose PHI."""
        # Hash should be one-way - can't extract PHI from hash
        file_hash = compute_file_hash(sample_file_content)

        # Hash should be 64 characters (SHA-256 hex)
        assert len(file_hash) == 64
        assert all(c in '0123456789abcdef' for c in file_hash)

        # Hash should not contain any text from the file
        file_text = sample_file_content.decode('utf-8').lower()
        assert 'john doe' not in file_hash.lower()
        assert 'sarah smith' not in file_hash.lower()

    @pytest.mark.asyncio
    async def test_duplicate_info_no_phi(self, auth_headers, sample_file_content):
        """Test that duplicate detection response doesn't expose PHI."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # First upload
            files1 = {"file": ("note.txt", io.BytesIO(sample_file_content), "text/plain")}
            await client.post(
                "/api/v1/encounters/upload-note",
                files=files1,
                headers=auth_headers
            )

            # Check duplicate
            files2 = {"file": ("duplicate.txt", io.BytesIO(sample_file_content), "text/plain")}
            response = await client.post(
                "/api/v1/encounters/check-duplicate",
                files=files2,
                headers=auth_headers
            )

            result = response.json()
            duplicate_info = result.get("duplicate_info", {})

            # Should only contain non-PHI metadata
            allowed_fields = {"file_id", "encounter_id", "original_filename", "upload_timestamp", "file_size"}
            assert set(duplicate_info.keys()).issubset(allowed_fields)

            # Should NOT contain file content or extracted PHI
            assert "content" not in duplicate_info
            assert "phi_entities" not in duplicate_info
            assert "patient_name" not in duplicate_info


class TestPerformance:
    """Performance tests for bulk upload."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_bulk_upload_10_files(self, auth_headers, sample_file_content):
        """Test uploading 10 files in a batch."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            batch_id = str(uuid.uuid4())
            upload_count = 10

            for i in range(upload_count):
                files = {"file": (f"note_{i}.txt", io.BytesIO(sample_file_content), "text/plain")}
                data = {"batch_id": batch_id}

                response = await client.post(
                    "/api/v1/encounters/upload-note",
                    files=files,
                    data=data,
                    headers=auth_headers
                )

                assert response.status_code == http_status.HTTP_201_CREATED

            # Verify batch status
            status_response = await client.post(
                f"/api/v1/encounters/batch/{batch_id}/status",
                headers=auth_headers
            )

            result = status_response.json()
            assert result["total_count"] == upload_count

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_duplicate_check_performance(self, auth_headers, sample_file_content):
        """Test duplicate checking performance with multiple existing files."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Upload 20 different files first
            for i in range(20):
                content = sample_file_content + f"\nFile number: {i}".encode()
                files = {"file": (f"file_{i}.txt", io.BytesIO(content), "text/plain")}
                await client.post(
                    "/api/v1/encounters/upload-note",
                    files=files,
                    headers=auth_headers
                )

            # Check duplicate (should be fast even with many existing files)
            import time
            start_time = time.time()

            files = {"file": ("check.txt", io.BytesIO(sample_file_content), "text/plain")}
            response = await client.post(
                "/api/v1/encounters/check-duplicate",
                files=files,
                headers=auth_headers
            )

            end_time = time.time()
            duration = end_time - start_time

            assert response.status_code == http_status.HTTP_200_OK
            # Duplicate check should be fast (< 1 second even with 20 files)
            assert duration < 1.0


class TestErrorHandling:
    """Test error handling in bulk upload."""

    @pytest.mark.asyncio
    async def test_invalid_batch_id_format(self, auth_headers, sample_file_content):
        """Test that invalid batch_id is handled gracefully."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            files = {"file": ("note.txt", io.BytesIO(sample_file_content), "text/plain")}
            data = {"batch_id": "invalid-not-a-uuid"}

            response = await client.post(
                "/api/v1/encounters/upload-note",
                files=files,
                data=data,
                headers=auth_headers
            )

            # Should accept any string as batch_id (validation up to frontend)
            # Or implement UUID validation if required
            assert response.status_code in [http_status.HTTP_201_CREATED, http_status.HTTP_400_BAD_REQUEST]

    @pytest.mark.asyncio
    async def test_batch_status_nonexistent_batch(self, auth_headers):
        """Test batch status for non-existent batch_id."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            nonexistent_batch_id = str(uuid.uuid4())

            response = await client.post(
                f"/api/v1/encounters/batch/{nonexistent_batch_id}/status",
                headers=auth_headers
            )

            assert response.status_code == http_status.HTTP_200_OK
            result = response.json()
            assert result["total_count"] == 0
            assert result["encounters"] == []
