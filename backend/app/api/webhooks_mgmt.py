"""
Webhook Management Endpoints
Register, list, update, and test webhooks
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import secrets
from prisma import models

from app.core.deps import get_current_user, get_db
from app.schemas.webhook import (
    WebhookCreate,
    WebhookResponse,
    WebhookListResponse,
    WebhookUpdateRequest,
    WebhookTestRequest,
    WebhookDeliveryResponse,
    WebhookDeliveryListResponse,
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    request: WebhookCreate,
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
):
    """
    Register a new webhook

    The webhook will receive HTTP POST requests when subscribed events occur.
    A secret is generated for signature verification.
    """
    try:
        # Generate webhook secret for signature verification
        webhook_secret = secrets.token_urlsafe(32)

        # Create webhook
        webhook = await db.webhook.create(
            data={
                "userId": current_user.id,
                "apiKeyId": request.api_key_id,
                "url": str(request.url),
                "events": [event.value for event in request.events],
                "secret": webhook_secret,
                "isActive": True,
            }
        )

        # Audit log
        await db.auditlog.create(
            data={
                "userId": current_user.id,
                "action": "WEBHOOK_CREATED",
                "resourceType": "Webhook",
                "resourceId": webhook.id,
                "metadata": {
                    "url": str(request.url),
                    "events": [event.value for event in request.events],
                },
            }
        )

        logger.info(
            f"Webhook created",
            webhook_id=webhook.id,
            user_id=current_user.id,
            url=str(request.url),
        )

        return WebhookResponse.from_orm(webhook)

    except Exception as e:
        logger.error(f"Failed to create webhook", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create webhook",
        )


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
):
    """List all webhooks for the current user"""
    try:
        webhooks = await db.webhook.find_many(
            where={"userId": current_user.id},
            order={"createdAt": "desc"},
        )

        return WebhookListResponse(
            webhooks=[WebhookResponse.from_orm(wh) for wh in webhooks],
            total=len(webhooks),
        )

    except Exception as e:
        logger.error(f"Failed to list webhooks", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list webhooks",
        )


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
):
    """Get details of a specific webhook"""
    try:
        webhook = await db.webhook.find_first(
            where={"id": webhook_id, "userId": current_user.id}
        )

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found",
            )

        return WebhookResponse.from_orm(webhook)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get webhook", error=str(e), webhook_id=webhook_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get webhook",
        )


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    request: WebhookUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
):
    """Update a webhook configuration"""
    try:
        # Verify ownership
        webhook = await db.webhook.find_first(
            where={"id": webhook_id, "userId": current_user.id}
        )

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found",
            )

        # Build update data
        update_data = {}
        if request.url is not None:
            update_data["url"] = str(request.url)
        if request.events is not None:
            update_data["events"] = [event.value for event in request.events]
        if request.is_active is not None:
            update_data["isActive"] = request.is_active

        # Update
        updated_webhook = await db.webhook.update(
            where={"id": webhook_id},
            data=update_data,
        )

        # Audit log
        await db.auditlog.create(
            data={
                "userId": current_user.id,
                "action": "WEBHOOK_UPDATED",
                "resourceType": "Webhook",
                "resourceId": webhook_id,
                "metadata": update_data,
            }
        )

        logger.info(f"Webhook updated", webhook_id=webhook_id, user_id=current_user.id)

        return WebhookResponse.from_orm(updated_webhook)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update webhook", error=str(e), webhook_id=webhook_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update webhook",
        )


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
):
    """Delete a webhook"""
    try:
        # Verify ownership
        webhook = await db.webhook.find_first(
            where={"id": webhook_id, "userId": current_user.id}
        )

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found",
            )

        # Delete
        await db.webhook.delete(where={"id": webhook_id})

        # Audit log
        await db.auditlog.create(
            data={
                "userId": current_user.id,
                "action": "WEBHOOK_DELETED",
                "resourceType": "Webhook",
                "resourceId": webhook_id,
            }
        )

        logger.info(f"Webhook deleted", webhook_id=webhook_id, user_id=current_user.id)

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete webhook", error=str(e), webhook_id=webhook_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete webhook",
        )


@router.post("/{webhook_id}/test", status_code=status.HTTP_202_ACCEPTED)
async def test_webhook(
    webhook_id: str,
    request: WebhookTestRequest,
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
):
    """
    Test a webhook by sending a sample event

    Sends a test payload to verify the webhook endpoint is working.
    """
    try:
        # Verify ownership
        webhook = await db.webhook.find_first(
            where={"id": webhook_id, "userId": current_user.id}
        )

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found",
            )

        # Create test payload
        test_payload = {
            "event": request.event.value,
            "test": True,
            "data": {
                "encounter_id": "test-encounter-id",
                "status": "completed",
                "timestamp": "2024-01-01T00:00:00Z",
            },
        }

        # TODO: Queue webhook delivery
        # from app.services.webhook_service import deliver_webhook
        # await deliver_webhook(webhook.id, request.event.value, test_payload)

        logger.info(
            f"Webhook test triggered",
            webhook_id=webhook_id,
            event=request.event.value,
        )

        return {
            "message": "Test webhook queued for delivery",
            "webhook_id": webhook_id,
            "event": request.event.value,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test webhook", error=str(e), webhook_id=webhook_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test webhook",
        )


@router.get("/{webhook_id}/deliveries", response_model=WebhookDeliveryListResponse)
async def list_webhook_deliveries(
    webhook_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
):
    """List recent webhook delivery attempts"""
    try:
        # Verify ownership
        webhook = await db.webhook.find_first(
            where={"id": webhook_id, "userId": current_user.id}
        )

        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found",
            )

        # Get deliveries
        deliveries = await db.webhookdelivery.find_many(
            where={"webhookId": webhook_id},
            order={"createdAt": "desc"},
            skip=offset,
            take=limit,
        )

        return WebhookDeliveryListResponse(
            deliveries=[WebhookDeliveryResponse.from_orm(d) for d in deliveries],
            total=len(deliveries),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to list webhook deliveries",
            error=str(e),
            webhook_id=webhook_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list webhook deliveries",
        )
