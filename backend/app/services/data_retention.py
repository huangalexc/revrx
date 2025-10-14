"""
Data Retention Service
Implements HIPAA-compliant data retention and deletion policies
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import structlog

from app.core.database import prisma
from app.core.config import settings
from app.core.storage import storage_service
from prisma import Json


logger = structlog.get_logger(__name__)


class DataRetentionService:
    """
    Service for managing data retention and automated deletion

    HIPAA Requirements:
    - Medical records must be retained for minimum 6 years
    - Some states require 7+ years
    - PHI must be securely deleted after retention period
    - Audit logs must track all deletions
    """

    def __init__(self):
        self.retention_days = settings.DATA_RETENTION_DAYS  # Default: 2555 days (7 years)
        logger.info("Data retention service initialized", retention_days=self.retention_days)

    async def find_expired_encounters(self) -> List[str]:
        """
        Find encounters that have exceeded retention period

        Returns:
            List of encounter IDs to be deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)

        logger.info(
            "Finding expired encounters",
            cutoff_date=cutoff_date.isoformat(),
            retention_days=self.retention_days,
        )

        # Find encounters older than retention period
        expired_encounters = await prisma.encounter.find_many(
            where={"createdAt": {"lt": cutoff_date}},
            select={"id": True, "createdAt": True, "userId": True},
        )

        encounter_ids = [e.id for e in expired_encounters]

        logger.info(
            "Found expired encounters",
            count=len(encounter_ids),
            oldest_date=min([e.createdAt for e in expired_encounters]).isoformat()
            if expired_encounters
            else None,
        )

        return encounter_ids

    async def delete_encounter_data(self, encounter_id: str, user_id: str) -> Dict[str, Any]:
        """
        Delete all data associated with an encounter

        Args:
            encounter_id: Encounter ID to delete
            user_id: User ID for audit logging (system user for automated deletion)

        Returns:
            Dictionary with deletion statistics

        Deletes:
        - Uploaded files from S3
        - Encounter record (cascades to uploaded_files, phi_mapping, report)
        - Audit log of deletion
        """
        logger.info("Starting encounter data deletion", encounter_id=encounter_id)

        stats = {
            "encounter_id": encounter_id,
            "deleted_files": 0,
            "deleted_s3_objects": 0,
            "deleted_db_records": 0,
            "errors": [],
        }

        try:
            # Fetch encounter and related data
            encounter = await prisma.encounter.find_unique(
                where={"id": encounter_id},
                include={
                    "uploadedFiles": True,
                    "report": True,
                    "phiMapping": True,
                },
            )

            if not encounter:
                logger.warning("Encounter not found", encounter_id=encounter_id)
                return stats

            # Delete files from S3
            for uploaded_file in encounter.uploadedFiles:
                try:
                    await storage_service.delete_file(uploaded_file.filePath)
                    stats["deleted_s3_objects"] += 1
                    logger.debug(
                        "Deleted S3 file",
                        encounter_id=encounter_id,
                        file_path=uploaded_file.filePath,
                    )
                except Exception as e:
                    error_msg = f"Failed to delete S3 file {uploaded_file.filePath}: {str(e)}"
                    stats["errors"].append(error_msg)
                    logger.error(
                        "Failed to delete S3 file",
                        encounter_id=encounter_id,
                        file_path=uploaded_file.filePath,
                        error=str(e),
                    )

            stats["deleted_files"] = len(encounter.uploadedFiles)

            # Log deletion in audit log before deleting
            await prisma.auditlog.create(
                data={
                    "userId": user_id,
                    "action": "ENCOUNTER_DELETED",
                    "resourceType": "Encounter",
                    "resourceId": encounter_id,
                    "metadata": Json({
                        "reason": "data_retention_policy",
                        "retention_days": self.retention_days,
                        "encounter_created_at": encounter.createdAt.isoformat(),
                        "deleted_files": stats["deleted_files"],
                        "had_phi_mapping": encounter.phiMapping is not None,
                        "had_report": encounter.report is not None,
                    }),
                }
            )

            # Delete encounter (cascades to related records)
            await prisma.encounter.delete(where={"id": encounter_id})
            stats["deleted_db_records"] = 1

            logger.info(
                "Encounter data deletion completed",
                encounter_id=encounter_id,
                stats=stats,
            )

        except Exception as e:
            error_msg = f"Failed to delete encounter {encounter_id}: {str(e)}"
            stats["errors"].append(error_msg)
            logger.error(
                "Encounter deletion failed",
                encounter_id=encounter_id,
                error=str(e),
            )

        return stats

    async def run_retention_cleanup(self, system_user_id: str = "system") -> Dict[str, Any]:
        """
        Run automated data retention cleanup

        This should be called by a scheduled job (e.g., daily cron)

        Args:
            system_user_id: User ID for audit logging (default: "system")

        Returns:
            Dictionary with cleanup statistics
        """
        logger.info("Starting data retention cleanup")

        cleanup_stats = {
            "started_at": datetime.utcnow().isoformat(),
            "total_encounters_deleted": 0,
            "total_files_deleted": 0,
            "total_s3_objects_deleted": 0,
            "errors": [],
        }

        try:
            # Find expired encounters
            expired_encounter_ids = await self.find_expired_encounters()

            if not expired_encounter_ids:
                logger.info("No expired encounters found")
                cleanup_stats["completed_at"] = datetime.utcnow().isoformat()
                return cleanup_stats

            # Delete each encounter
            for encounter_id in expired_encounter_ids:
                deletion_stats = await self.delete_encounter_data(
                    encounter_id, system_user_id
                )

                if deletion_stats.get("deleted_db_records", 0) > 0:
                    cleanup_stats["total_encounters_deleted"] += 1

                cleanup_stats["total_files_deleted"] += deletion_stats.get(
                    "deleted_files", 0
                )
                cleanup_stats["total_s3_objects_deleted"] += deletion_stats.get(
                    "deleted_s3_objects", 0
                )

                if deletion_stats.get("errors"):
                    cleanup_stats["errors"].extend(deletion_stats["errors"])

            cleanup_stats["completed_at"] = datetime.utcnow().isoformat()

            logger.info(
                "Data retention cleanup completed",
                stats=cleanup_stats,
            )

            # Log cleanup summary
            await prisma.auditlog.create(
                data={
                    "userId": system_user_id,
                    "action": "DATA_RETENTION_CLEANUP",
                    "resourceType": "System",
                    "resourceId": "data_retention",
                    "metadata": cleanup_stats,
                }
            )

        except Exception as e:
            error_msg = f"Data retention cleanup failed: {str(e)}"
            cleanup_stats["errors"].append(error_msg)
            logger.error("Data retention cleanup failed", error=str(e))

        return cleanup_stats

    async def get_retention_status(self, encounter_id: str) -> Dict[str, Any]:
        """
        Get retention status for an encounter

        Args:
            encounter_id: Encounter ID

        Returns:
            Dictionary with retention information
        """
        encounter = await prisma.encounter.find_unique(
            where={"id": encounter_id},
            select={"id": True, "createdAt": True},
        )

        if not encounter:
            return {"error": "Encounter not found"}

        days_since_creation = (datetime.utcnow() - encounter.createdAt).days
        days_until_deletion = self.retention_days - days_since_creation

        return {
            "encounter_id": encounter_id,
            "created_at": encounter.createdAt.isoformat(),
            "retention_days": self.retention_days,
            "days_since_creation": days_since_creation,
            "days_until_deletion": max(0, days_until_deletion),
            "will_be_deleted": days_until_deletion <= 0,
            "deletion_date": (
                encounter.createdAt + timedelta(days=self.retention_days)
            ).isoformat(),
        }

    async def get_retention_summary(self) -> Dict[str, Any]:
        """
        Get overall retention summary

        Returns:
            Dictionary with retention statistics
        """
        logger.info("Generating retention summary")

        # Count total encounters
        total_encounters = await prisma.encounter.count()

        # Count encounters expiring soon (within 30 days)
        cutoff_soon = datetime.utcnow() - timedelta(days=self.retention_days - 30)
        expiring_soon = await prisma.encounter.count(
            where={"createdAt": {"lt": cutoff_soon}}
        )

        # Count already expired
        cutoff_expired = datetime.utcnow() - timedelta(days=self.retention_days)
        already_expired = await prisma.encounter.count(
            where={"createdAt": {"lt": cutoff_expired}}
        )

        return {
            "retention_days": self.retention_days,
            "total_encounters": total_encounters,
            "expiring_within_30_days": expiring_soon,
            "already_expired": already_expired,
            "retention_policy": f"Data is retained for {self.retention_days} days ({self.retention_days // 365} years)",
        }


# Export singleton instance
data_retention_service = DataRetentionService()
