"""
Subscription and Payment Schemas
Pydantic models for subscription and payment requests/responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SubscriptionStatusEnum(str, Enum):
    """Subscription status values"""
    INACTIVE = "INACTIVE"
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"


class CheckoutSessionCreate(BaseModel):
    """Request to create a checkout session"""
    success_url: str = Field(..., description="URL to redirect after successful payment")
    cancel_url: str = Field(..., description="URL to redirect if checkout is cancelled")
    trial_period_days: Optional[int] = Field(None, description="Number of days for trial period")


class CheckoutSessionResponse(BaseModel):
    """Response containing checkout session data"""
    session_id: str
    url: str


class TrialActivationRequest(BaseModel):
    """Request to activate trial"""
    trial_days: int = Field(7, description="Number of days for trial period")


class TrialActivationResponse(BaseModel):
    """Response after trial activation"""
    trial_activated: bool
    trial_end_date: datetime
    subscription_status: SubscriptionStatusEnum


class SubscriptionResponse(BaseModel):
    """Subscription details response"""
    id: str
    user_id: str
    stripe_subscription_id: str
    stripe_customer_id: str
    status: SubscriptionStatusEnum
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    canceled_at: Optional[datetime] = None
    amount: float
    currency: str
    billing_interval: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionStatusResponse(BaseModel):
    """Current subscription status"""
    is_subscribed: bool
    subscription_status: SubscriptionStatusEnum
    trial_end_date: Optional[datetime] = None
    subscription: Optional[SubscriptionResponse] = None
    days_remaining: Optional[int] = None


class CancelSubscriptionRequest(BaseModel):
    """Request to cancel subscription"""
    cancel_at_period_end: bool = Field(
        True, description="If True, cancel at end of period; if False, cancel immediately"
    )


class CancelSubscriptionResponse(BaseModel):
    """Response after canceling subscription"""
    success: bool
    message: str
    subscription: Optional[SubscriptionResponse] = None


class PaymentMethodResponse(BaseModel):
    """Payment method details"""
    id: str
    type: str
    card: dict


class InvoiceResponse(BaseModel):
    """Invoice details"""
    id: str
    number: Optional[str]
    status: str
    amount_due: float
    amount_paid: float
    currency: str
    invoice_pdf: Optional[str]
    hosted_invoice_url: Optional[str]
    created: datetime
    due_date: Optional[datetime]


class BillingHistoryResponse(BaseModel):
    """Billing history with invoices"""
    invoices: List[InvoiceResponse]
    payment_methods: List[PaymentMethodResponse]
