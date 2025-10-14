"""
Duplicate Detection Service
Detect duplicate file uploads based on file hash comparison
"""

from typing import Optional, Dict, Any
from datetime import datetime
import structlog

from app.core.database import prisma
from prisma.models import UploadedFile

logger = structlog.get_logger(__name__)


class DuplicateDetectionService:
    """Service for detecting duplicate file uploads"""

    async def check_duplicate(
        self, user_id: str, file_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a file with the same hash exists for this user

        Args:
            user_id: User ID to check duplicates for
            file_hash: SHA-256 hash of file content

        Returns:
            Dictionary with duplicate file info if found, None otherwise
            {
                "file_id": str,
                "encounter_id": str,
                "original_filename": str,
                "upload_timestamp": datetime,
                "file_size": int
            }
        """
        logger.info(
            "Checking for duplicate file",
            user_id=user_id,
            file_hash_preview=file_hash[:16] if file_hash else None
        )

        # Find uploaded file with matching hash for this user
        duplicate_file = await prisma.uploadedfile.find_first(
            where={
                "fileHash": file_hash,
                "encounter": {
                    "is": {
                        "userId": user_id
                    }
                }
            },
            include={
                "encounter": True
            },
            order={
                "createdAt": "desc"  # Get most recent upload
            }
        )

        if not duplicate_file:
            logger.info("No duplicate found", user_id=user_id)
            return None

        duplicate_info = {
            "file_id": duplicate_file.id,
            "encounter_id": duplicate_file.encounterId,
            "original_filename": duplicate_file.fileName,
            "upload_timestamp": duplicate_file.createdAt,
            "file_size": duplicate_file.fileSize,
        }

        logger.info(
            "Duplicate file found",
            user_id=user_id,
            file_id=duplicate_file.id,
            original_filename=duplicate_file.fileName,
            upload_timestamp=duplicate_file.createdAt
        )

        return duplicate_info

    async def get_duplicate_count(self, user_id: str, file_hash: str) -> int:
        """
        Get count of duplicate files for this user

        Args:
            user_id: User ID
            file_hash: SHA-256 hash

        Returns:
            Count of duplicate files
        """
        count = await prisma.uploadedfile.count(
            where={
                "fileHash": file_hash,
                "encounter": {
                    "is": {
                        "userId": user_id
                    }
                }
            }
        )

        logger.debug(
            "Duplicate count",
            user_id=user_id,
            file_hash_preview=file_hash[:16],
            count=count
        )

        return count

    async def mark_as_duplicate(
        self,
        file_id: str,
        original_file_id: str,
        duplicate_handling: str
    ) -> UploadedFile:
        """
        Mark a file as duplicate and record handling decision

        Args:
            file_id: ID of the duplicate file
            original_file_id: ID of the original file
            duplicate_handling: How duplicate was handled (SKIP, REPLACE, PROCESS_AS_NEW)

        Returns:
            Updated UploadedFile record
        """
        updated_file = await prisma.uploadedfile.update(
            where={"id": file_id},
            data={
                "isDuplicate": True,
                "originalFileId": original_file_id,
                "duplicateHandling": duplicate_handling
            }
        )

        logger.info(
            "File marked as duplicate",
            file_id=file_id,
            original_file_id=original_file_id,
            duplicate_handling=duplicate_handling
        )

        return updated_file

    async def get_all_duplicates_for_user(
        self, user_id: str, limit: int = 100
    ) -> list:
        """
        Get all duplicate files for a user

        Args:
            user_id: User ID
            limit: Maximum number of results to return

        Returns:
            List of duplicate file records
        """
        duplicates = await prisma.uploadedfile.find_many(
            where={
                "isDuplicate": True,
                "encounter": {
                    "is": {
                        "userId": user_id
                    }
                }
            },
            include={
                "encounter": True
            },
            order={
                "createdAt": "desc"
            },
            take=limit
        )

        logger.info(
            "Retrieved duplicates for user",
            user_id=user_id,
            duplicate_count=len(duplicates)
        )

        return duplicates


# Singleton instance
duplicate_detection_service = DuplicateDetectionService()
