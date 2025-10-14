"""
Celery Application Configuration
Distributed task queue for async report processing
"""

from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure, worker_ready
import structlog
from app.core.config import settings
from app.core.database import prisma

logger = structlog.get_logger(__name__)

# Determine broker and result backend URLs
broker_url = settings.CELERY_BROKER_URL or settings.REDIS_URL
result_backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

# Create Celery instance
celery_app = Celery(
    "revrx",
    broker=broker_url,
    backend=result_backend,
    include=["app.tasks.report_tasks"]
)

# Configure Celery
celery_app.conf.update(
    # Task execution settings
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    # Result backend settings
    result_expires=settings.CELERY_RESULT_EXPIRES,
    result_backend_transport_options={
        "global_keyprefix": "celery_revrx",
        "max_connections": 100,
    },

    # Worker settings
    worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (memory leak prevention)
    worker_disable_rate_limits=False,

    # Task time limits
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Requeue task if worker dies

    # Retry settings
    task_autoretry_for=(Exception,),
    task_retry_kwargs={"max_retries": 3, "countdown": 5},
    task_default_retry_delay=5,

    # Result backend settings
    result_extended=True,  # Store task args and kwargs
    result_compression="gzip",

    # Monitoring
    task_send_sent_event=True,
    worker_send_task_events=True,
    task_track_started=True,

    # Queue routing
    task_routes={
        "app.tasks.report_tasks.*": {"queue": "reports"},
    },
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",

    # Beat scheduler (for periodic tasks)
    beat_schedule={},
)

# Celery signals for lifecycle management


@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    """Connect to database when worker starts"""
    logger.info("Celery worker starting", worker=sender)
    # Note: Prisma connection should be established per-task, not per-worker
    # due to async nature of Prisma client


@task_prerun.connect
def on_task_prerun(task_id, task, args, kwargs, **extras):
    """Log before task execution"""
    logger.info(
        "Task starting",
        task_id=task_id,
        task_name=task.name,
        task_args=args,
        task_kwargs=kwargs
    )


@task_postrun.connect
def on_task_postrun(task_id, task, args, kwargs, retval, **extras):
    """Log after task execution"""
    logger.info(
        "Task completed",
        task_id=task_id,
        task_name=task.name,
        task_result=str(retval)[:100] if retval else None
    )


@task_failure.connect
def on_task_failure(task_id, exception, args, kwargs, traceback, einfo, **extras):
    """Log task failures"""
    logger.error(
        "Task failed",
        task_id=task_id,
        exception=str(exception),
        traceback=str(traceback)[:500],
        task_args=args,
        task_kwargs=kwargs
    )


# Health check task
@celery_app.task(name="app.celery_app.health_check")
def health_check() -> dict:
    """
    Health check task to verify Celery workers are responsive

    Returns:
        dict: Health status
    """
    return {
        "status": "healthy",
        "worker": "responsive",
        "broker": broker_url.split("@")[-1] if "@" in broker_url else broker_url
    }


# Utility function to get Celery stats
def get_celery_stats() -> dict:
    """
    Get Celery queue and worker statistics

    Returns:
        dict: Statistics including active tasks, queue depth, worker count
    """
    try:
        inspect = celery_app.control.inspect()

        # Get active tasks
        active = inspect.active() or {}
        active_count = sum(len(tasks) for tasks in active.values())

        # Get scheduled tasks
        scheduled = inspect.scheduled() or {}
        scheduled_count = sum(len(tasks) for tasks in scheduled.values())

        # Get reserved tasks
        reserved = inspect.reserved() or {}
        reserved_count = sum(len(tasks) for tasks in reserved.values())

        # Get registered tasks
        registered = inspect.registered() or {}

        # Get worker stats
        stats = inspect.stats() or {}
        worker_count = len(stats)

        return {
            "active_tasks": active_count,
            "scheduled_tasks": scheduled_count,
            "reserved_tasks": reserved_count,
            "total_pending": active_count + scheduled_count + reserved_count,
            "worker_count": worker_count,
            "workers": list(stats.keys()),
            "registered_tasks": list(set(task for tasks in registered.values() for task in tasks)),
        }
    except Exception as e:
        logger.error("Failed to get Celery stats", error=str(e))
        return {
            "error": str(e),
            "active_tasks": 0,
            "worker_count": 0,
        }


if __name__ == "__main__":
    # Start worker from command line: python -m app.celery_app worker
    celery_app.start()
