"""
Webhook Schemas
Pydantic models for webhook management
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
from enum import Enum


class WebhookEvent(str, Enum):
    """Available webhook events"""
    ENCOUNTER_CREATED = "encounter.created"
    ENCOUNTER_PROCESSING = "encounter.processing"
    ENCOUNTER_COMPLETED = "encounter.completed"
    ENCOUNTER_FAILED = "encounter.failed"
    REPORT_GENERATED = "report.generated"


class WebhookCreate(BaseModel):
    """Request to create a webhook"""
    url: HttpUrl = Field(..., description="Webhook endpoint URL")
    events: List[WebhookEvent] = Field(..., description="Events to subscribe to", min_length=1)
    api_key_id: Optional[str] = Field(None, description="Optional API key ID to associate")


class WebhookResponse(BaseModel):
    """Webhook details"""
    id: str
    url: str
    events: List[str]
    secret: str
    is_active: bool
    failure_count: int
    last_success_at: Optional[datetime]
    last_failure_at: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookListResponse(BaseModel):
    """List of webhooks"""
    webhooks: List[WebhookResponse]
    total: int


class WebhookUpdateRequest(BaseModel):
    """Request to update a webhook"""
    url: Optional[HttpUrl] = None
    events: Optional[List[WebhookEvent]] = Field(None, min_length=1)
    is_active: Optional[bool] = None


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery log"""
    id: str
    webhook_id: str
    event: str
    status: str
    response_status: Optional[int]
    response_time: Optional[int]
    error: Optional[str]
    attempt_number: int
    max_attempts: int
    created_at: datetime
    delivered_at: Optional[datetime]
    next_retry_at: Optional[datetime]

    class Config:
        from_attributes = True


class WebhookDeliveryListResponse(BaseModel):
    """List of webhook deliveries"""
    deliveries: List[WebhookDeliveryResponse]
    total: int


class WebhookTestRequest(BaseModel):
    """Request to test a webhook"""
    event: WebhookEvent = Field(WebhookEvent.ENCOUNTER_COMPLETED, description="Event to simulate")
