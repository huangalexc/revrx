"""
Subscription and Payment API Endpoints
Handles trial activation, subscription management, and billing
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from prisma import models
from prisma.enums import SubscriptionStatus
from datetime import datetime, timedelta
from typing import Optional

from app.core.deps import get_current_user, get_db
from app.core.config import settings
from app.services.stripe_service import get_stripe_service, StripeService
from app.schemas.subscription import (
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    TrialActivationRequest,
    TrialActivationResponse,
    SubscriptionResponse,
    SubscriptionStatusResponse,
    CancelSubscriptionRequest,
    CancelSubscriptionResponse,
    BillingHistoryResponse,
    PaymentMethodResponse,
    InvoiceResponse,
    SubscriptionStatusEnum,
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.post("/activate-trial", response_model=TrialActivationResponse)
async def activate_trial(
    request: TrialActivationRequest,
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
    stripe_service: StripeService = Depends(get_stripe_service),
):
    """
    Activate trial period for a user

    This endpoint:
    1. Creates a Stripe customer if not exists
    2. Sets trial end date
    3. Updates subscription status to TRIAL
    """
    # Check if user already has an active trial or subscription
    if current_user.subscriptionStatus in [
        SubscriptionStatus.TRIAL,
        SubscriptionStatus.ACTIVE,
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active trial or subscription",
        )

    # Create Stripe customer if not exists
    stripe_customer_id = current_user.stripeCustomerId
    if not stripe_customer_id:
        try:
            stripe_customer_id = await stripe_service.create_customer(
                email=current_user.email,
                user_id=current_user.id,
            )
        except Exception as e:
            logger.error(f"Failed to create Stripe customer", error=str(e), user_id=current_user.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create payment account",
            )

    # Set trial end date
    trial_end_date = datetime.utcnow() + timedelta(days=request.trial_days)

    # Update user
    updated_user = await db.user.update(
        where={"id": current_user.id},
        data={
            "stripeCustomerId": stripe_customer_id,
            "subscriptionStatus": SubscriptionStatus.TRIAL,
            "trialEndDate": trial_end_date,
        },
    )

    logger.info(
        f"Trial activated",
        user_id=current_user.id,
        trial_days=request.trial_days,
        trial_end_date=trial_end_date,
    )

    return TrialActivationResponse(
        trial_activated=True,
        trial_end_date=trial_end_date,
        subscription_status=SubscriptionStatusEnum.TRIAL,
    )


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CheckoutSessionCreate,
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
    stripe_service: StripeService = Depends(get_stripe_service),
):
    """
    Create a Stripe Checkout session for subscription

    User must have a Stripe customer ID. If on trial, can include trial period.
    """
    # Ensure user has Stripe customer ID
    if not current_user.stripeCustomerId:
        # Create customer if not exists
        try:
            stripe_customer_id = await stripe_service.create_customer(
                email=current_user.email,
                user_id=current_user.id,
            )
            await db.user.update(
                where={"id": current_user.id},
                data={"stripeCustomerId": stripe_customer_id},
            )
        except Exception as e:
            logger.error(f"Failed to create Stripe customer", error=str(e), user_id=current_user.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create payment account",
            )
    else:
        stripe_customer_id = current_user.stripeCustomerId

    # Create checkout session
    try:
        session_data = await stripe_service.create_checkout_session(
            customer_id=stripe_customer_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            trial_period_days=request.trial_period_days,
        )

        logger.info(
            f"Checkout session created",
            user_id=current_user.id,
            session_id=session_data["session_id"],
        )

        return CheckoutSessionResponse(**session_data)
    except Exception as e:
        logger.error(f"Failed to create checkout session", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session",
        )


@router.post("/create-payment-method-session", response_model=CheckoutSessionResponse)
async def create_payment_method_session(
    request: CheckoutSessionCreate,
    current_user: models.User = Depends(get_current_user),
    stripe_service: StripeService = Depends(get_stripe_service),
):
    """
    Create a Stripe Checkout session for adding/updating payment method

    Does not create a subscription, only collects payment method.
    """
    if not current_user.stripeCustomerId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have a Stripe customer ID. Activate trial first.",
        )

    try:
        session_data = await stripe_service.create_payment_method_setup_session(
            customer_id=current_user.stripeCustomerId,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )

        logger.info(
            f"Payment method setup session created",
            user_id=current_user.id,
            session_id=session_data["session_id"],
        )

        return CheckoutSessionResponse(**session_data)
    except Exception as e:
        logger.error(f"Failed to create payment method session", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment method session",
        )


@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
):
    """
    Get current subscription status for the user

    Returns trial status, subscription details, and days remaining.
    """
    try:
        # Check for active subscription
        active_subscription = await db.subscription.find_first(
            where={
                "userId": current_user.id,
                "status": {"in": [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]},
            },
            order={"createdAt": "desc"},
        )

        days_remaining = None
        if current_user.trialEndDate and current_user.subscriptionStatus == SubscriptionStatus.TRIAL:
            # Make datetime timezone-aware for comparison
            from datetime import timezone
            now = datetime.now(timezone.utc) if current_user.trialEndDate.tzinfo else datetime.utcnow()
            days_remaining = (current_user.trialEndDate - now).days

        is_subscribed = current_user.subscriptionStatus in [
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIAL,
        ]

        # Convert Prisma enum to Pydantic enum
        subscription_status_value = current_user.subscriptionStatus.value if hasattr(current_user.subscriptionStatus, 'value') else current_user.subscriptionStatus

        return SubscriptionStatusResponse(
            is_subscribed=is_subscribed,
            subscription_status=SubscriptionStatusEnum(subscription_status_value),
            trial_end_date=current_user.trialEndDate,
            subscription=SubscriptionResponse.from_orm(active_subscription) if active_subscription else None,
            days_remaining=days_remaining,
        )
    except Exception as e:
        logger.error(f"Error getting subscription status", error=str(e), user_id=current_user.id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting subscription status: {str(e)}",
        )


@router.post("/cancel", response_model=CancelSubscriptionResponse)
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
    stripe_service: StripeService = Depends(get_stripe_service),
):
    """
    Cancel the user's subscription

    Can choose to cancel immediately or at the end of the billing period.
    """
    # Find active subscription
    active_subscription = await db.subscription.find_first(
        where={
            "userId": current_user.id,
            "status": SubscriptionStatus.ACTIVE,
        },
        order={"createdAt": "desc"},
    )

    if not active_subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found",
        )

    # Cancel in Stripe
    try:
        stripe_subscription = await stripe_service.cancel_subscription(
            subscription_id=active_subscription.stripeSubscriptionId,
            cancel_at_period_end=request.cancel_at_period_end,
        )
    except Exception as e:
        logger.error(f"Failed to cancel subscription in Stripe", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription",
        )

    # Update database
    updated_subscription = await db.subscription.update(
        where={"id": active_subscription.id},
        data={
            "cancelAtPeriodEnd": request.cancel_at_period_end,
            "canceledAt": datetime.utcnow() if not request.cancel_at_period_end else None,
            "status": SubscriptionStatus.CANCELLED if not request.cancel_at_period_end else SubscriptionStatus.ACTIVE,
        },
    )

    # Update user status if cancelled immediately
    if not request.cancel_at_period_end:
        await db.user.update(
            where={"id": current_user.id},
            data={"subscriptionStatus": SubscriptionStatus.CANCELLED},
        )

    logger.info(
        f"Subscription cancelled",
        user_id=current_user.id,
        subscription_id=active_subscription.id,
        cancel_at_period_end=request.cancel_at_period_end,
    )

    return CancelSubscriptionResponse(
        success=True,
        message="Subscription cancelled successfully",
        subscription=SubscriptionResponse.from_orm(updated_subscription),
    )


@router.post("/reactivate", response_model=SubscriptionResponse)
async def reactivate_subscription(
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
    stripe_service: StripeService = Depends(get_stripe_service),
):
    """
    Reactivate a subscription that was set to cancel at period end
    """
    # Find subscription set to cancel
    subscription = await db.subscription.find_first(
        where={
            "userId": current_user.id,
            "status": SubscriptionStatus.ACTIVE,
            "cancelAtPeriodEnd": True,
        },
        order={"createdAt": "desc"},
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription scheduled for cancellation found",
        )

    # Reactivate in Stripe
    try:
        await stripe_service.reactivate_subscription(
            subscription_id=subscription.stripeSubscriptionId,
        )
    except Exception as e:
        logger.error(f"Failed to reactivate subscription in Stripe", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate subscription",
        )

    # Update database
    updated_subscription = await db.subscription.update(
        where={"id": subscription.id},
        data={
            "cancelAtPeriodEnd": False,
            "canceledAt": None,
        },
    )

    logger.info(
        f"Subscription reactivated",
        user_id=current_user.id,
        subscription_id=subscription.id,
    )

    return SubscriptionResponse.from_orm(updated_subscription)


@router.get("/billing-history", response_model=BillingHistoryResponse)
async def get_billing_history(
    current_user: models.User = Depends(get_current_user),
    stripe_service: StripeService = Depends(get_stripe_service),
):
    """
    Get billing history including invoices and payment methods
    """
    if not current_user.stripeCustomerId:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No billing information found",
        )

    try:
        # Get invoices
        invoices_data = await stripe_service.list_customer_invoices(
            customer_id=current_user.stripeCustomerId,
            limit=20,
        )

        # Get payment methods
        payment_methods_data = await stripe_service.list_customer_payment_methods(
            customer_id=current_user.stripeCustomerId,
        )

        return BillingHistoryResponse(
            invoices=[InvoiceResponse(**inv) for inv in invoices_data],
            payment_methods=[PaymentMethodResponse(**pm) for pm in payment_methods_data],
        )
    except Exception as e:
        logger.error(f"Failed to retrieve billing history", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve billing history",
        )
