"""
Audit Logging System for HIPAA Compliance

This module provides decorators and utilities for comprehensive audit logging
of all sensitive operations, PHI access, and security events.
"""

import functools
import structlog
from typing import Any, Callable, Optional
from datetime import datetime
from fastapi import Request

from app.core.database import prisma
from prisma import Json

logger = structlog.get_logger(__name__)


async def create_audit_log(
    action: str,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """
    Create an audit log entry in the database.

    Args:
        action: Action performed (e.g., "LOGIN_SUCCESS", "VIEW_REPORT", "PHI_ACCESS")
        user_id: ID of user performing action
        resource_type: Type of resource (e.g., "Encounter", "Report")
        resource_id: ID of specific resource
        ip_address: Client IP address
        user_agent: Client user agent string
        metadata: Additional contextual data
    """
    try:
        await prisma.auditlog.create(
            data={
                "action": action,
                "userId": user_id,
                "resourceType": resource_type,
                "resourceId": resource_id,
                "ipAddress": ip_address,
                "userAgent": user_agent,
                "metadata": Json(metadata) if metadata else Json({}),
            }
        )

        logger.info(
            "audit_log_created",
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
        )
    except Exception as e:
        logger.error(
            "audit_log_failed",
            error=str(e),
            action=action,
            user_id=user_id,
        )
        # Don't raise - audit log failures should not break application flow


def audit_log(
    action: str,
    resource_type: Optional[str] = None,
    extract_resource_id: Optional[str] = None,
):
    """
    Decorator for auditing endpoint calls.

    Usage:
        @audit_log("VIEW_REPORT", resource_type="Report", extract_resource_id="encounter_id")
        async def get_report(encounter_id: str, current_user: User):
            ...

    Args:
        action: Action being performed
        resource_type: Type of resource (if applicable)
        extract_resource_id: Name of parameter containing resource ID
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and user info
            request: Optional[Request] = None
            user_id: Optional[str] = None
            resource_id: Optional[str] = None

            # Find request object
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            # Extract current_user if present
            current_user = kwargs.get("current_user")
            if current_user:
                user_id = getattr(current_user, "id", None)

            # Extract resource ID if specified
            if extract_resource_id and extract_resource_id in kwargs:
                resource_id = kwargs[extract_resource_id]

            # Get request metadata
            ip_address = None
            user_agent = None
            if request:
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get("user-agent")

            # Execute function
            try:
                result = await func(*args, **kwargs)

                # Log successful action
                await create_audit_log(
                    action=action,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata={"status": "success"},
                )

                return result

            except Exception as e:
                # Log failed action
                await create_audit_log(
                    action=f"{action}_FAILED",
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata={
                        "status": "failed",
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                raise

        return wrapper
    return decorator


def audit_phi_access(encounter_id: str):
    """
    Specialized decorator for PHI access logging.

    Usage:
        @audit_phi_access("encounter_id")
        async def get_phi_mapping(encounter_id: str, current_user: User):
            ...
    """
    return audit_log(
        action="PHI_ACCESS",
        resource_type="PhiMapping",
        extract_resource_id=encounter_id,
    )


async def log_authentication_event(
    action: str,
    email: str,
    success: bool,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    reason: Optional[str] = None,
) -> None:
    """
    Log authentication-related events (login, logout, failures).

    Args:
        action: AUTH_LOGIN, AUTH_LOGOUT, AUTH_FAILED, etc.
        email: User email attempting action
        success: Whether action succeeded
        ip_address: Client IP address
        user_agent: Client user agent
        reason: Failure reason (if applicable)
    """
    metadata = {
        "email": email,
        "success": success,
    }
    if reason:
        metadata["reason"] = reason

    await create_audit_log(
        action=action,
        user_id=None,  # User may not be authenticated yet
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata,
    )


async def log_upload_event(
    user_id: str,
    encounter_id: str,
    file_type: str,
    file_name: str,
    file_size: int,
    ip_address: Optional[str] = None,
) -> None:
    """
    Log file upload events.

    Args:
        user_id: User performing upload
        encounter_id: Associated encounter ID
        file_type: Type of file uploaded
        file_name: Original filename
        file_size: File size in bytes
        ip_address: Client IP address
    """
    await create_audit_log(
        action="FILE_UPLOAD",
        user_id=user_id,
        resource_type="UploadedFile",
        resource_id=encounter_id,
        ip_address=ip_address,
        metadata={
            "file_type": file_type,
            "file_name": file_name,
            "file_size": file_size,
        },
    )


async def log_report_generation(
    user_id: str,
    encounter_id: str,
    processing_time_ms: int,
    suggested_codes_count: int,
    incremental_revenue: float,
) -> None:
    """
    Log report generation events.

    Args:
        user_id: User who owns the encounter
        encounter_id: Encounter ID
        processing_time_ms: Processing time in milliseconds
        suggested_codes_count: Number of codes suggested
        incremental_revenue: Estimated incremental revenue
    """
    await create_audit_log(
        action="REPORT_GENERATED",
        user_id=user_id,
        resource_type="Report",
        resource_id=encounter_id,
        metadata={
            "processing_time_ms": processing_time_ms,
            "suggested_codes_count": suggested_codes_count,
            "incremental_revenue": incremental_revenue,
        },
    )


async def log_payment_event(
    action: str,
    user_id: str,
    amount: float,
    currency: str,
    stripe_event_id: Optional[str] = None,
    subscription_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """
    Log payment and subscription events.

    Args:
        action: PAYMENT_SUCCESS, SUBSCRIPTION_CREATED, etc.
        user_id: User ID
        amount: Payment amount
        currency: Currency code
        stripe_event_id: Stripe event ID
        subscription_id: Subscription ID
        metadata: Additional payment data
    """
    payment_metadata = {
        "amount": amount,
        "currency": currency,
        **(metadata or {}),
    }

    if stripe_event_id:
        payment_metadata["stripe_event_id"] = stripe_event_id

    await create_audit_log(
        action=action,
        user_id=user_id,
        resource_type="Subscription",
        resource_id=subscription_id,
        metadata=payment_metadata,
    )


async def log_admin_action(
    action: str,
    admin_user_id: str,
    target_user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    changes: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Log administrative actions.

    Args:
        action: ADMIN_USER_SUSPENDED, ADMIN_ROLE_CHANGED, etc.
        admin_user_id: ID of admin performing action
        target_user_id: ID of affected user (if applicable)
        resource_type: Type of resource modified
        resource_id: ID of resource modified
        changes: Dictionary of changes made
        ip_address: Admin's IP address
    """
    metadata = {
        "admin_user_id": admin_user_id,
    }

    if target_user_id:
        metadata["target_user_id"] = target_user_id
    if changes:
        metadata["changes"] = changes

    await create_audit_log(
        action=action,
        user_id=admin_user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        metadata=metadata,
    )


async def cleanup_old_audit_logs(days_to_retain: int = 2190) -> int:
    """
    Clean up audit logs older than specified retention period.

    HIPAA requires 6 years (2190 days) minimum retention.

    Args:
        days_to_retain: Number of days to retain (default: 6 years)

    Returns:
        Number of logs deleted
    """
    from datetime import timedelta

    cutoff_date = datetime.utcnow() - timedelta(days=days_to_retain)

    # Count logs to be deleted
    count = await prisma.auditlog.count(
        where={"createdAt": {"lt": cutoff_date}}
    )

    if count > 0:
        # Archive to cold storage before deletion (implementation depends on storage solution)
        logger.warning(
            "audit_log_cleanup",
            count=count,
            cutoff_date=cutoff_date.isoformat(),
            message="Audit logs should be archived before deletion",
        )

        # Delete old logs
        await prisma.auditlog.delete_many(
            where={"createdAt": {"lt": cutoff_date}}
        )

        logger.info("audit_logs_cleaned", count=count)

    return count
