"""
Task Queue Manager for Async Report Processing

Supports two modes:
- Phase 1: In-process queue using asyncio (default for development)
- Phase 2: Celery + Redis for distributed processing (production)

Set ENABLE_CELERY=true in environment to use Celery mode.
"""

import asyncio
from typing import Dict, Optional
import structlog
import os

from app.services.report_processor import process_report_async

logger = structlog.get_logger(__name__)

# Determine which queue backend to use
USE_CELERY = os.getenv("ENABLE_CELERY", "false").lower() == "true"


class TaskQueue:
    """
    In-process task queue for background report processing

    Manages running tasks and provides simple queuing mechanism
    """

    def __init__(self):
        self._running_tasks: Dict[str, asyncio.Task] = {}
        logger.info("Task queue initialized")

    def queue_report_processing(self, report_id: str) -> None:
        """
        Queue a report for background processing

        Args:
            report_id: Report ID to process

        Returns:
            None (processing happens in background)
        """
        # Check if already processing
        if report_id in self._running_tasks:
            task = self._running_tasks[report_id]
            if not task.done():
                logger.warning(
                    "Report already queued for processing",
                    report_id=report_id
                )
                return

        # Create background task
        task = asyncio.create_task(self._process_with_cleanup(report_id))
        self._running_tasks[report_id] = task

        logger.info(
            "Report queued for background processing",
            report_id=report_id,
            total_running_tasks=len([t for t in self._running_tasks.values() if not t.done()])
        )

    async def _process_with_cleanup(self, report_id: str) -> None:
        """
        Process report and clean up task when done

        Args:
            report_id: Report ID to process
        """
        try:
            await process_report_async(report_id)
        except Exception as e:
            logger.error(
                "Background report processing failed",
                report_id=report_id,
                error=str(e)
            )
        finally:
            # Clean up completed task
            if report_id in self._running_tasks:
                del self._running_tasks[report_id]

    def get_task_status(self, report_id: str) -> Optional[str]:
        """
        Get status of a queued task

        Args:
            report_id: Report ID

        Returns:
            "running", "completed", or None if not found
        """
        if report_id not in self._running_tasks:
            return None

        task = self._running_tasks[report_id]
        return "completed" if task.done() else "running"

    def get_running_count(self) -> int:
        """
        Get count of currently running tasks

        Returns:
            Number of tasks currently processing
        """
        return len([t for t in self._running_tasks.values() if not t.done()])

    def get_queue_stats(self) -> Dict[str, int]:
        """
        Get queue statistics

        Returns:
            Dictionary with queue metrics
        """
        total = len(self._running_tasks)
        running = self.get_running_count()
        completed = total - running

        return {
            "total_tasks": total,
            "running_tasks": running,
            "completed_tasks": completed
        }


# Global task queue instance
task_queue = TaskQueue()


def queue_report_processing(report_id: str) -> Optional[str]:
    """
    Convenience function to queue report processing

    Automatically uses Celery if enabled, otherwise falls back to in-process queue.

    Args:
        report_id: Report ID to process

    Returns:
        Optional[str]: Celery task ID if using Celery, None otherwise
    """
    if USE_CELERY:
        try:
            from app.tasks.report_tasks import queue_report_processing_celery
            task_id = queue_report_processing_celery(report_id)
            logger.info(
                "Report queued via Celery",
                report_id=report_id,
                task_id=task_id,
                backend="celery"
            )
            return task_id
        except Exception as e:
            logger.error(
                "Failed to queue report via Celery, falling back to in-process",
                report_id=report_id,
                error=str(e)
            )
            task_queue.queue_report_processing(report_id)
            return None
    else:
        logger.info(
            "Report queued via in-process queue",
            report_id=report_id,
            backend="asyncio"
        )
        task_queue.queue_report_processing(report_id)
        return None


def get_queue_stats() -> Dict[str, int]:
    """
    Get current queue statistics

    Returns stats from Celery if enabled, otherwise from in-process queue.

    Returns:
        Dictionary with queue metrics
    """
    if USE_CELERY:
        try:
            from app.celery_app import get_celery_stats
            stats = get_celery_stats()
            logger.debug("Retrieved Celery queue stats", stats=stats)
            return {
                "total_tasks": stats.get("total_pending", 0),
                "running_tasks": stats.get("active_tasks", 0),
                "worker_count": stats.get("worker_count", 0),
                "backend": "celery"
            }
        except Exception as e:
            logger.error("Failed to get Celery stats", error=str(e))
            return {"error": str(e), "backend": "celery"}
    else:
        return {**task_queue.get_queue_stats(), "backend": "asyncio"}
