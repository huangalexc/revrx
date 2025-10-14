"""
Celery Tasks for Report Processing
Distributed async report generation using Celery workers
"""

import asyncio
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
import structlog

from app.celery_app import celery_app
from app.services.report_processor import process_report_async
from app.core.database import prisma
from prisma import enums

logger = structlog.get_logger(__name__)


class AsyncPrismaTask(Task):
    """
    Custom Celery task class that manages Prisma database connection lifecycle

    Prisma client is async and requires connection management per task.
    This base class ensures proper connection and cleanup.
    """

    def before_start(self, task_id, args, kwargs):
        """Connect to database before task starts"""
        logger.debug("Connecting to database", task_id=task_id)
        # Connection will be established in async context

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Disconnect from database after task completes"""
        logger.debug("Task completed, cleaning up", task_id=task_id, status=status)
        # Cleanup will be handled in async context


@celery_app.task(
    name="app.tasks.report_tasks.process_report",
    base=AsyncPrismaTask,
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
)
def process_report(self, report_id: str) -> dict:
    """
    Celery task to process a report asynchronously

    This task wraps the async report processing function and manages
    the database connection lifecycle.

    Args:
        report_id: ID of the report to process

    Returns:
        dict: Result with status and report data

    Raises:
        Exception: Re-raises exceptions for Celery retry mechanism
    """
    task_id = self.request.id
    logger.info(
        "Celery task starting report processing",
        task_id=task_id,
        report_id=report_id,
        attempt=self.request.retries + 1
    )

    try:
        # Run async function in new event loop
        result = asyncio.run(_process_report_with_connection(report_id, task_id))

        logger.info(
            "Celery task completed successfully",
            task_id=task_id,
            report_id=report_id,
            status=result.get("status")
        )

        return result

    except SoftTimeLimitExceeded:
        logger.error(
            "Celery task soft time limit exceeded",
            task_id=task_id,
            report_id=report_id
        )

        # Mark report as failed due to timeout
        asyncio.run(_mark_report_failed(
            report_id,
            "Task exceeded time limit (4 minutes)"
        ))

        raise  # Re-raise for Celery to handle

    except Exception as e:
        logger.error(
            "Celery task failed",
            task_id=task_id,
            report_id=report_id,
            error=str(e),
            attempt=self.request.retries + 1
        )

        # Mark report as failed if max retries reached
        if self.request.retries >= self.max_retries:
            asyncio.run(_mark_report_failed(
                report_id,
                f"Task failed after {self.max_retries} retries: {str(e)}"
            ))

        raise  # Re-raise for Celery retry mechanism


async def _process_report_with_connection(report_id: str, task_id: str) -> dict:
    """
    Process report with proper database connection management

    Args:
        report_id: ID of the report to process
        task_id: Celery task ID for logging

    Returns:
        dict: Result with status and report data
    """
    try:
        # Connect to database
        if not prisma.is_connected():
            await prisma.connect()

        # Process the report using existing async processor
        await process_report_async(report_id, max_retries=1)  # Celery handles retries

        # Fetch final report
        report = await prisma.report.find_unique(
            where={"id": report_id},
            include={"encounter": True}
        )

        return {
            "status": report.status,
            "report_id": report_id,
            "task_id": task_id,
            "progress_percent": report.progressPercent,
            "processing_time_ms": report.processingTimeMs,
        }

    finally:
        # Disconnect from database
        if prisma.is_connected():
            await prisma.disconnect()


async def _mark_report_failed(report_id: str, error_message: str):
    """
    Mark a report as failed in the database

    Args:
        report_id: ID of the report
        error_message: Error message to store
    """
    try:
        if not prisma.is_connected():
            await prisma.connect()

        await prisma.report.update(
            where={"id": report_id},
            data={
                "status": enums.ReportStatus.FAILED,
                "errorMessage": error_message,
                "currentStep": "failed"
            }
        )

    except Exception as e:
        logger.error(
            "Failed to mark report as failed",
            report_id=report_id,
            error=str(e)
        )
    finally:
        if prisma.is_connected():
            await prisma.disconnect()


@celery_app.task(name="app.tasks.report_tasks.cleanup_old_results")
def cleanup_old_results() -> dict:
    """
    Periodic task to clean up old Celery results from Redis

    This task should be scheduled to run daily to prevent Redis memory growth.

    Returns:
        dict: Cleanup statistics
    """
    try:
        # Celery automatically expires results based on result_expires setting
        # This task is a placeholder for additional cleanup logic if needed

        logger.info("Cleanup task completed")

        return {
            "status": "success",
            "message": "Old results cleaned up"
        }

    except Exception as e:
        logger.error("Cleanup task failed", error=str(e))
        return {
            "status": "failed",
            "error": str(e)
        }


# Utility function to queue a report processing task
def queue_report_processing_celery(report_id: str) -> str:
    """
    Queue a report for processing using Celery

    Args:
        report_id: ID of the report to process

    Returns:
        str: Celery task ID
    """
    task = process_report.apply_async(
        args=[report_id],
        queue="reports",
        routing_key="reports.process"
    )

    logger.info(
        "Report queued for Celery processing",
        report_id=report_id,
        task_id=task.id
    )

    return task.id
