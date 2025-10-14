"""
Stripe Payment Service
Handles all Stripe API interactions for subscription management
"""

import stripe
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from prisma import models
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class StripeService:
    """Service for managing Stripe payments and subscriptions"""

    def __init__(self, settings: Settings):
        self.settings = settings
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.price_id_monthly = settings.STRIPE_PRICE_ID_MONTHLY

    async def create_customer(
        self, email: str, user_id: str, name: Optional[str] = None
    ) -> str:
        """
        Create a Stripe customer

        Args:
            email: Customer email
            user_id: Internal user ID
            name: Customer name (optional)

        Returns:
            Stripe customer ID
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                metadata={"user_id": user_id},
                name=name,
            )
            logger.info(f"Created Stripe customer", customer_id=customer.id, user_id=user_id)
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer", error=str(e), user_id=user_id)
            raise

    async def create_checkout_session(
        self,
        customer_id: str,
        success_url: str,
        cancel_url: str,
        trial_period_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session for subscription

        Args:
            customer_id: Stripe customer ID
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if checkout is cancelled
            trial_period_days: Number of days for trial period (optional)

        Returns:
            Checkout session data including session ID and URL
        """
        try:
            session_params = {
                "customer": customer_id,
                "payment_method_types": ["card"],
                "mode": "subscription",
                "line_items": [
                    {
                        "price": self.price_id_monthly,
                        "quantity": 1,
                    }
                ],
                "success_url": success_url,
                "cancel_url": cancel_url,
                "allow_promotion_codes": True,
            }

            if trial_period_days:
                session_params["subscription_data"] = {
                    "trial_period_days": trial_period_days
                }

            session = stripe.checkout.Session.create(**session_params)

            logger.info(
                f"Created checkout session",
                session_id=session.id,
                customer_id=customer_id,
            )

            return {
                "session_id": session.id,
                "url": session.url,
            }
        except stripe.error.StripeError as e:
            logger.error(
                f"Failed to create checkout session",
                error=str(e),
                customer_id=customer_id,
            )
            raise

    async def create_payment_method_setup_session(
        self,
        customer_id: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session for payment method setup only

        Args:
            customer_id: Stripe customer ID
            success_url: URL to redirect after successful setup
            cancel_url: URL to redirect if setup is cancelled

        Returns:
            Setup session data including session ID and URL
        """
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                mode="setup",
                success_url=success_url,
                cancel_url=cancel_url,
            )

            logger.info(
                f"Created setup session",
                session_id=session.id,
                customer_id=customer_id,
            )

            return {
                "session_id": session.id,
                "url": session.url,
            }
        except stripe.error.StripeError as e:
            logger.error(
                f"Failed to create setup session",
                error=str(e),
                customer_id=customer_id,
            )
            raise

    async def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a subscription from Stripe

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Subscription data or None if not found
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return self._format_subscription(subscription)
        except stripe.error.StripeError as e:
            logger.error(
                f"Failed to retrieve subscription",
                error=str(e),
                subscription_id=subscription_id,
            )
            return None

    async def cancel_subscription(
        self, subscription_id: str, cancel_at_period_end: bool = True
    ) -> Dict[str, Any]:
        """
        Cancel a Stripe subscription

        Args:
            subscription_id: Stripe subscription ID
            cancel_at_period_end: If True, cancel at end of period; if False, cancel immediately

        Returns:
            Updated subscription data
        """
        try:
            if cancel_at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)

            logger.info(
                f"Cancelled subscription",
                subscription_id=subscription_id,
                immediate=not cancel_at_period_end,
            )

            return self._format_subscription(subscription)
        except stripe.error.StripeError as e:
            logger.error(
                f"Failed to cancel subscription",
                error=str(e),
                subscription_id=subscription_id,
            )
            raise

    async def reactivate_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Reactivate a subscription that was set to cancel at period end

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Updated subscription data
        """
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=False,
            )

            logger.info(
                f"Reactivated subscription",
                subscription_id=subscription_id,
            )

            return self._format_subscription(subscription)
        except stripe.error.StripeError as e:
            logger.error(
                f"Failed to reactivate subscription",
                error=str(e),
                subscription_id=subscription_id,
            )
            raise

    async def list_customer_payment_methods(
        self, customer_id: str
    ) -> List[Dict[str, Any]]:
        """
        List all payment methods for a customer

        Args:
            customer_id: Stripe customer ID

        Returns:
            List of payment method data
        """
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card",
            )

            return [
                {
                    "id": pm.id,
                    "type": pm.type,
                    "card": {
                        "brand": pm.card.brand,
                        "last4": pm.card.last4,
                        "exp_month": pm.card.exp_month,
                        "exp_year": pm.card.exp_year,
                    },
                }
                for pm in payment_methods.data
            ]
        except stripe.error.StripeError as e:
            logger.error(
                f"Failed to list payment methods",
                error=str(e),
                customer_id=customer_id,
            )
            return []

    async def list_customer_invoices(
        self, customer_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List invoices for a customer

        Args:
            customer_id: Stripe customer ID
            limit: Maximum number of invoices to return

        Returns:
            List of invoice data
        """
        try:
            invoices = stripe.Invoice.list(
                customer=customer_id,
                limit=limit,
            )

            return [
                {
                    "id": inv.id,
                    "number": inv.number,
                    "status": inv.status,
                    "amount_due": inv.amount_due / 100,  # Convert from cents
                    "amount_paid": inv.amount_paid / 100,
                    "currency": inv.currency,
                    "invoice_pdf": inv.invoice_pdf,
                    "hosted_invoice_url": inv.hosted_invoice_url,
                    "created": datetime.fromtimestamp(inv.created),
                    "due_date": datetime.fromtimestamp(inv.due_date) if inv.due_date else None,
                }
                for inv in invoices.data
            ]
        except stripe.error.StripeError as e:
            logger.error(
                f"Failed to list invoices",
                error=str(e),
                customer_id=customer_id,
            )
            return []

    async def construct_webhook_event(
        self, payload: bytes, sig_header: str
    ) -> Optional[stripe.Event]:
        """
        Construct and verify a Stripe webhook event

        Args:
            payload: Raw request body
            sig_header: Stripe signature header

        Returns:
            Verified Stripe event or None if verification fails
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.settings.STRIPE_WEBHOOK_SECRET
            )
            logger.info(f"Webhook event verified", event_type=event.type, event_id=event.id)
            return event
        except ValueError as e:
            logger.error(f"Invalid webhook payload", error=str(e))
            return None
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature", error=str(e))
            return None

    def _format_subscription(self, subscription: stripe.Subscription) -> Dict[str, Any]:
        """Format Stripe subscription object to dict"""
        return {
            "id": subscription.id,
            "customer": subscription.customer,
            "status": subscription.status,
            "current_period_start": datetime.fromtimestamp(subscription.current_period_start),
            "current_period_end": datetime.fromtimestamp(subscription.current_period_end),
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "canceled_at": datetime.fromtimestamp(subscription.canceled_at) if subscription.canceled_at else None,
            "trial_start": datetime.fromtimestamp(subscription.trial_start) if subscription.trial_start else None,
            "trial_end": datetime.fromtimestamp(subscription.trial_end) if subscription.trial_end else None,
        }


# Dependency injection
def get_stripe_service(settings: Settings = None) -> StripeService:
    """Get StripeService instance"""
    if settings is None:
        from app.core.config import settings as default_settings
        settings = default_settings
    return StripeService(settings)
