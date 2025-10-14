"""
File Validation Utilities
Validates file types, sizes, and content
"""

import magic
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException
import structlog

from app.core.config import settings
from app.schemas.encounter import FileType

logger = structlog.get_logger(__name__)

# MIME type mappings
ALLOWED_MIME_TYPES = {
    FileType.TXT: ["text/plain"],
    FileType.PDF: ["application/pdf"],
    FileType.DOCX: [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ],
    FileType.CSV: ["text/csv", "text/plain"],
    FileType.JSON: ["application/json", "text/plain"],
}

# File extensions
ALLOWED_EXTENSIONS = {
    FileType.TXT: [".txt"],
    FileType.PDF: [".pdf"],
    FileType.DOCX: [".docx"],
    FileType.CSV: [".csv"],
    FileType.JSON: [".json"],
}

MAX_FILE_SIZE_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes


def validate_file_extension(filename: str, expected_type: FileType) -> bool:
    """
    Validate file extension matches expected type

    Args:
        filename: Name of the file
        expected_type: Expected file type

    Returns:
        True if valid, False otherwise
    """
    file_ext = Path(filename).suffix.lower()
    allowed_exts = ALLOWED_EXTENSIONS.get(expected_type, [])
    return file_ext in allowed_exts


def validate_file_size(file_size: int) -> bool:
    """
    Validate file size is within limits

    Args:
        file_size: Size of file in bytes

    Returns:
        True if valid, False otherwise
    """
    return 0 < file_size <= MAX_FILE_SIZE_BYTES


def detect_mime_type(file_content: bytes) -> str:
    """
    Detect MIME type from file content using python-magic

    Args:
        file_content: File content as bytes

    Returns:
        MIME type string
    """
    try:
        mime = magic.Magic(mime=True)
        return mime.from_buffer(file_content)
    except Exception as e:
        logger.error("Failed to detect MIME type", error=str(e))
        return "application/octet-stream"


def validate_mime_type(mime_type: str, expected_type: FileType) -> bool:
    """
    Validate MIME type matches expected file type

    Args:
        mime_type: Detected MIME type
        expected_type: Expected file type

    Returns:
        True if valid, False otherwise
    """
    allowed_mimes = ALLOWED_MIME_TYPES.get(expected_type, [])

    # For TXT files, be more lenient as python-magic can misdetect text files
    if expected_type == FileType.TXT and mime_type.startswith("text/"):
        return True

    return mime_type in allowed_mimes


async def validate_upload_file(
    file: UploadFile,
    expected_type: FileType,
    max_size: Optional[int] = None
) -> Tuple[bytes, str]:
    """
    Comprehensive file validation

    Args:
        file: FastAPI UploadFile object
        expected_type: Expected file type
        max_size: Optional custom max size in bytes

    Returns:
        Tuple of (file_content, mime_type)

    Raises:
        HTTPException: If validation fails
    """
    # Validate filename
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required"
        )

    # Validate file extension
    if not validate_file_extension(file.filename, expected_type):
        allowed_exts = ", ".join(ALLOWED_EXTENSIONS.get(expected_type, []))
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Expected: {allowed_exts}"
        )

    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        logger.error("Failed to read file", error=str(e))
        raise HTTPException(
            status_code=400,
            detail="Failed to read file content"
        )

    # Validate file size
    file_size = len(file_content)
    max_allowed = max_size or MAX_FILE_SIZE_BYTES

    if not validate_file_size(file_size) or file_size > max_allowed:
        max_mb = max_allowed / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {max_mb}MB"
        )

    # Detect and validate MIME type
    mime_type = detect_mime_type(file_content)

    # For TXT files, skip MIME type validation as python-magic often misdetects plain text
    # The actual content validation happens during text extraction
    if expected_type != FileType.TXT and not validate_mime_type(mime_type, expected_type):
        allowed_types = ", ".join(ALLOWED_MIME_TYPES.get(expected_type, []))
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file content type. Expected: {allowed_types}, got: {mime_type}"
        )

    # Override MIME type for TXT files
    if expected_type == FileType.TXT:
        mime_type = "text/plain"

    logger.info(
        "File validated successfully",
        filename=file.filename,
        size=file_size,
        mime_type=mime_type
    )

    return file_content, mime_type


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and other attacks

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Get just the filename without path
    filename = Path(filename).name

    # Remove any potentially dangerous characters
    safe_chars = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    sanitized = "".join(c for c in filename if c in safe_chars)

    # Ensure filename is not empty
    if not sanitized:
        sanitized = "unnamed_file"

    return sanitized
