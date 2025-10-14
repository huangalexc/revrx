"""
Subscription Background Tasks
Celery tasks for trial conversion and expiration reminders
"""

from celery import shared_task
from datetime import datetime, timedelta
from prisma import Prisma
from prisma.enums import SubscriptionStatus

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


@shared_task(name="check_trial_expirations")
def check_trial_expirations():
    """
    Check for expired trials and update user subscription status

    Runs periodically (e.g., every hour) to:
    1. Find users with expired trials
    2. Update their subscription status to EXPIRED
    3. Optionally send expiration notification
    """
    db = Prisma()
    db.connect()

    try:
        # Find users with expired trials
        now = datetime.utcnow()
        expired_users = db.user.find_many(
            where={
                "subscriptionStatus": SubscriptionStatus.TRIAL,
                "trialEndDate": {"lt": now},
            }
        )

        count = len(expired_users)
        logger.info(f"Found {count} expired trials to process")

        for user in expired_users:
            try:
                # Update user status to EXPIRED
                db.user.update(
                    where={"id": user.id},
                    data={"subscriptionStatus": SubscriptionStatus.EXPIRED},
                )

                logger.info(
                    f"Expired trial for user",
                    user_id=user.id,
                    trial_end_date=user.trialEndDate,
                )

                # TODO: Send trial expiration email
                # send_trial_expired_email(user.email, user.id)

            except Exception as e:
                logger.error(
                    f"Failed to expire trial for user",
                    user_id=user.id,
                    error=str(e),
                )

        logger.info(f"Processed {count} expired trials")
        return {"processed": count}

    except Exception as e:
        logger.error(f"Error checking trial expirations", error=str(e))
        raise
    finally:
        db.disconnect()


@shared_task(name="send_trial_expiration_reminders")
def send_trial_expiration_reminders():
    """
    Send reminders to users with upcoming trial expirations

    Sends emails at:
    - 3 days before expiration
    - 1 day before expiration
    """
    db = Prisma()
    db.connect()

    try:
        now = datetime.utcnow()
        three_days_from_now = now + timedelta(days=3)
        one_day_from_now = now + timedelta(days=1)

        # Find users expiring in 3 days
        three_day_users = db.user.find_many(
            where={
                "subscriptionStatus": SubscriptionStatus.TRIAL,
                "trialEndDate": {
                    "gte": three_days_from_now - timedelta(hours=1),
                    "lte": three_days_from_now + timedelta(hours=1),
                },
            }
        )

        # Find users expiring in 1 day
        one_day_users = db.user.find_many(
            where={
                "subscriptionStatus": SubscriptionStatus.TRIAL,
                "trialEndDate": {
                    "gte": one_day_from_now - timedelta(hours=1),
                    "lte": one_day_from_now + timedelta(hours=1),
                },
            }
        )

        # Send 3-day reminders
        for user in three_day_users:
            try:
                logger.info(
                    f"Sending 3-day trial expiration reminder",
                    user_id=user.id,
                    email=user.email,
                    trial_end_date=user.trialEndDate,
                )

                # TODO: Send email
                # send_trial_reminder_email(user.email, user.id, days=3)

            except Exception as e:
                logger.error(
                    f"Failed to send 3-day reminder",
                    user_id=user.id,
                    error=str(e),
                )

        # Send 1-day reminders
        for user in one_day_users:
            try:
                logger.info(
                    f"Sending 1-day trial expiration reminder",
                    user_id=user.id,
                    email=user.email,
                    trial_end_date=user.trialEndDate,
                )

                # TODO: Send email
                # send_trial_reminder_email(user.email, user.id, days=1)

            except Exception as e:
                logger.error(
                    f"Failed to send 1-day reminder",
                    user_id=user.id,
                    error=str(e),
                )

        logger.info(
            f"Sent trial expiration reminders",
            three_day_count=len(three_day_users),
            one_day_count=len(one_day_users),
        )

        return {
            "three_day_reminders": len(three_day_users),
            "one_day_reminders": len(one_day_users),
        }

    except Exception as e:
        logger.error(f"Error sending trial expiration reminders", error=str(e))
        raise
    finally:
        db.disconnect()


@shared_task(name="sync_subscription_status_with_stripe")
def sync_subscription_status_with_stripe():
    """
    Sync subscription status with Stripe for users with active subscriptions

    Runs periodically to ensure database is in sync with Stripe.
    Checks for:
    - Payment failures
    - Manual cancellations in Stripe
    - Status changes
    """
    db = Prisma()
    db.connect()

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Find users with active or trial subscriptions in our database
        subscriptions = db.subscription.find_many(
            where={
                "status": {
                    "in": [
                        SubscriptionStatus.ACTIVE,
                        SubscriptionStatus.TRIAL,
                    ]
                }
            }
        )

        synced_count = 0
        updated_count = 0

        for sub in subscriptions:
            try:
                # Get subscription from Stripe
                stripe_sub = stripe.Subscription.retrieve(sub.stripeSubscriptionId)

                # Check if status has changed
                stripe_status = stripe_sub.status
                status_mapping = {
                    "active": SubscriptionStatus.ACTIVE,
                    "canceled": SubscriptionStatus.CANCELLED,
                    "incomplete": SubscriptionStatus.INACTIVE,
                    "incomplete_expired": SubscriptionStatus.EXPIRED,
                    "past_due": SubscriptionStatus.SUSPENDED,
                    "trialing": SubscriptionStatus.TRIAL,
                    "unpaid": SubscriptionStatus.SUSPENDED,
                }
                new_status = status_mapping.get(stripe_status, SubscriptionStatus.INACTIVE)

                if new_status != sub.status:
                    # Update subscription status
                    db.subscription.update(
                        where={"id": sub.id},
                        data={"status": new_status},
                    )

                    # Update user status
                    db.user.update(
                        where={"id": sub.userId},
                        data={"subscriptionStatus": new_status},
                    )

                    logger.info(
                        f"Synced subscription status with Stripe",
                        subscription_id=sub.id,
                        old_status=sub.status,
                        new_status=new_status,
                    )

                    updated_count += 1

                synced_count += 1

            except stripe.error.StripeError as e:
                logger.error(
                    f"Failed to sync subscription with Stripe",
                    subscription_id=sub.id,
                    error=str(e),
                )
            except Exception as e:
                logger.error(
                    f"Error syncing subscription",
                    subscription_id=sub.id,
                    error=str(e),
                )

        logger.info(
            f"Subscription sync complete",
            synced=synced_count,
            updated=updated_count,
        )

        return {"synced": synced_count, "updated": updated_count}

    except Exception as e:
        logger.error(f"Error syncing subscriptions with Stripe", error=str(e))
        raise
    finally:
        db.disconnect()


# Celery Beat schedule configuration
# Add this to your celery config:
"""
from celery.schedules import crontab

beat_schedule = {
    'check-trial-expirations': {
        'task': 'check_trial_expirations',
        'schedule': crontab(minute=0),  # Every hour
    },
    'send-trial-reminders': {
        'task': 'send_trial_expiration_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    'sync-stripe-subscriptions': {
        'task': 'sync_subscription_status_with_stripe',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
    },
}
"""
