"""
File Hash Utility
Compute SHA-256 hash of file contents for duplicate detection
"""

import hashlib
from typing import BinaryIO
import structlog

logger = structlog.get_logger(__name__)


def compute_file_hash(file_bytes: bytes) -> str:
    """
    Compute SHA-256 hash of file contents

    Args:
        file_bytes: File content as bytes

    Returns:
        SHA-256 hash as hexadecimal string
    """
    sha256_hash = hashlib.sha256()
    sha256_hash.update(file_bytes)
    hash_hex = sha256_hash.hexdigest()

    logger.debug(
        "File hash computed",
        file_size=len(file_bytes),
        hash_preview=hash_hex[:16]
    )

    return hash_hex


def compute_file_hash_streaming(file: BinaryIO, chunk_size: int = 8192) -> str:
    """
    Compute SHA-256 hash of file contents using streaming (memory efficient)

    Args:
        file: File-like object (must be opened in binary mode)
        chunk_size: Size of chunks to read (default 8192 bytes)

    Returns:
        SHA-256 hash as hexadecimal string
    """
    sha256_hash = hashlib.sha256()

    # Reset file pointer to beginning
    file.seek(0)

    # Read file in chunks
    while True:
        chunk = file.read(chunk_size)
        if not chunk:
            break
        sha256_hash.update(chunk)

    # Reset file pointer back to beginning for subsequent reads
    file.seek(0)

    hash_hex = sha256_hash.hexdigest()

    logger.debug(
        "File hash computed (streaming)",
        hash_preview=hash_hex[:16]
    )

    return hash_hex


def verify_file_hash(file_bytes: bytes, expected_hash: str) -> bool:
    """
    Verify if file content matches expected hash

    Args:
        file_bytes: File content as bytes
        expected_hash: Expected SHA-256 hash (hexadecimal string)

    Returns:
        True if hash matches, False otherwise
    """
    actual_hash = compute_file_hash(file_bytes)
    matches = actual_hash == expected_hash.lower()

    logger.debug(
        "File hash verification",
        matches=matches,
        expected_hash=expected_hash[:16],
        actual_hash=actual_hash[:16]
    )

    return matches
