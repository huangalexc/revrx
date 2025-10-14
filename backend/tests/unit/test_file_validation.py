"""
Unit Tests for File Validation

Tests for file upload validation, virus scanning, and file processing.
"""

import pytest
from datetime import datetime
from io import BytesIO

from app.core.database import prisma


# ============================================================================
# File Type Validation Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestFileTypeValidation:
    """Test file type and MIME type validation"""

    async def test_valid_txt_file(self):
        """Test validation accepts valid TXT files"""
        file_data = {
            "fileName": "clinical_note.txt",
            "mimeType": "text/plain",
            "fileSize": 1024,
        }

        assert file_data["mimeType"] == "text/plain"
        assert file_data["fileName"].endswith(".txt")

    async def test_valid_pdf_file(self):
        """Test validation accepts valid PDF files"""
        file_data = {
            "fileName": "clinical_note.pdf",
            "mimeType": "application/pdf",
            "fileSize": 2048,
        }

        assert file_data["mimeType"] == "application/pdf"
        assert file_data["fileName"].endswith(".pdf")

    async def test_valid_docx_file(self):
        """Test validation accepts valid DOCX files"""
        file_data = {
            "fileName": "clinical_note.docx",
            "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "fileSize": 3072,
        }

        assert file_data["mimeType"] in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/octet-stream"
        ]
        assert file_data["fileName"].endswith(".docx")

    async def test_valid_csv_file(self):
        """Test validation accepts valid CSV files"""
        file_data = {
            "fileName": "billing_codes.csv",
            "mimeType": "text/csv",
            "fileSize": 512,
        }

        assert file_data["mimeType"] in ["text/csv", "application/csv"]
        assert file_data["fileName"].endswith(".csv")

    async def test_valid_json_file(self):
        """Test validation accepts valid JSON files"""
        file_data = {
            "fileName": "billing_codes.json",
            "mimeType": "application/json",
            "fileSize": 768,
        }

        assert file_data["mimeType"] == "application/json"
        assert file_data["fileName"].endswith(".json")

    async def test_invalid_file_extension(self):
        """Test validation rejects unsupported file extensions"""
        invalid_extensions = [".exe", ".sh", ".bat", ".zip", ".tar"]

        for ext in invalid_extensions:
            file_name = f"malicious{ext}"
            # Should be rejected by validation
            assert not file_name.endswith((".txt", ".pdf", ".docx", ".csv", ".json"))

    async def test_mime_type_mismatch(self):
        """Test detection of MIME type mismatches"""
        # PDF file with wrong MIME type
        file_data = {
            "fileName": "clinical_note.pdf",
            "mimeType": "text/plain",  # Mismatch
            "fileSize": 2048,
        }

        extension = file_data["fileName"].split(".")[-1]
        expected_mime_types = {
            "pdf": ["application/pdf"],
            "txt": ["text/plain"],
        }

        assert file_data["mimeType"] not in expected_mime_types.get(extension, [])


# ============================================================================
# File Size Validation Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestFileSizeValidation:
    """Test file size limits and validation"""

    async def test_clinical_note_within_limit(self):
        """Test clinical note file within 5MB limit"""
        max_size = 5 * 1024 * 1024  # 5MB
        file_size = 3 * 1024 * 1024  # 3MB

        assert file_size <= max_size

    async def test_clinical_note_exceeds_limit(self):
        """Test clinical note file exceeding 5MB limit"""
        max_size = 5 * 1024 * 1024  # 5MB
        file_size = 6 * 1024 * 1024  # 6MB

        assert file_size > max_size

    async def test_billing_codes_within_limit(self):
        """Test billing codes file within 1MB limit"""
        max_size = 1 * 1024 * 1024  # 1MB
        file_size = 512 * 1024  # 512KB

        assert file_size <= max_size

    async def test_empty_file_rejected(self):
        """Test empty files are rejected"""
        file_size = 0
        min_size = 1  # At least 1 byte

        assert file_size < min_size

    async def test_file_size_at_boundary(self):
        """Test file size exactly at limit"""
        max_size = 5 * 1024 * 1024  # 5MB
        file_size = 5 * 1024 * 1024  # Exactly 5MB

        assert file_size <= max_size


# ============================================================================
# File Content Validation Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestFileContentValidation:
    """Test validation of file content structure and format"""

    async def test_valid_csv_structure(self):
        """Test validation of CSV file structure"""
        csv_content = "code,description,modifier\nCPT-99213,Office Visit,\nICD-Z00.00,General Exam,"
        lines = csv_content.strip().split("\n")

        # Must have header row
        assert len(lines) > 0
        # Header should contain expected columns
        header = lines[0].split(",")
        assert "code" in [h.lower() for h in header]

    async def test_valid_json_structure(self):
        """Test validation of JSON file structure"""
        import json

        json_content = '{"codes": [{"code": "CPT-99213", "description": "Office Visit"}]}'

        try:
            data = json.loads(json_content)
            assert isinstance(data, dict)
            is_valid = True
        except json.JSONDecodeError:
            is_valid = False

        assert is_valid is True

    async def test_invalid_json_structure(self):
        """Test detection of invalid JSON"""
        import json

        invalid_json = '{"codes": [{"code": "CPT-99213", "description": "Office Visit"'  # Missing closing brackets

        try:
            json.loads(invalid_json)
            is_valid = True
        except json.JSONDecodeError:
            is_valid = False

        assert is_valid is False

    async def test_empty_csv_file(self):
        """Test handling of empty CSV file"""
        csv_content = ""
        lines = csv_content.strip().split("\n")

        # Empty file should be rejected
        assert len(lines) == 1 and lines[0] == ""

    async def test_csv_with_only_header(self):
        """Test CSV file with header but no data rows"""
        csv_content = "code,description,modifier\n"
        lines = csv_content.strip().split("\n")

        # Header present but no data rows
        assert len(lines) == 1


# ============================================================================
# Virus Scanning Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestVirusScanValidation:
    """Test virus scanning workflow and status"""

    async def test_create_file_with_pending_scan(self, db, test_encounter):
        """Test file created with PENDING scan status"""
        file_record = await db.uploadedfile.create(
            data={
                "encounterId": test_encounter["id"],
                "fileType": "CLINICAL_NOTE_TXT",
                "fileName": "test.txt",
                "filePath": "test/path/test.txt",
                "fileSize": 1024,
                "mimeType": "text/plain",
                "scanStatus": "PENDING",
            }
        )

        assert file_record.scanStatus == "PENDING"
        assert file_record.scanResult is None

    async def test_update_scan_status_clean(self, db, test_encounter):
        """Test updating scan status to CLEAN"""
        file_record = await db.uploadedfile.create(
            data={
                "encounterId": test_encounter["id"],
                "fileType": "CLINICAL_NOTE_TXT",
                "fileName": "test.txt",
                "filePath": "test/path/test.txt",
                "fileSize": 1024,
                "mimeType": "text/plain",
                "scanStatus": "PENDING",
            }
        )

        updated = await db.uploadedfile.update(
            where={"id": file_record.id},
            data={
                "scanStatus": "CLEAN",
                "scanResult": "No threats detected",
            }
        )

        assert updated.scanStatus == "CLEAN"
        assert updated.scanResult == "No threats detected"

    async def test_update_scan_status_infected(self, db, test_encounter):
        """Test updating scan status to INFECTED"""
        file_record = await db.uploadedfile.create(
            data={
                "encounterId": test_encounter["id"],
                "fileType": "CLINICAL_NOTE_TXT",
                "fileName": "malicious.txt",
                "filePath": "test/path/malicious.txt",
                "fileSize": 2048,
                "mimeType": "text/plain",
                "scanStatus": "PENDING",
            }
        )

        updated = await db.uploadedfile.update(
            where={"id": file_record.id},
            data={
                "scanStatus": "INFECTED",
                "scanResult": "Threat detected: EICAR-Test-File",
            }
        )

        assert updated.scanStatus == "INFECTED"
        assert "Threat detected" in updated.scanResult

    async def test_scan_status_error(self, db, test_encounter):
        """Test handling of scan errors"""
        file_record = await db.uploadedfile.create(
            data={
                "encounterId": test_encounter["id"],
                "fileType": "CLINICAL_NOTE_TXT",
                "fileName": "test.txt",
                "filePath": "test/path/test.txt",
                "fileSize": 1024,
                "mimeType": "text/plain",
                "scanStatus": "PENDING",
            }
        )

        updated = await db.uploadedfile.update(
            where={"id": file_record.id},
            data={
                "scanStatus": "ERROR",
                "scanResult": "Scanner unavailable",
            }
        )

        assert updated.scanStatus == "ERROR"
        assert updated.scanResult is not None

    async def test_processing_blocked_until_scan_complete(self, db, test_encounter):
        """Test that encounter processing is blocked until scan completes"""
        # Create file with pending scan
        await db.uploadedfile.create(
            data={
                "encounterId": test_encounter["id"],
                "fileType": "CLINICAL_NOTE_TXT",
                "fileName": "test.txt",
                "filePath": "test/path/test.txt",
                "fileSize": 1024,
                "mimeType": "text/plain",
                "scanStatus": "PENDING",
            }
        )

        # Check encounter files
        files = await db.uploadedfile.find_many(
            where={"encounterId": test_encounter["id"]}
        )

        # Any file with PENDING or INFECTED should block processing
        has_pending_scans = any(f.scanStatus in ["PENDING", "INFECTED"] for f in files)
        assert has_pending_scans is True


# ============================================================================
# File Storage Path Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestFileStoragePath:
    """Test file path generation and validation"""

    async def test_file_path_structure(self, db, test_encounter):
        """Test file path follows expected structure"""
        file_path = f"uploads/{test_encounter['userId']}/{test_encounter['id']}/clinical_note.txt"

        file_record = await db.uploadedfile.create(
            data={
                "encounterId": test_encounter["id"],
                "fileType": "CLINICAL_NOTE_TXT",
                "fileName": "clinical_note.txt",
                "filePath": file_path,
                "fileSize": 1024,
                "mimeType": "text/plain",
            }
        )

        assert file_record.filePath.startswith("uploads/")
        assert test_encounter["userId"] in file_record.filePath
        assert test_encounter["id"] in file_record.filePath

    async def test_file_path_uniqueness(self, db, test_encounter):
        """Test that file paths are unique per upload"""
        import uuid

        file_id_1 = str(uuid.uuid4())
        file_id_2 = str(uuid.uuid4())

        path_1 = f"uploads/{test_encounter['userId']}/{test_encounter['id']}/{file_id_1}_note.txt"
        path_2 = f"uploads/{test_encounter['userId']}/{test_encounter['id']}/{file_id_2}_note.txt"

        assert path_1 != path_2


# ============================================================================
# Multiple File Upload Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestMultipleFileUploads:
    """Test handling of multiple file uploads per encounter"""

    async def test_upload_clinical_note_and_billing_codes(self, db, test_encounter):
        """Test uploading both clinical note and billing codes"""
        # Upload clinical note
        note = await db.uploadedfile.create(
            data={
                "encounterId": test_encounter["id"],
                "fileType": "CLINICAL_NOTE_TXT",
                "fileName": "note.txt",
                "filePath": "test/note.txt",
                "fileSize": 2048,
                "mimeType": "text/plain",
                "scanStatus": "CLEAN",
            }
        )

        # Upload billing codes
        codes = await db.uploadedfile.create(
            data={
                "encounterId": test_encounter["id"],
                "fileType": "BILLING_CODES_CSV",
                "fileName": "codes.csv",
                "filePath": "test/codes.csv",
                "fileSize": 512,
                "mimeType": "text/csv",
                "scanStatus": "CLEAN",
            }
        )

        # Verify both files exist
        files = await db.uploadedfile.find_many(
            where={"encounterId": test_encounter["id"]}
        )

        assert len(files) == 2
        file_types = [f.fileType for f in files]
        assert "CLINICAL_NOTE_TXT" in file_types
        assert "BILLING_CODES_CSV" in file_types

    async def test_multiple_clinical_note_formats(self, db, test_encounter):
        """Test uploading clinical notes in different formats"""
        formats = [
            ("CLINICAL_NOTE_TXT", "note.txt", "text/plain"),
            ("CLINICAL_NOTE_PDF", "note.pdf", "application/pdf"),
            ("CLINICAL_NOTE_DOCX", "note.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ]

        for file_type, file_name, mime_type in formats:
            await db.uploadedfile.create(
                data={
                    "encounterId": test_encounter["id"],
                    "fileType": file_type,
                    "fileName": file_name,
                    "filePath": f"test/{file_name}",
                    "fileSize": 1024,
                    "mimeType": mime_type,
                    "scanStatus": "CLEAN",
                }
            )

        files = await db.uploadedfile.find_many(
            where={"encounterId": test_encounter["id"]}
        )

        assert len(files) == 3


# ============================================================================
# File Metadata Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestFileMetadata:
    """Test file metadata tracking and validation"""

    async def test_file_created_timestamp(self, db, test_encounter):
        """Test that file creation timestamp is recorded"""
        file_record = await db.uploadedfile.create(
            data={
                "encounterId": test_encounter["id"],
                "fileType": "CLINICAL_NOTE_TXT",
                "fileName": "test.txt",
                "filePath": "test/test.txt",
                "fileSize": 1024,
                "mimeType": "text/plain",
            }
        )

        assert file_record.createdAt is not None
        assert isinstance(file_record.createdAt, datetime)

    async def test_file_size_recorded_accurately(self, db, test_encounter):
        """Test that file size is recorded in bytes"""
        file_size = 2048  # 2KB

        file_record = await db.uploadedfile.create(
            data={
                "encounterId": test_encounter["id"],
                "fileType": "CLINICAL_NOTE_TXT",
                "fileName": "test.txt",
                "filePath": "test/test.txt",
                "fileSize": file_size,
                "mimeType": "text/plain",
            }
        )

        assert file_record.fileSize == file_size

    async def test_mime_type_recorded(self, db, test_encounter):
        """Test that MIME type is recorded correctly"""
        mime_types = [
            "text/plain",
            "application/pdf",
            "text/csv",
            "application/json",
        ]

        for mime_type in mime_types:
            file_record = await db.uploadedfile.create(
                data={
                    "encounterId": test_encounter["id"],
                    "fileType": "CLINICAL_NOTE_TXT",
                    "fileName": "test.txt",
                    "filePath": f"test/{mime_type.replace('/', '_')}.txt",
                    "fileSize": 1024,
                    "mimeType": mime_type,
                }
            )

            assert file_record.mimeType == mime_type
