"""
Admin API Endpoints

Administrative functions for user management, audit logs, and system metrics.
Requires ADMIN role for access.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

from app.core.database import prisma
from app.core.deps import get_current_admin_user
from app.core.audit import create_audit_log, log_admin_action, audit_log
from app.schemas.admin import (
    UserListResponse,
    UserDetail,
    AuditLogListResponse,
    AuditLogDetail,
    SystemMetricsResponse,
    UserUpdateRequest,
    SubscriptionOverrideRequest,
)
from app.schemas.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=UserListResponse)
@audit_log("ADMIN_LIST_USERS")
async def list_users(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    subscription_status: Optional[str] = None,
) -> UserListResponse:
    """
    List all users with pagination and filtering.

    **Required Role:** ADMIN

    **Query Parameters:**
    - page: Page number (default: 1)
    - limit: Items per page (default: 20, max: 100)
    - search: Search by email or name
    - role: Filter by role (ADMIN, MEMBER)
    - subscription_status: Filter by subscription status
    """
    skip = (page - 1) * limit

    # Build where clause
    where = {}

    if search:
        where["OR"] = [
            {"email": {"contains": search, "mode": "insensitive"}},
        ]

    if role:
        where["role"] = role

    if subscription_status:
        where["subscriptionStatus"] = subscription_status

    # Get total count
    total = await prisma.user.count(where=where)

    # Get users
    users = await prisma.user.find_many(
        where=where,
        skip=skip,
        take=limit,
        order={"createdAt": "desc"},
        include={
            "subscriptions": {
                "take": 1,
                "order": {"createdAt": "desc"},
            },
            "_count": {
                "select": {
                    "encounters": True,
                    "auditLogs": True,
                },
            },
        },
    )

    # Convert to response model
    user_details = []
    for user in users:
        user_details.append(
            UserDetail(
                id=user.id,
                email=user.email,
                role=user.role,
                emailVerified=user.emailVerified,
                subscriptionStatus=user.subscriptionStatus,
                stripeCustomerId=user.stripeCustomerId,
                trialEndDate=user.trialEndDate,
                createdAt=user.createdAt,
                updatedAt=user.updatedAt,
                lastLoginAt=user.lastLoginAt,
                encounterCount=user._count.encounters if user._count else 0,
                auditLogCount=user._count.auditLogs if user._count else 0,
            )
        )

    return UserListResponse(
        users=user_details,
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit,
    )


@router.get("/audit-logs", response_model=AuditLogListResponse)
@audit_log("ADMIN_VIEW_AUDIT_LOGS")
async def list_audit_logs(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> AuditLogListResponse:
    """
    Retrieve audit logs with filtering and pagination.

    **Required Role:** ADMIN

    **Query Parameters:**
    - page: Page number
    - limit: Items per page (max: 200)
    - user_id: Filter by user ID
    - action: Filter by action type
    - resource_type: Filter by resource type
    - start_date: Filter logs after this date (ISO format)
    - end_date: Filter logs before this date (ISO format)
    """
    skip = (page - 1) * limit

    # Build where clause
    where = {}

    if user_id:
        where["userId"] = user_id

    if action:
        where["action"] = {"contains": action, "mode": "insensitive"}

    if resource_type:
        where["resourceType"] = resource_type

    if start_date or end_date:
        where["createdAt"] = {}
        if start_date:
            where["createdAt"]["gte"] = start_date
        if end_date:
            where["createdAt"]["lte"] = end_date

    # Get total count
    total = await prisma.auditlog.count(where=where)

    # Get audit logs
    logs = await prisma.auditlog.find_many(
        where=where,
        skip=skip,
        take=limit,
        order={"createdAt": "desc"},
        include={"user": {"select": {"email": True}}},
    )

    # Convert to response model
    log_details = []
    for log in logs:
        log_details.append(
            AuditLogDetail(
                id=log.id,
                userId=log.userId,
                userEmail=log.user.email if log.user else None,
                action=log.action,
                resourceType=log.resourceType,
                resourceId=log.resourceId,
                ipAddress=log.ipAddress,
                userAgent=log.userAgent,
                metadata=log.metadata,
                createdAt=log.createdAt,
            )
        )

    return AuditLogListResponse(
        logs=log_details,
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit,
    )


@router.get("/metrics", response_model=SystemMetricsResponse)
@audit_log("ADMIN_VIEW_METRICS")
async def get_system_metrics(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    days: int = Query(30, ge=1, le=365),
) -> SystemMetricsResponse:
    """
    Get system-wide metrics and statistics.

    **Required Role:** ADMIN

    **Query Parameters:**
    - days: Number of days to include in time-series data (default: 30)
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    # User metrics
    total_users = await prisma.user.count()
    active_subscriptions = await prisma.user.count(
        where={"subscriptionStatus": {"in": ["TRIAL", "ACTIVE"]}}
    )
    new_users_period = await prisma.user.count(
        where={"createdAt": {"gte": start_date}}
    )

    # Encounter metrics
    total_encounters = await prisma.encounter.count()
    encounters_period = await prisma.encounter.count(
        where={"createdAt": {"gte": start_date}}
    )
    completed_encounters = await prisma.encounter.count(
        where={"status": "COMPLETED", "createdAt": {"gte": start_date}}
    )
    failed_encounters = await prisma.encounter.count(
        where={"status": "FAILED", "createdAt": {"gte": start_date}}
    )

    # Processing metrics
    avg_processing_time_result = await prisma.encounter.aggregate(
        where={
            "status": "COMPLETED",
            "processingTime": {"not": None},
            "createdAt": {"gte": start_date},
        },
        _avg={"processingTime": True},
    )
    avg_processing_time = (
        avg_processing_time_result._avg.processingTime
        if avg_processing_time_result._avg.processingTime
        else 0
    )

    # Revenue metrics
    revenue_result = await prisma.report.aggregate(
        where={"createdAt": {"gte": start_date}},
        _sum={"incrementalRevenue": True},
        _avg={"incrementalRevenue": True},
    )
    total_potential_revenue = revenue_result._sum.incrementalRevenue or 0
    avg_revenue_per_encounter = revenue_result._avg.incrementalRevenue or 0

    # Subscription metrics
    subscription_counts = await prisma.user.group_by(
        by=["subscriptionStatus"],
        _count=True,
    )

    subscription_breakdown = {
        item.subscriptionStatus: item._count for item in subscription_counts
    }

    # Audit log metrics
    total_audit_logs = await prisma.auditlog.count()
    audit_logs_period = await prisma.auditlog.count(
        where={"createdAt": {"gte": start_date}}
    )

    # Failed login attempts (security metric)
    failed_logins = await prisma.auditlog.count(
        where={
            "action": {"contains": "FAILED"},
            "createdAt": {"gte": start_date},
        }
    )

    # Time series data for encounters (daily breakdown)
    encounter_time_series = []
    for day in range(days):
        day_start = datetime.utcnow() - timedelta(days=days - day)
        day_end = day_start + timedelta(days=1)

        daily_count = await prisma.encounter.count(
            where={
                "createdAt": {"gte": day_start, "lt": day_end}
            }
        )

        encounter_time_series.append({
            "date": day_start.date().isoformat(),
            "count": daily_count,
        })

    return SystemMetricsResponse(
        users={
            "total": total_users,
            "active_subscriptions": active_subscriptions,
            "new_users_period": new_users_period,
        },
        encounters={
            "total": total_encounters,
            "period": encounters_period,
            "completed": completed_encounters,
            "failed": failed_encounters,
            "avg_processing_time_ms": int(avg_processing_time),
        },
        revenue={
            "total_potential": float(total_potential_revenue),
            "avg_per_encounter": float(avg_revenue_per_encounter),
        },
        subscriptions=subscription_breakdown,
        audit_logs={
            "total": total_audit_logs,
            "period": audit_logs_period,
            "failed_logins": failed_logins,
        },
        time_series=encounter_time_series,
    )


@router.patch("/users/{user_id}", response_model=UserDetail)
async def update_user(
    request: Request,
    user_id: str,
    user_update: UserUpdateRequest,
    current_user: User = Depends(get_current_admin_user),
) -> UserDetail:
    """
    Update user account (suspend, activate, change role, etc.).

    **Required Role:** ADMIN

    **Actions:**
    - Suspend/activate account
    - Change user role
    - Verify email manually
    - Extend trial period
    """
    # Get existing user
    user = await prisma.user.find_unique(where={"id": user_id})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prepare update data
    update_data = {}
    changes = {}

    if user_update.subscription_status is not None:
        update_data["subscriptionStatus"] = user_update.subscription_status
        changes["subscription_status"] = {
            "old": user.subscriptionStatus,
            "new": user_update.subscription_status,
        }

    if user_update.role is not None:
        update_data["role"] = user_update.role
        changes["role"] = {"old": user.role, "new": user_update.role}

    if user_update.email_verified is not None:
        update_data["emailVerified"] = user_update.email_verified
        changes["email_verified"] = {
            "old": user.emailVerified,
            "new": user_update.email_verified,
        }

    if user_update.trial_end_date is not None:
        update_data["trialEndDate"] = user_update.trial_end_date
        changes["trial_end_date"] = {
            "old": user.trialEndDate.isoformat() if user.trialEndDate else None,
            "new": user_update.trial_end_date.isoformat(),
        }

    # Update user
    updated_user = await prisma.user.update(
        where={"id": user_id}, data=update_data
    )

    # Log admin action
    await log_admin_action(
        action="ADMIN_USER_UPDATED",
        admin_user_id=current_user.id,
        target_user_id=user_id,
        resource_type="User",
        resource_id=user_id,
        changes=changes,
        ip_address=request.client.host if request.client else None,
    )

    logger.info(
        "admin_user_updated",
        admin_id=current_user.id,
        user_id=user_id,
        changes=changes,
    )

    return UserDetail(
        id=updated_user.id,
        email=updated_user.email,
        role=updated_user.role,
        emailVerified=updated_user.emailVerified,
        subscriptionStatus=updated_user.subscriptionStatus,
        stripeCustomerId=updated_user.stripeCustomerId,
        trialEndDate=updated_user.trialEndDate,
        createdAt=updated_user.createdAt,
        updatedAt=updated_user.updatedAt,
        lastLoginAt=updated_user.lastLoginAt,
        encounterCount=0,
        auditLogCount=0,
    )


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    request: Request,
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Suspend a user account.

    **Required Role:** ADMIN
    """
    user = await prisma.user.find_unique(where={"id": user_id})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "ADMIN":
        raise HTTPException(
            status_code=403, detail="Cannot suspend admin accounts"
        )

    # Update user status
    await prisma.user.update(
        where={"id": user_id}, data={"subscriptionStatus": "SUSPENDED"}
    )

    # Log action
    await log_admin_action(
        action="ADMIN_USER_SUSPENDED",
        admin_user_id=current_user.id,
        target_user_id=user_id,
        resource_type="User",
        resource_id=user_id,
        ip_address=request.client.host if request.client else None,
    )

    logger.warning(
        "user_suspended",
        admin_id=current_user.id,
        user_id=user_id,
        user_email=user.email,
    )

    return {"status": "success", "message": "User suspended"}


@router.post("/users/{user_id}/activate")
async def activate_user(
    request: Request,
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Activate a suspended user account.

    **Required Role:** ADMIN
    """
    user = await prisma.user.find_unique(where={"id": user_id})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update user status
    await prisma.user.update(
        where={"id": user_id}, data={"subscriptionStatus": "ACTIVE"}
    )

    # Log action
    await log_admin_action(
        action="ADMIN_USER_ACTIVATED",
        admin_user_id=current_user.id,
        target_user_id=user_id,
        resource_type="User",
        resource_id=user_id,
        ip_address=request.client.host if request.client else None,
    )

    logger.info(
        "user_activated",
        admin_id=current_user.id,
        user_id=user_id,
        user_email=user.email,
    )

    return {"status": "success", "message": "User activated"}


@router.post("/users/{user_id}/subscription-override")
async def override_subscription(
    request: Request,
    user_id: str,
    override_request: SubscriptionOverrideRequest,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Grant free or extended access to a user (override subscription).

    **Required Role:** ADMIN

    Use cases:
    - Grant free access for partners/testing
    - Extend trial for customer support
    - Provide complimentary access
    """
    user = await prisma.user.find_unique(where={"id": user_id})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Calculate new trial end date
    new_trial_end = datetime.utcnow() + timedelta(
        days=override_request.extend_days
    )

    # Update user
    await prisma.user.update(
        where={"id": user_id},
        data={
            "subscriptionStatus": "ACTIVE",
            "trialEndDate": new_trial_end,
        },
    )

    # Log action
    await log_admin_action(
        action="ADMIN_SUBSCRIPTION_OVERRIDE",
        admin_user_id=current_user.id,
        target_user_id=user_id,
        resource_type="User",
        resource_id=user_id,
        changes={
            "extend_days": override_request.extend_days,
            "new_trial_end": new_trial_end.isoformat(),
            "reason": override_request.reason,
        },
        ip_address=request.client.host if request.client else None,
    )

    logger.warning(
        "subscription_override",
        admin_id=current_user.id,
        user_id=user_id,
        extend_days=override_request.extend_days,
        reason=override_request.reason,
    )

    return {
        "status": "success",
        "message": f"Extended access by {override_request.extend_days} days",
        "trial_end_date": new_trial_end.isoformat(),
    }


@router.post("/data-retention/cleanup")
async def run_data_retention_cleanup(
    dry_run: bool = Query(False, description="Preview what would be deleted without actually deleting"),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Run data retention cleanup to delete expired encounters

    HIPAA Requirements:
    - Medical records retained for 7 years (configurable)
    - All deletions are audit logged
    - Cascading deletion of related data

    Args:
        dry_run: If True, only preview deletions without executing

    Returns:
        Cleanup statistics and deleted encounter IDs
    """
    from app.services.data_retention import DataRetentionService

    retention_service = DataRetentionService()

    # Find expired encounters
    expired_encounter_ids = await retention_service.find_expired_encounters()

    if dry_run:
        logger.info(
            "Data retention cleanup DRY RUN",
            admin_id=current_user.id,
            expired_count=len(expired_encounter_ids),
        )

        return {
            "dry_run": True,
            "expired_encounter_count": len(expired_encounter_ids),
            "expired_encounter_ids": expired_encounter_ids,
            "message": f"Would delete {len(expired_encounter_ids)} encounters (DRY RUN - no data deleted)",
        }

    # Execute cleanup
    stats = await retention_service.run_retention_cleanup(system_user_id=current_user.id)

    # Log admin action
    await log_admin_action(
        action="DATA_RETENTION_CLEANUP",
        admin_user_id=current_user.id,
        metadata={
            "deleted_encounters": stats["deleted_encounters"],
            "deleted_files": stats["total_deleted_files"],
            "errors": stats["errors"],
        },
    )

    logger.info(
        "Data retention cleanup completed",
        admin_id=current_user.id,
        stats=stats,
    )

    return {
        "dry_run": False,
        "deleted_encounters": stats["deleted_encounters"],
        "total_deleted_files": stats["total_deleted_files"],
        "total_s3_objects_deleted": stats["total_s3_objects_deleted"],
        "errors": stats["errors"],
        "message": f"Successfully deleted {stats['deleted_encounters']} expired encounters",
    }
