"""
Audit Logs API Endpoints
Provides admin access to audit logs for HIPAA compliance and security monitoring
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status as http_status
from pydantic import BaseModel

from app.core.database import prisma
from app.core.deps import get_current_user, get_current_admin_user
from prisma.models import User

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


# Response Models
class AuditLogResponse(BaseModel):
    id: str
    userId: Optional[str]
    action: str
    resourceType: Optional[str]
    resourceId: Optional[str]
    ipAddress: Optional[str]
    userAgent: Optional[str]
    metadata: Optional[dict]
    createdAt: datetime

    class Config:
        from_attributes = True


class AuditLogsListResponse(BaseModel):
    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get(
    "",
    response_model=AuditLogsListResponse,
    status_code=http_status.HTTP_200_OK,
    dependencies=[Depends(get_current_admin_user)],
)
async def list_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    start_date: Optional[datetime] = Query(None, description="Filter logs from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter logs until this date"),
    current_user: User = Depends(get_current_user),
):
    """
    Get paginated list of audit logs (admin only).

    Supports filtering by:
    - User ID
    - Action type
    - Resource type and ID
    - Date range
    """
    # Build where clause
    where_conditions = {}

    if user_id:
        where_conditions["userId"] = user_id

    if action:
        where_conditions["action"] = {"contains": action, "mode": "insensitive"}

    if resource_type:
        where_conditions["resourceType"] = resource_type

    if resource_id:
        where_conditions["resourceId"] = resource_id

    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["gte"] = start_date
        if end_date:
            date_filter["lte"] = end_date
        where_conditions["createdAt"] = date_filter

    # Get total count
    total = await prisma.auditlog.count(where=where_conditions if where_conditions else None)

    # Calculate pagination
    skip = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size

    # Fetch logs
    logs = await prisma.auditlog.find_many(
        where=where_conditions if where_conditions else None,
        order={"createdAt": "desc"},
        skip=skip,
        take=page_size,
    )

    return AuditLogsListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/encounter/{encounter_id}",
    response_model=List[AuditLogResponse],
    status_code=http_status.HTTP_200_OK,
)
async def get_encounter_audit_logs(
    encounter_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get all audit logs for a specific encounter.

    Users can only view logs for their own encounters.
    Admins can view all encounter logs.
    """
    # Check if encounter belongs to user (unless admin)
    if current_user.role != "ADMIN":
        encounter = await prisma.encounter.find_unique(
            where={"id": encounter_id}
        )

        if not encounter:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Encounter not found"
            )

        if encounter.userId != current_user.id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this encounter's audit logs"
            )

    # Fetch audit logs related to this encounter
    logs = await prisma.auditlog.find_many(
        where={
            "OR": [
                {"resourceId": encounter_id},
                {"metadata": {"path": ["encounter_id"], "equals": encounter_id}},
            ]
        },
        order={"createdAt": "asc"},
    )

    return [AuditLogResponse.model_validate(log) for log in logs]


@router.get(
    "/user/{user_id}",
    response_model=List[AuditLogResponse],
    status_code=http_status.HTTP_200_OK,
    dependencies=[Depends(get_current_admin_user)],
)
async def get_user_audit_logs(
    user_id: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of logs to return"),
    current_user: User = Depends(get_current_user),
):
    """
    Get audit logs for a specific user (admin only).
    """
    logs = await prisma.auditlog.find_many(
        where={"userId": user_id},
        order={"createdAt": "desc"},
        take=limit,
    )

    return [AuditLogResponse.model_validate(log) for log in logs]


@router.get(
    "/actions",
    response_model=List[str],
    status_code=http_status.HTTP_200_OK,
    dependencies=[Depends(get_current_admin_user)],
)
async def get_distinct_actions(
    current_user: User = Depends(get_current_user),
):
    """
    Get list of all distinct action types in audit logs (admin only).
    Useful for filtering.
    """
    # Note: Prisma doesn't have a direct distinct() method for specific fields
    # We'll fetch all actions and deduplicate in Python
    logs = await prisma.auditlog.find_many(
        select={"action": True},
        order={"action": "asc"},
    )

    actions = list(set(log.action for log in logs if log.action))
    return sorted(actions)
