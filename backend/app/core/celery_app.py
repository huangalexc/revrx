"""
Celery Configuration for Background Tasks
Handles asynchronous encounter processing
"""

from celery import Celery
from celery.signals import worker_ready, worker_shutdown
import structlog

from app.core.config import settings


logger = structlog.get_logger(__name__)


# Create Celery app
celery_app = Celery(
    "revrx",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.encounter_tasks",
        "app.tasks.retention_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "app.tasks.encounter_tasks.*": {"queue": "encounters"},
        "app.tasks.retention_tasks.*": {"queue": "maintenance"},
    },
    # Task execution
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task time limits
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit
    # Task retries
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,
)


@worker_ready.connect
def on_worker_ready(**kwargs):
    """Called when Celery worker is ready"""
    logger.info("Celery worker is ready")


@worker_shutdown.connect
def on_worker_shutdown(**kwargs):
    """Called when Celery worker is shutting down"""
    logger.info("Celery worker is shutting down")
