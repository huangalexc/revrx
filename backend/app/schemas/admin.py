"""
Admin API Schemas

Pydantic models for admin endpoints request/response data.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# User Management Schemas
class UserDetail(BaseModel):
    """Detailed user information for admin view"""
    id: str
    email: str
    role: str
    emailVerified: bool
    subscriptionStatus: str
    stripeCustomerId: Optional[str] = None
    trialEndDate: Optional[datetime] = None
    createdAt: datetime
    updatedAt: datetime
    lastLoginAt: Optional[datetime] = None
    encounterCount: int = 0
    auditLogCount: int = 0

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Paginated list of users"""
    users: List[UserDetail]
    total: int
    page: int
    limit: int
    pages: int


class UserUpdateRequest(BaseModel):
    """Request body for updating user"""
    subscription_status: Optional[str] = None
    role: Optional[str] = None
    email_verified: Optional[bool] = None
    trial_end_date: Optional[datetime] = None


class SubscriptionOverrideRequest(BaseModel):
    """Request to override user subscription"""
    extend_days: int = Field(..., ge=1, le=3650, description="Days to extend access")
    reason: str = Field(..., min_length=10, description="Reason for override")


# Audit Log Schemas
class AuditLogDetail(BaseModel):
    """Detailed audit log entry"""
    id: str
    userId: Optional[str] = None
    userEmail: Optional[str] = None
    action: str
    resourceType: Optional[str] = None
    resourceId: Optional[str] = None
    ipAddress: Optional[str] = None
    userAgent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    createdAt: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated list of audit logs"""
    logs: List[AuditLogDetail]
    total: int
    page: int
    limit: int
    pages: int


# System Metrics Schemas
class UserMetrics(BaseModel):
    """User-related metrics"""
    total: int
    active_subscriptions: int
    new_users_period: int


class EncounterMetrics(BaseModel):
    """Encounter processing metrics"""
    total: int
    period: int
    completed: int
    failed: int
    avg_processing_time_ms: int


class RevenueMetrics(BaseModel):
    """Revenue opportunity metrics"""
    total_potential: float
    avg_per_encounter: float


class AuditMetrics(BaseModel):
    """Audit log metrics"""
    total: int
    period: int
    failed_logins: int


class TimeSeriesDataPoint(BaseModel):
    """Single data point in time series"""
    date: str
    count: int


class SystemMetricsResponse(BaseModel):
    """Comprehensive system metrics"""
    users: UserMetrics
    encounters: EncounterMetrics
    revenue: RevenueMetrics
    subscriptions: Dict[str, int]
    audit_logs: AuditMetrics
    time_series: List[Dict[str, Any]]
