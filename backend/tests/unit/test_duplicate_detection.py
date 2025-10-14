"""
Unit tests for duplicate detection service
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.duplicate_detection import DuplicateDetectionService


@pytest.fixture
def duplicate_service():
    """Create duplicate detection service instance"""
    return DuplicateDetectionService()


@pytest.fixture
def mock_prisma():
    """Mock Prisma client"""
    with patch('app.services.duplicate_detection.prisma') as mock:
        yield mock


@pytest.mark.asyncio
async def test_check_duplicate_found(duplicate_service, mock_prisma):
    """Test finding a duplicate file"""
    user_id = "user123"
    file_hash = "abc123hash"

    # Mock duplicate file data
    mock_file = MagicMock()
    mock_file.id = "file123"
    mock_file.encounterId = "encounter123"
    mock_file.fileName = "test.pdf"
    mock_file.createdAt = datetime(2025, 1, 1, 12, 0, 0)
    mock_file.fileSize = 1024

    mock_prisma.uploadedfile.find_first = AsyncMock(return_value=mock_file)

    result = await duplicate_service.check_duplicate(user_id, file_hash)

    assert result is not None
    assert result["file_id"] == "file123"
    assert result["encounter_id"] == "encounter123"
    assert result["original_filename"] == "test.pdf"
    assert result["file_size"] == 1024


@pytest.mark.asyncio
async def test_check_duplicate_not_found(duplicate_service, mock_prisma):
    """Test when no duplicate is found"""
    user_id = "user123"
    file_hash = "uniquehash"

    mock_prisma.uploadedfile.find_first = AsyncMock(return_value=None)

    result = await duplicate_service.check_duplicate(user_id, file_hash)

    assert result is None


@pytest.mark.asyncio
async def test_get_duplicate_count(duplicate_service, mock_prisma):
    """Test getting count of duplicates"""
    user_id = "user123"
    file_hash = "abc123hash"

    mock_prisma.uploadedfile.count = AsyncMock(return_value=3)

    result = await duplicate_service.get_duplicate_count(user_id, file_hash)

    assert result == 3


@pytest.mark.asyncio
async def test_get_duplicate_count_zero(duplicate_service, mock_prisma):
    """Test duplicate count when no duplicates exist"""
    user_id = "user123"
    file_hash = "uniquehash"

    mock_prisma.uploadedfile.count = AsyncMock(return_value=0)

    result = await duplicate_service.get_duplicate_count(user_id, file_hash)

    assert result == 0


@pytest.mark.asyncio
async def test_mark_as_duplicate(duplicate_service, mock_prisma):
    """Test marking file as duplicate"""
    file_id = "file123"
    original_file_id = "original123"
    duplicate_handling = "SKIP"

    mock_updated_file = MagicMock()
    mock_updated_file.id = file_id
    mock_updated_file.isDuplicate = True
    mock_updated_file.originalFileId = original_file_id
    mock_updated_file.duplicateHandling = duplicate_handling

    mock_prisma.uploadedfile.update = AsyncMock(return_value=mock_updated_file)

    result = await duplicate_service.mark_as_duplicate(
        file_id, original_file_id, duplicate_handling
    )

    assert result.id == file_id
    assert result.isDuplicate is True
    assert result.originalFileId == original_file_id
    assert result.duplicateHandling == duplicate_handling


@pytest.mark.asyncio
async def test_get_all_duplicates_for_user(duplicate_service, mock_prisma):
    """Test retrieving all duplicates for a user"""
    user_id = "user123"

    mock_duplicates = [
        MagicMock(id="dup1", isDuplicate=True),
        MagicMock(id="dup2", isDuplicate=True),
    ]

    mock_prisma.uploadedfile.find_many = AsyncMock(return_value=mock_duplicates)

    result = await duplicate_service.get_all_duplicates_for_user(user_id)

    assert len(result) == 2
    assert all(f.isDuplicate for f in result)


@pytest.mark.asyncio
async def test_get_all_duplicates_for_user_empty(duplicate_service, mock_prisma):
    """Test retrieving duplicates when none exist"""
    user_id = "user123"

    mock_prisma.uploadedfile.find_many = AsyncMock(return_value=[])

    result = await duplicate_service.get_all_duplicates_for_user(user_id)

    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_all_duplicates_with_limit(duplicate_service, mock_prisma):
    """Test retrieving duplicates with custom limit"""
    user_id = "user123"
    limit = 5

    mock_duplicates = [MagicMock(id=f"dup{i}") for i in range(5)]
    mock_prisma.uploadedfile.find_many = AsyncMock(return_value=mock_duplicates)

    result = await duplicate_service.get_all_duplicates_for_user(user_id, limit=limit)

    # Verify find_many was called with correct limit
    call_args = mock_prisma.uploadedfile.find_many.call_args
    assert call_args.kwargs.get('take') == limit
    assert len(result) == 5
