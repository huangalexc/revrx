"""
Webhook Delivery Service
Handles webhook delivery with retry logic and signature generation
"""

import httpx
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from prisma.enums import WebhookDeliveryStatus

from app.core.logging import get_logger

logger = get_logger(__name__)


class WebhookService:
    """Service for delivering webhooks"""

    @classmethod
    def generate_signature(cls, payload: str, secret: str) -> str:
        """
        Generate HMAC-SHA256 signature for webhook payload

        Args:
            payload: JSON string payload
            secret: Webhook secret

        Returns:
            Hex-encoded signature
        """
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    @classmethod
    async def deliver_webhook(
        cls,
        db,
        webhook_id: str,
        event: str,
        payload: Dict[str, Any],
        max_retries: int = 3,
    ) -> bool:
        """
        Deliver a webhook with retries

        Args:
            db: Database connection
            webhook_id: Webhook ID
            event: Event type
            payload: Event payload
            max_retries: Maximum retry attempts

        Returns:
            True if delivered successfully, False otherwise
        """
        # Get webhook config
        webhook = await db.webhook.find_unique(where={"id": webhook_id})

        if not webhook or not webhook.isActive:
            logger.warning(f"Webhook not found or inactive", webhook_id=webhook_id)
            return False

        # Check if event is subscribed
        if event not in webhook.events:
            logger.debug(f"Event not subscribed", webhook_id=webhook_id, event=event)
            return False

        # Prepare payload
        payload_str = json.dumps(payload, default=str)

        # Generate signature
        signature = cls.generate_signature(payload_str, webhook.secret)

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event,
            "X-Webhook-Signature": signature,
            "X-Webhook-ID": webhook_id,
            "X-Webhook-Timestamp": str(int(datetime.utcnow().timestamp())),
            "User-Agent": "RevRx-Webhook/1.0",
        }

        # Create delivery record
        delivery = await db.webhookdelivery.create(
            data={
                "webhookId": webhook_id,
                "event": event,
                "payload": payload,
                "requestUrl": webhook.url,
                "requestMethod": "POST",
                "requestHeaders": headers,
                "status": WebhookDeliveryStatus.PENDING,
                "attemptNumber": 1,
                "maxAttempts": max_retries,
            }
        )

        # Attempt delivery
        success = await cls._attempt_delivery(
            db=db,
            delivery_id=delivery.id,
            url=webhook.url,
            headers=headers,
            payload_str=payload_str,
        )

        # Update webhook stats
        if success:
            await db.webhook.update(
                where={"id": webhook_id},
                data={
                    "lastSuccessAt": datetime.utcnow(),
                    "failureCount": 0,
                },
            )
        else:
            # Schedule retry if not max attempts
            if delivery.attemptNumber < max_retries:
                next_retry_at = datetime.utcnow() + timedelta(minutes=5 * delivery.attemptNumber)
                await db.webhookdelivery.update(
                    where={"id": delivery.id},
                    data={
                        "status": WebhookDeliveryStatus.RETRYING,
                        "nextRetryAt": next_retry_at,
                    },
                )
            else:
                await db.webhook.update(
                    where={"id": webhook_id},
                    data={
                        "lastFailureAt": datetime.utcnow(),
                        "failureCount": {"increment": 1},
                    },
                )

        return success

    @classmethod
    async def _attempt_delivery(
        cls,
        db,
        delivery_id: str,
        url: str,
        headers: Dict[str, str],
        payload_str: str,
    ) -> bool:
        """
        Attempt to deliver a webhook

        Args:
            db: Database connection
            delivery_id: Delivery record ID
            url: Webhook URL
            headers: Request headers
            payload_str: JSON payload string

        Returns:
            True if successful, False otherwise
        """
        start_time = datetime.utcnow()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    content=payload_str,
                )

                response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                # Check if successful (2xx status code)
                success = 200 <= response.status_code < 300

                # Update delivery record
                await db.webhookdelivery.update(
                    where={"id": delivery_id},
                    data={
                        "responseStatus": response.status_code,
                        "responseBody": response.text[:1000],  # Limit to 1000 chars
                        "responseTime": response_time,
                        "status": WebhookDeliveryStatus.DELIVERED if success else WebhookDeliveryStatus.FAILED,
                        "deliveredAt": datetime.utcnow() if success else None,
                        "error": None if success else f"HTTP {response.status_code}",
                    },
                )

                if success:
                    logger.info(
                        f"Webhook delivered successfully",
                        delivery_id=delivery_id,
                        status=response.status_code,
                        response_time=response_time,
                    )
                else:
                    logger.warning(
                        f"Webhook delivery failed",
                        delivery_id=delivery_id,
                        status=response.status_code,
                        response=response.text[:200],
                    )

                return success

        except httpx.TimeoutException as e:
            logger.error(f"Webhook delivery timeout", delivery_id=delivery_id, error=str(e))

            await db.webhookdelivery.update(
                where={"id": delivery_id},
                data={
                    "status": WebhookDeliveryStatus.FAILED,
                    "error": "Request timeout",
                },
            )

            return False

        except Exception as e:
            logger.error(f"Webhook delivery error", delivery_id=delivery_id, error=str(e))

            await db.webhookdelivery.update(
                where={"id": delivery_id},
                data={
                    "status": WebhookDeliveryStatus.FAILED,
                    "error": str(e)[:500],
                },
            )

            return False

    @classmethod
    async def retry_failed_deliveries(cls, db):
        """
        Retry webhook deliveries that are pending retry

        Should be called periodically (e.g., every 5 minutes via Celery)
        """
        now = datetime.utcnow()

        # Find deliveries to retry
        deliveries = await db.webhookdelivery.find_many(
            where={
                "status": WebhookDeliveryStatus.RETRYING,
                "nextRetryAt": {"lte": now},
            },
            include={"webhook": True},
        )

        logger.info(f"Retrying {len(deliveries)} webhook deliveries")

        for delivery in deliveries:
            if delivery.attemptNumber >= delivery.maxAttempts:
                # Max attempts reached
                await db.webhookdelivery.update(
                    where={"id": delivery.id},
                    data={"status": WebhookDeliveryStatus.FAILED},
                )
                continue

            # Increment attempt number
            await db.webhookdelivery.update(
                where={"id": delivery.id},
                data={"attemptNumber": {"increment": 1}},
            )

            # Regenerate signature with current timestamp
            payload_str = json.dumps(delivery.payload, default=str)
            signature = cls.generate_signature(payload_str, delivery.webhook.secret)

            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Event": delivery.event,
                "X-Webhook-Signature": signature,
                "X-Webhook-ID": delivery.webhookId,
                "X-Webhook-Timestamp": str(int(datetime.utcnow().timestamp())),
                "X-Webhook-Retry": str(delivery.attemptNumber),
                "User-Agent": "RevRx-Webhook/1.0",
            }

            # Attempt delivery
            success = await cls._attempt_delivery(
                db=db,
                delivery_id=delivery.id,
                url=delivery.webhook.url,
                headers=headers,
                payload_str=payload_str,
            )

            if success:
                await db.webhook.update(
                    where={"id": delivery.webhookId},
                    data={
                        "lastSuccessAt": datetime.utcnow(),
                        "failureCount": 0,
                    },
                )
            elif delivery.attemptNumber + 1 >= delivery.maxAttempts:
                # Final attempt failed
                await db.webhook.update(
                    where={"id": delivery.webhookId},
                    data={
                        "lastFailureAt": datetime.utcnow(),
                        "failureCount": {"increment": 1},
                        "lastError": "Max retry attempts reached",
                    },
                )
            else:
                # Schedule next retry (exponential backoff)
                next_retry_at = now + timedelta(minutes=5 * (delivery.attemptNumber + 1))
                await db.webhookdelivery.update(
                    where={"id": delivery.id},
                    data={"nextRetryAt": next_retry_at},
                )

        return len(deliveries)


async def trigger_webhook_event(db, user_id: str, event: str, payload: Dict[str, Any]):
    """
    Trigger webhook event for all matching webhooks

    Args:
        db: Database connection
        user_id: User ID who owns the webhooks
        event: Event type
        payload: Event payload
    """
    # Find all active webhooks for this user that subscribe to this event
    webhooks = await db.webhook.find_many(
        where={
            "userId": user_id,
            "isActive": True,
            "events": {"has": event},
        }
    )

    logger.info(
        f"Triggering webhook event",
        event=event,
        user_id=user_id,
        webhook_count=len(webhooks),
    )

    # Deliver to each webhook
    for webhook in webhooks:
        try:
            await WebhookService.deliver_webhook(
                db=db,
                webhook_id=webhook.id,
                event=event,
                payload=payload,
            )
        except Exception as e:
            logger.error(
                f"Failed to deliver webhook",
                webhook_id=webhook.id,
                event=event,
                error=str(e),
            )
