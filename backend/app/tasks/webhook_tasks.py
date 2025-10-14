"""
Webhook Background Tasks
Celery tasks for webhook delivery retry and cleanup
"""

from celery import shared_task
from prisma import Prisma
from datetime import datetime, timedelta
from prisma.enums import WebhookDeliveryStatus

from app.core.logging import get_logger
from app.services.webhook_service import WebhookService

logger = get_logger(__name__)


@shared_task(name="retry_failed_webhooks")
def retry_failed_webhooks():
    """
    Retry webhook deliveries that are pending retry

    Runs periodically (every 5 minutes) to retry failed webhook deliveries
    with exponential backoff.
    """
    db = Prisma()
    db.connect()

    try:
        import asyncio

        loop = asyncio.get_event_loop()
        count = loop.run_until_complete(WebhookService.retry_failed_deliveries(db))

        logger.info(f"Retried {count} webhook deliveries")
        return {"retried": count}

    except Exception as e:
        logger.error(f"Error retrying webhook deliveries", error=str(e))
        raise
    finally:
        db.disconnect()


@shared_task(name="cleanup_old_webhook_deliveries")
def cleanup_old_webhook_deliveries(days_to_keep: int = 30):
    """
    Clean up old webhook delivery logs

    Removes webhook delivery records older than specified days.
    Keeps failed deliveries longer for debugging.

    Args:
        days_to_keep: Number of days to keep delivery logs (default 30)
    """
    db = Prisma()
    db.connect()

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        cutoff_date_failed = datetime.utcnow() - timedelta(days=days_to_keep * 3)  # Keep failed longer

        # Delete successful deliveries older than cutoff
        deleted_success = db.webhookdelivery.delete_many(
            where={
                "status": WebhookDeliveryStatus.DELIVERED,
                "createdAt": {"lt": cutoff_date},
            }
        )

        # Delete failed deliveries older than extended cutoff
        deleted_failed = db.webhookdelivery.delete_many(
            where={
                "status": {"in": [WebhookDeliveryStatus.FAILED, WebhookDeliveryStatus.RETRYING]},
                "createdAt": {"lt": cutoff_date_failed},
            }
        )

        total_deleted = deleted_success + deleted_failed

        logger.info(
            f"Cleaned up webhook deliveries",
            success_deleted=deleted_success,
            failed_deleted=deleted_failed,
            total=total_deleted,
        )

        return {
            "success_deleted": deleted_success,
            "failed_deleted": deleted_failed,
            "total": total_deleted,
        }

    except Exception as e:
        logger.error(f"Error cleaning up webhook deliveries", error=str(e))
        raise
    finally:
        db.disconnect()


@shared_task(name="disable_failing_webhooks")
def disable_failing_webhooks(failure_threshold: int = 10):
    """
    Disable webhooks that have failed too many times

    Automatically disables webhooks that exceed the failure threshold
    to prevent continued failed delivery attempts.

    Args:
        failure_threshold: Number of consecutive failures before disabling (default 10)
    """
    db = Prisma()
    db.connect()

    try:
        # Find webhooks with high failure counts
        failing_webhooks = db.webhook.find_many(
            where={
                "isActive": True,
                "failureCount": {"gte": failure_threshold},
            }
        )

        disabled_count = 0

        for webhook in failing_webhooks:
            # Disable webhook
            db.webhook.update(
                where={"id": webhook.id},
                data={"isActive": False},
            )

            logger.warning(
                f"Disabled webhook due to repeated failures",
                webhook_id=webhook.id,
                url=webhook.url,
                failure_count=webhook.failureCount,
            )

            # TODO: Send notification to user about disabled webhook
            # send_webhook_disabled_notification(webhook.userId, webhook.id)

            disabled_count += 1

        logger.info(f"Disabled {disabled_count} failing webhooks")

        return {"disabled": disabled_count}

    except Exception as e:
        logger.error(f"Error disabling failing webhooks", error=str(e))
        raise
    finally:
        db.disconnect()


# Celery Beat schedule configuration
# Add this to your celery config:
"""
from celery.schedules import crontab

beat_schedule = {
    'retry-failed-webhooks': {
        'task': 'retry_failed_webhooks',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'cleanup-old-webhook-deliveries': {
        'task': 'cleanup_old_webhook_deliveries',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'disable-failing-webhooks': {
        'task': 'disable_failing_webhooks',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
    },
}
"""
