"""
Stripe Webhook Handlers
Processes Stripe events for subscription lifecycle management
"""

from fastapi import APIRouter, Request, HTTPException, status, Depends
from prisma.enums import SubscriptionStatus
from datetime import datetime
from typing import Dict, Any

from app.core.deps import get_db
from app.core.config import settings
from app.services.stripe_service import get_stripe_service, StripeService
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db = Depends(get_db),
    stripe_service: StripeService = Depends(get_stripe_service),
):
    """
    Handle Stripe webhook events

    Processes subscription lifecycle events:
    - subscription.created
    - subscription.updated
    - subscription.deleted
    - customer.subscription.trial_will_end
    - payment_intent.succeeded
    - payment_intent.payment_failed
    - invoice.payment_succeeded
    - invoice.payment_failed
    """
    # Get raw body for signature verification
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature header",
        )

    # Verify and construct event
    event = await stripe_service.construct_webhook_event(payload, sig_header)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )

    logger.info(f"Webhook event received", event_type=event.type, event_id=event.id)

    # Handle different event types
    try:
        if event.type == "customer.subscription.created":
            await handle_subscription_created(event.data.object, db)
        elif event.type == "customer.subscription.updated":
            await handle_subscription_updated(event.data.object, db)
        elif event.type == "customer.subscription.deleted":
            await handle_subscription_deleted(event.data.object, db)
        elif event.type == "customer.subscription.trial_will_end":
            await handle_trial_will_end(event.data.object, db)
        elif event.type == "payment_intent.succeeded":
            await handle_payment_succeeded(event.data.object, db)
        elif event.type == "payment_intent.payment_failed":
            await handle_payment_failed(event.data.object, db)
        elif event.type == "invoice.payment_succeeded":
            await handle_invoice_payment_succeeded(event.data.object, db)
        elif event.type == "invoice.payment_failed":
            await handle_invoice_payment_failed(event.data.object, db)
        else:
            logger.info(f"Unhandled webhook event type", event_type=event.type)

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error processing webhook", error=str(e), event_type=event.type, event_id=event.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing webhook",
        )


async def handle_subscription_created(subscription: Dict[str, Any], db):
    """Handle subscription.created event"""
    stripe_customer_id = subscription["customer"]
    stripe_subscription_id = subscription["id"]

    # Find user by Stripe customer ID
    user = await db.user.find_first(
        where={"stripeCustomerId": stripe_customer_id}
    )

    if not user:
        logger.error(f"User not found for Stripe customer", customer_id=stripe_customer_id)
        return

    # Get subscription details
    price_data = subscription["items"]["data"][0]["price"]
    amount = price_data["unit_amount"] / 100  # Convert from cents
    currency = price_data["currency"]
    interval = price_data["recurring"]["interval"]

    # Create subscription record
    db_subscription = await db.subscription.create(
        data={
            "userId": user.id,
            "stripeSubscriptionId": stripe_subscription_id,
            "stripeCustomerId": stripe_customer_id,
            "stripePriceId": price_data["id"],
            "status": SubscriptionStatus.ACTIVE,
            "currentPeriodStart": datetime.fromtimestamp(subscription["current_period_start"]),
            "currentPeriodEnd": datetime.fromtimestamp(subscription["current_period_end"]),
            "cancelAtPeriodEnd": subscription.get("cancel_at_period_end", False),
            "amount": amount,
            "currency": currency,
            "billingInterval": interval,
        }
    )

    # Update user subscription status
    await db.user.update(
        where={"id": user.id},
        data={"subscriptionStatus": SubscriptionStatus.ACTIVE},
    )

    logger.info(
        f"Subscription created",
        user_id=user.id,
        subscription_id=db_subscription.id,
        stripe_subscription_id=stripe_subscription_id,
    )


async def handle_subscription_updated(subscription: Dict[str, Any], db):
    """Handle subscription.updated event"""
    stripe_subscription_id = subscription["id"]

    # Find subscription in database
    db_subscription = await db.subscription.find_first(
        where={"stripeSubscriptionId": stripe_subscription_id}
    )

    if not db_subscription:
        logger.error(f"Subscription not found", stripe_subscription_id=stripe_subscription_id)
        return

    # Map Stripe status to our enum
    stripe_status = subscription["status"]
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

    # Update subscription
    updated_subscription = await db.subscription.update(
        where={"id": db_subscription.id},
        data={
            "status": new_status,
            "currentPeriodStart": datetime.fromtimestamp(subscription["current_period_start"]),
            "currentPeriodEnd": datetime.fromtimestamp(subscription["current_period_end"]),
            "cancelAtPeriodEnd": subscription.get("cancel_at_period_end", False),
            "canceledAt": datetime.fromtimestamp(subscription["canceled_at"]) if subscription.get("canceled_at") else None,
        }
    )

    # Update user subscription status
    await db.user.update(
        where={"id": db_subscription.userId},
        data={"subscriptionStatus": new_status},
    )

    logger.info(
        f"Subscription updated",
        subscription_id=db_subscription.id,
        new_status=new_status,
        stripe_subscription_id=stripe_subscription_id,
    )


async def handle_subscription_deleted(subscription: Dict[str, Any], db):
    """Handle subscription.deleted event"""
    stripe_subscription_id = subscription["id"]

    # Find subscription in database
    db_subscription = await db.subscription.find_first(
        where={"stripeSubscriptionId": stripe_subscription_id}
    )

    if not db_subscription:
        logger.error(f"Subscription not found", stripe_subscription_id=stripe_subscription_id)
        return

    # Update subscription to cancelled
    await db.subscription.update(
        where={"id": db_subscription.id},
        data={
            "status": SubscriptionStatus.CANCELLED,
            "canceledAt": datetime.utcnow(),
        }
    )

    # Update user subscription status
    await db.user.update(
        where={"id": db_subscription.userId},
        data={"subscriptionStatus": SubscriptionStatus.CANCELLED},
    )

    logger.info(
        f"Subscription deleted",
        subscription_id=db_subscription.id,
        stripe_subscription_id=stripe_subscription_id,
    )


async def handle_trial_will_end(subscription: Dict[str, Any], db):
    """
    Handle customer.subscription.trial_will_end event
    Send reminder email to user about trial ending
    """
    stripe_customer_id = subscription["customer"]

    # Find user
    user = await db.user.find_first(
        where={"stripeCustomerId": stripe_customer_id}
    )

    if not user:
        logger.error(f"User not found for Stripe customer", customer_id=stripe_customer_id)
        return

    # Calculate days until trial ends
    trial_end = datetime.fromtimestamp(subscription["trial_end"])
    days_remaining = (trial_end - datetime.utcnow()).days

    logger.info(
        f"Trial will end soon",
        user_id=user.id,
        days_remaining=days_remaining,
        trial_end=trial_end,
    )

    # TODO: Send email notification
    # This will be implemented in the email service


async def handle_payment_succeeded(payment_intent: Dict[str, Any], db):
    """Handle payment_intent.succeeded event"""
    logger.info(
        f"Payment succeeded",
        payment_intent_id=payment_intent["id"],
        amount=payment_intent["amount"] / 100,
    )

    # TODO: Create audit log entry for payment
    # TODO: Send payment confirmation email


async def handle_payment_failed(payment_intent: Dict[str, Any], db):
    """Handle payment_intent.payment_failed event"""
    logger.error(
        f"Payment failed",
        payment_intent_id=payment_intent["id"],
        amount=payment_intent["amount"] / 100,
        error=payment_intent.get("last_payment_error"),
    )

    # TODO: Send payment failure notification
    # TODO: Update user status if needed


async def handle_invoice_payment_succeeded(invoice: Dict[str, Any], db):
    """Handle invoice.payment_succeeded event"""
    logger.info(
        f"Invoice payment succeeded",
        invoice_id=invoice["id"],
        amount=invoice["amount_paid"] / 100,
    )

    # TODO: Send invoice receipt email


async def handle_invoice_payment_failed(invoice: Dict[str, Any], db):
    """Handle invoice.payment_failed event"""
    logger.error(
        f"Invoice payment failed",
        invoice_id=invoice["id"],
        amount=invoice["amount_due"] / 100,
    )

    # TODO: Send payment failure notification
    # TODO: Potentially suspend subscription after X failures
