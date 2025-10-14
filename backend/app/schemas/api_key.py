"""
API Key Schemas
Pydantic models for API key management
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ApiKeyCreate(BaseModel):
    """Request to create a new API key"""
    name: str = Field(..., description="Name for the API key", min_length=1, max_length=100)
    rate_limit: Optional[int] = Field(100, description="Rate limit per minute", ge=1, le=10000)
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date")


class ApiKeyResponse(BaseModel):
    """API key details (without the actual key)"""
    id: str
    name: str
    key_prefix: str
    is_active: bool
    rate_limit: int
    usage_count: int
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApiKeyCreateResponse(BaseModel):
    """Response after creating an API key (includes the actual key once)"""
    api_key: str = Field(..., description="The actual API key - save this, it won't be shown again")
    key: ApiKeyResponse


class ApiKeyListResponse(BaseModel):
    """List of API keys"""
    keys: list[ApiKeyResponse]
    total: int


class ApiKeyUpdateRequest(BaseModel):
    """Request to update an API key"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    rate_limit: Optional[int] = Field(None, ge=1, le=10000)
