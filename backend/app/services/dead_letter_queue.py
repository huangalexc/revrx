"""
Dead Letter Queue Service
Handles permanently failed reports for debugging and manual retry
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog

from app.core.database import prisma
from app.services.task_queue import queue_report_processing
from prisma import enums

logger = structlog.get_logger(__name__)


async def get_failed_reports(
    limit: int = 50,
    offset: int = 0,
    min_retry_count: int = 3
) -> Dict[str, Any]:
    """
    Get all permanently failed reports (after max retries)

    Args:
        limit: Maximum number of reports to return
        offset: Pagination offset
        min_retry_count: Minimum retry count to consider "permanently failed"

    Returns:
        Dictionary with failed reports and metadata
    """
    # Query for failed reports with retry count >= min_retry_count
    failed_reports = await prisma.report.find_many(
        where={
            "status": enums.ReportStatus.FAILED,
            "retryCount": {"gte": min_retry_count}
        },
        include={
            "encounter": {
                "include": {
                    "user": True
                }
            }
        },
        order={"processingStartedAt": "desc"},
        take=limit,
        skip=offset
    )

    # Get total count for pagination
    total_count = await prisma.report.count(
        where={
            "status": enums.ReportStatus.FAILED,
            "retryCount": {"gte": min_retry_count}
        }
    )

    # Format reports for response
    formatted_reports = []
    for report in failed_reports:
        formatted_reports.append({
            "report_id": report.id,
            "encounter_id": report.encounterId,
            "user_email": report.encounter.user.email if report.encounter and report.encounter.user else None,
            "retry_count": report.retryCount,
            "error_message": report.errorMessage,
            "error_details": report.errorDetails,
            "processing_started_at": report.processingStartedAt.isoformat() if report.processingStartedAt else None,
            "current_step": report.currentStep,
            "progress_percent": report.progressPercent,
        })

    return {
        "failed_reports": formatted_reports,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + len(failed_reports)) < total_count
    }


async def retry_failed_report(report_id: str, force: bool = False) -> Dict[str, Any]:
    """
    Retry a failed report

    Args:
        report_id: Report ID to retry
        force: Force retry even if retry count is high

    Returns:
        Dictionary with retry status
    """
    # Get report
    report = await prisma.report.find_unique(
        where={"id": report_id}
    )

    if not report:
        raise ValueError(f"Report {report_id} not found")

    if report.status != enums.ReportStatus.FAILED:
        raise ValueError(f"Report {report_id} is not in FAILED status (current: {report.status})")

    # Check retry count
    if not force and report.retryCount >= 5:
        raise ValueError(
            f"Report {report_id} has exceeded maximum retries ({report.retryCount}). "
            "Use force=True to retry anyway."
        )

    # Reset report status to PENDING
    await prisma.report.update(
        where={"id": report_id},
        data={
            "status": enums.ReportStatus.PENDING,
            "progressPercent": 0,
            "currentStep": "queued_for_retry",
            "processingStartedAt": None,
            "processingCompletedAt": None,
            "processingTimeMs": None,
            "errorMessage": None,
            "errorDetails": None,
        }
    )

    # Queue for processing
    queue_report_processing(report_id)

    logger.info(
        "Failed report queued for retry",
        report_id=report_id,
        previous_retry_count=report.retryCount,
        force=force
    )

    return {
        "report_id": report_id,
        "status": "queued_for_retry",
        "previous_retry_count": report.retryCount,
        "message": "Report has been reset and queued for processing"
    }


async def bulk_retry_failed_reports(
    min_retry_count: int = 3,
    max_age_hours: Optional[int] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Bulk retry multiple failed reports

    Args:
        min_retry_count: Minimum retry count to include
        max_age_hours: Only retry reports failed within this many hours
        limit: Maximum number of reports to retry

    Returns:
        Dictionary with bulk retry results
    """
    # Build query filters
    where_clause = {
        "status": enums.ReportStatus.FAILED,
        "retryCount": {"gte": min_retry_count}
    }

    if max_age_hours:
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        where_clause["processingStartedAt"] = {"gte": cutoff_time}

    # Get failed reports
    failed_reports = await prisma.report.find_many(
        where=where_clause,
        order={"processingStartedAt": "desc"},
        take=limit
    )

    # Retry each report
    results = {
        "total_attempted": len(failed_reports),
        "successful": 0,
        "failed": 0,
        "errors": []
    }

    for report in failed_reports:
        try:
            await retry_failed_report(report.id, force=True)
            results["successful"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({
                "report_id": report.id,
                "error": str(e)
            })
            logger.error(
                "Failed to retry report in bulk operation",
                report_id=report.id,
                error=str(e)
            )

    logger.info(
        "Bulk retry completed",
        total_attempted=results["total_attempted"],
        successful=results["successful"],
        failed=results["failed"]
    )

    return results


async def get_failure_statistics(days: int = 7) -> Dict[str, Any]:
    """
    Get statistics about report failures

    Args:
        days: Number of days to analyze

    Returns:
        Dictionary with failure statistics
    """
    cutoff_time = datetime.utcnow() - timedelta(days=days)

    # Get all failed reports in time window
    failed_reports = await prisma.report.find_many(
        where={
            "status": enums.ReportStatus.FAILED,
            "processingStartedAt": {"gte": cutoff_time}
        }
    )

    # Analyze error patterns
    error_types = {}
    failure_steps = {}
    total_failures = len(failed_reports)

    for report in failed_reports:
        # Count by error message pattern
        error_msg = report.errorMessage or "Unknown error"
        error_key = error_msg[:100]  # First 100 chars as key
        error_types[error_key] = error_types.get(error_key, 0) + 1

        # Count by failure step
        step = report.currentStep or "unknown"
        failure_steps[step] = failure_steps.get(step, 0) + 1

    # Sort by frequency
    top_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10]
    top_failure_steps = sorted(failure_steps.items(), key=lambda x: x[1], reverse=True)

    return {
        "days_analyzed": days,
        "total_failures": total_failures,
        "top_error_messages": [
            {"message": msg, "count": count}
            for msg, count in top_errors
        ],
        "failures_by_step": [
            {"step": step, "count": count}
            for step, count in top_failure_steps
        ],
        "permanently_failed_count": await prisma.report.count(
            where={
                "status": enums.ReportStatus.FAILED,
                "retryCount": {"gte": 3}
            }
        )
    }
