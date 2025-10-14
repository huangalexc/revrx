"""
Monitoring and Health Check Endpoints
Provides health checks and metrics for Celery workers and Redis
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import structlog
import redis

from app.core.config import settings
from app.services.task_queue import get_queue_stats

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Overall system health check

    Returns:
        dict: Health status
    """
    return {
        "status": "healthy",
        "service": "revrx-api",
        "version": "1.0.0"
    }


@router.get("/health/celery")
async def celery_health() -> Dict[str, Any]:
    """
    Check Celery worker health

    Returns:
        dict: Celery worker status and count

    Raises:
        HTTPException: If Celery is unavailable
    """
    try:
        # Only check Celery if enabled
        if not settings.ENABLE_CELERY:
            return {
                "status": "disabled",
                "mode": "asyncio",
                "message": "Celery is not enabled, using in-process queue"
            }

        from app.celery_app import celery_app

        # Ping workers
        inspect = celery_app.control.inspect()
        ping = inspect.ping()

        if not ping:
            logger.warning("No Celery workers responding to ping")
            raise HTTPException(
                status_code=503,
                detail="No Celery workers available"
            )

        # Get worker stats
        stats = inspect.stats()

        return {
            "status": "healthy",
            "mode": "celery",
            "workers": list(ping.keys()),
            "worker_count": len(ping),
            "stats": stats
        }

    except ImportError:
        logger.error("Celery not available (import error)")
        raise HTTPException(
            status_code=503,
            detail="Celery is not available"
        )
    except Exception as e:
        logger.error("Celery health check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Celery health check failed: {str(e)}"
        )


@router.get("/health/redis")
async def redis_health() -> Dict[str, Any]:
    """
    Check Redis connectivity and stats

    Returns:
        dict: Redis connection status and metrics

    Raises:
        HTTPException: If Redis is unavailable
    """
    try:
        # Connect to Redis
        redis_client = redis.from_url(settings.REDIS_URL)

        # Ping Redis
        redis_client.ping()

        # Get Redis info
        info = redis_client.info()

        # Extract key metrics
        memory_used = info.get('used_memory_human', 'N/A')
        connected_clients = info.get('connected_clients', 0)
        uptime_days = info.get('uptime_in_days', 0)

        return {
            "status": "healthy",
            "connected": True,
            "memory_used": memory_used,
            "connected_clients": connected_clients,
            "uptime_days": uptime_days,
            "version": info.get('redis_version', 'unknown')
        }

    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Redis is unavailable: {str(e)}"
        )


@router.get("/health/database")
async def database_health() -> Dict[str, Any]:
    """
    Check database connectivity

    Returns:
        dict: Database connection status

    Raises:
        HTTPException: If database is unavailable
    """
    try:
        from app.core.database import prisma

        # Check if connected
        is_connected = prisma.is_connected()

        if not is_connected:
            # Try to connect
            await prisma.connect()

        # Run simple query
        result = await prisma.query_raw("SELECT 1 as health_check")

        return {
            "status": "healthy",
            "connected": True,
            "query_test": "passed"
        }

    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Database is unavailable: {str(e)}"
        )


@router.get("/metrics/queue")
async def queue_metrics() -> Dict[str, Any]:
    """
    Get current queue statistics

    Returns:
        dict: Queue depth, worker count, and processing stats
    """
    try:
        stats = get_queue_stats()

        # Add additional Redis queue info
        if settings.ENABLE_CELERY:
            redis_client = redis.from_url(settings.REDIS_URL)

            # Get queue depths for all known queues
            reports_queue = redis_client.llen('celery:reports')
            default_queue = redis_client.llen('celery')

            stats['queues'] = {
                'reports': reports_queue,
                'default': default_queue,
                'total': reports_queue + default_queue
            }

        return {
            "status": "success",
            "metrics": stats
        }

    except Exception as e:
        logger.error("Failed to get queue metrics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get queue metrics: {str(e)}"
        )


@router.get("/metrics/workers")
async def worker_metrics() -> Dict[str, Any]:
    """
    Get detailed worker metrics

    Returns:
        dict: Worker utilization, active tasks, and performance stats

    Raises:
        HTTPException: If metrics unavailable
    """
    try:
        if not settings.ENABLE_CELERY:
            return {
                "status": "disabled",
                "mode": "asyncio",
                "message": "Worker metrics only available in Celery mode"
            }

        from app.celery_app import celery_app, get_celery_stats

        # Get comprehensive stats
        stats = get_celery_stats()

        # Get active tasks details
        inspect = celery_app.control.inspect()
        active = inspect.active() or {}
        scheduled = inspect.scheduled() or {}
        reserved = inspect.reserved() or {}

        return {
            "status": "success",
            "worker_count": stats.get('worker_count', 0),
            "active_tasks": stats.get('active_tasks', 0),
            "scheduled_tasks": stats.get('scheduled_tasks', 0),
            "reserved_tasks": stats.get('reserved_tasks', 0),
            "total_pending": stats.get('total_pending', 0),
            "workers": stats.get('workers', []),
            "registered_tasks": stats.get('registered_tasks', []),
            "active_by_worker": {
                worker: len(tasks)
                for worker, tasks in active.items()
            },
            "scheduled_by_worker": {
                worker: len(tasks)
                for worker, tasks in scheduled.items()
            }
        }

    except Exception as e:
        logger.error("Failed to get worker metrics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get worker metrics: {str(e)}"
        )


@router.get("/metrics/processing")
async def processing_metrics() -> Dict[str, Any]:
    """
    Get report processing statistics from database

    Returns:
        dict: Report status counts and processing times
    """
    try:
        from app.core.database import prisma
        from prisma import enums

        # Count reports by status
        pending_count = await prisma.report.count(
            where={"status": enums.ReportStatus.PENDING}
        )
        processing_count = await prisma.report.count(
            where={"status": enums.ReportStatus.PROCESSING}
        )
        complete_count = await prisma.report.count(
            where={"status": enums.ReportStatus.COMPLETE}
        )
        failed_count = await prisma.report.count(
            where={"status": enums.ReportStatus.FAILED}
        )

        # Get average processing time for completed reports (last 100)
        recent_reports = await prisma.report.find_many(
            where={"status": enums.ReportStatus.COMPLETE},
            order={"processingCompletedAt": "desc"},
            take=100
        )

        avg_processing_time = 0
        if recent_reports:
            total_time = sum(
                r.processingTimeMs or 0
                for r in recent_reports
            )
            avg_processing_time = total_time / len(recent_reports)

        # Get failure rate (last 100 reports)
        recent_all = await prisma.report.find_many(
            order={"createdAt": "desc"},
            take=100
        )

        failure_rate = 0
        if recent_all:
            failed = sum(
                1 for r in recent_all
                if r.status == enums.ReportStatus.FAILED
            )
            failure_rate = (failed / len(recent_all)) * 100

        return {
            "status": "success",
            "report_counts": {
                "pending": pending_count,
                "processing": processing_count,
                "complete": complete_count,
                "failed": failed_count,
                "total": pending_count + processing_count + complete_count + failed_count
            },
            "performance": {
                "avg_processing_time_ms": round(avg_processing_time, 2),
                "avg_processing_time_seconds": round(avg_processing_time / 1000, 2),
                "failure_rate_percent": round(failure_rate, 2)
            }
        }

    except Exception as e:
        logger.error("Failed to get processing metrics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get processing metrics: {str(e)}"
        )


@router.get("/status")
async def system_status() -> Dict[str, Any]:
    """
    Comprehensive system status check

    Returns:
        dict: Status of all components (API, Celery, Redis, Database, Queue)
    """
    status = {
        "overall": "healthy",
        "components": {}
    }

    # Check API
    status["components"]["api"] = {"status": "healthy"}

    # Check Database
    try:
        from app.core.database import prisma
        is_connected = prisma.is_connected()
        status["components"]["database"] = {
            "status": "healthy" if is_connected else "degraded",
            "connected": is_connected
        }
    except Exception as e:
        status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        status["overall"] = "degraded"

    # Check Redis
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        status["components"]["redis"] = {
            "status": "healthy",
            "connected": True
        }
    except Exception as e:
        status["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        status["overall"] = "degraded"

    # Check Celery (if enabled)
    if settings.ENABLE_CELERY:
        try:
            from app.celery_app import celery_app
            inspect = celery_app.control.inspect()
            ping = inspect.ping()

            if ping:
                status["components"]["celery"] = {
                    "status": "healthy",
                    "worker_count": len(ping)
                }
            else:
                status["components"]["celery"] = {
                    "status": "unhealthy",
                    "error": "No workers responding"
                }
                status["overall"] = "degraded"
        except Exception as e:
            status["components"]["celery"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            status["overall"] = "degraded"
    else:
        status["components"]["celery"] = {
            "status": "disabled",
            "mode": "asyncio"
        }

    # Get queue stats
    try:
        queue_stats = get_queue_stats()
        status["components"]["queue"] = {
            "status": "healthy",
            "backend": queue_stats.get("backend"),
            "depth": queue_stats.get("total_tasks", 0)
        }
    except Exception as e:
        status["components"]["queue"] = {
            "status": "unknown",
            "error": str(e)
        }

    return status
