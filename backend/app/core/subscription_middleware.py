"""
Subscription Status Middleware
Blocks API access for users without active subscriptions
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from prisma.enums import SubscriptionStatus
from datetime import datetime
from typing import List

from app.core.logging import get_logger

logger = get_logger(__name__)


class SubscriptionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to check subscription status before allowing API access

    Blocks requests from users with expired/cancelled/suspended subscriptions.
    Allows access to:
    - Public endpoints (auth, health checks)
    - Subscription management endpoints
    - Admin users
    """

    # Paths that don't require active subscription
    EXEMPT_PATHS = [
        "/health",
        "/api/v1/health",
        "/api/auth/",
        "/api/subscriptions/",
        "/api/webhooks/",
        "/docs",
        "/openapi.json",
        "/redoc",
    ]

    # Status codes that allow API access
    ALLOWED_STATUSES = [
        SubscriptionStatus.TRIAL,
        SubscriptionStatus.ACTIVE,
    ]

    async def dispatch(self, request: Request, call_next):
        """Check subscription status before processing request"""

        # Check if path is exempt
        path = request.url.path
        if any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            return await call_next(request)

        # Get user from request state (set by auth middleware)
        user = getattr(request.state, "user", None)

        if not user:
            # No user in request state, let the request continue
            # (auth middleware will handle authentication)
            return await call_next(request)

        # Check if user is admin (admins always have access)
        if user.role == "ADMIN":
            return await call_next(request)

        # Check subscription status
        subscription_status = user.subscriptionStatus

        # Allow access if status is TRIAL or ACTIVE
        if subscription_status in self.ALLOWED_STATUSES:
            # If on trial, check if trial has expired
            if subscription_status == SubscriptionStatus.TRIAL:
                if user.trialEndDate and user.trialEndDate < datetime.utcnow():
                    logger.warning(
                        f"Trial expired for user",
                        user_id=user.id,
                        trial_end_date=user.trialEndDate,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail="Trial period has expired. Please subscribe to continue using the service.",
                    )

            return await call_next(request)

        # Block access for users without active subscription
        logger.warning(
            f"API access blocked - no active subscription",
            user_id=user.id,
            subscription_status=subscription_status,
        )

        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Active subscription required. Current status: {subscription_status}",
        )


def require_active_subscription(exempt_paths: List[str] = None):
    """
    Dependency to require active subscription for endpoint access

    Can be used as a dependency on individual routes or routers
    that require subscription access.

    Args:
        exempt_paths: Additional paths to exempt from subscription check

    Usage:
        @router.get("/protected", dependencies=[Depends(require_active_subscription())])
        async def protected_endpoint():
            ...
    """
    async def check_subscription(request: Request):
        user = getattr(request.state, "user", None)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Allow admin access
        if user.role == "ADMIN":
            return

        # Check subscription status
        subscription_status = user.subscriptionStatus

        if subscription_status not in SubscriptionMiddleware.ALLOWED_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Active subscription required. Current status: {subscription_status}",
            )

        # Check trial expiration
        if subscription_status == SubscriptionStatus.TRIAL:
            if user.trialEndDate and user.trialEndDate < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Trial period has expired. Please subscribe to continue.",
                )

    return check_subscription
