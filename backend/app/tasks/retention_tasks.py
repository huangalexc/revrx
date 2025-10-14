"""
Celery Tasks for Data Retention
Scheduled tasks for HIPAA-compliant data deletion
"""

import structlog
import asyncio

from app.core.celery_app import celery_app
from app.services.data_retention import data_retention_service


logger = structlog.get_logger(__name__)


@celery_app.task(name="run_retention_cleanup")
def run_retention_cleanup_task():
    """
    Run data retention cleanup

    This task should be scheduled daily via Celery Beat
    """
    logger.info("Starting retention cleanup task")

    try:
        stats = asyncio.run(
            data_retention_service.run_retention_cleanup(
                system_user_id="system-celery-retention"
            )
        )

        logger.info(
            "Retention cleanup task completed",
            encounters_deleted=stats["total_encounters_deleted"],
            files_deleted=stats["total_files_deleted"],
        )

        return stats

    except Exception as e:
        logger.error("Retention cleanup task failed", error=str(e))
        raise
