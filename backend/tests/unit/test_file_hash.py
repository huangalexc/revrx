"""
Unit tests for file hash utility
"""

import pytest
import hashlib
from io import BytesIO
from app.utils.file_hash import (
    compute_file_hash,
    compute_file_hash_streaming,
    verify_file_hash
)


def test_compute_file_hash():
    """Test basic file hash computation"""
    test_content = b"This is a test file content"
    expected_hash = hashlib.sha256(test_content).hexdigest()

    result = compute_file_hash(test_content)

    assert result == expected_hash
    assert isinstance(result, str)
    assert len(result) == 64  # SHA-256 produces 64 character hex string


def test_compute_file_hash_empty():
    """Test hash computation for empty file"""
    test_content = b""
    expected_hash = hashlib.sha256(test_content).hexdigest()

    result = compute_file_hash(test_content)

    assert result == expected_hash


def test_compute_file_hash_large():
    """Test hash computation for large file"""
    # Create 1MB of random content
    test_content = b"x" * (1024 * 1024)
    expected_hash = hashlib.sha256(test_content).hexdigest()

    result = compute_file_hash(test_content)

    assert result == expected_hash


def test_compute_file_hash_streaming():
    """Test streaming hash computation"""
    test_content = b"This is a test file content for streaming"
    file_obj = BytesIO(test_content)

    expected_hash = hashlib.sha256(test_content).hexdigest()

    result = compute_file_hash_streaming(file_obj)

    assert result == expected_hash
    # Verify file pointer was reset
    assert file_obj.tell() == 0


def test_compute_file_hash_streaming_large():
    """Test streaming hash with large file"""
    # 5MB file
    test_content = b"y" * (5 * 1024 * 1024)
    file_obj = BytesIO(test_content)

    expected_hash = hashlib.sha256(test_content).hexdigest()

    result = compute_file_hash_streaming(file_obj, chunk_size=8192)

    assert result == expected_hash
    assert file_obj.tell() == 0  # Pointer reset


def test_compute_file_hash_consistency():
    """Test that both methods produce same hash"""
    test_content = b"Test content for consistency check"
    file_obj = BytesIO(test_content)

    hash_direct = compute_file_hash(test_content)
    hash_streaming = compute_file_hash_streaming(file_obj)

    assert hash_direct == hash_streaming


def test_verify_file_hash_success():
    """Test successful hash verification"""
    test_content = b"Test content"
    expected_hash = compute_file_hash(test_content)

    result = verify_file_hash(test_content, expected_hash)

    assert result is True


def test_verify_file_hash_failure():
    """Test failed hash verification"""
    test_content = b"Test content"
    wrong_hash = "0" * 64

    result = verify_file_hash(test_content, wrong_hash)

    assert result is False


def test_verify_file_hash_case_insensitive():
    """Test hash verification is case insensitive"""
    test_content = b"Test content"
    hash_lowercase = compute_file_hash(test_content)
    hash_uppercase = hash_lowercase.upper()

    result_lower = verify_file_hash(test_content, hash_lowercase)
    result_upper = verify_file_hash(test_content, hash_uppercase)

    assert result_lower is True
    assert result_upper is True


def test_different_content_different_hash():
    """Test that different content produces different hashes"""
    content1 = b"First content"
    content2 = b"Second content"

    hash1 = compute_file_hash(content1)
    hash2 = compute_file_hash(content2)

    assert hash1 != hash2


def test_same_content_same_hash():
    """Test that identical content produces identical hash"""
    content = b"Identical content"

    hash1 = compute_file_hash(content)
    hash2 = compute_file_hash(content)

    assert hash1 == hash2


def test_hash_deterministic():
    """Test that hash computation is deterministic"""
    content = b"Deterministic test content"

    hashes = [compute_file_hash(content) for _ in range(5)]

    # All hashes should be identical
    assert len(set(hashes)) == 1
