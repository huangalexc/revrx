"""
User Schemas
Pydantic models for User data validation and serialization
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum
import re


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    role: UserRole = UserRole.MEMBER


class User(UserBase):
    """User schema with all fields"""
    id: str
    email: EmailStr
    role: UserRole
    created_at: datetime
    updated_at: datetime
    email_verified: bool = False
    is_active: bool = True

    class Config:
        from_attributes = True


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    email_verified: Optional[bool] = None


class UserResponse(User):
    """User response schema (excludes sensitive data)"""
    pass


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile information"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Remove all non-digit characters for validation
            digits = re.sub(r'\D', '', v)
            if len(digits) < 10 or len(digits) > 15:
                raise ValueError('Phone number must be between 10 and 15 digits')
        return v

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Basic timezone validation - could be enhanced with pytz
            import pytz
            if v not in pytz.all_timezones:
                raise ValueError('Invalid timezone')
        return v


class ChangePasswordRequest(BaseModel):
    """Schema for changing user password"""
    current_password: str = Field(..., alias="currentPassword")
    new_password: str = Field(..., min_length=8, max_length=100, alias="newPassword")
    confirm_password: str = Field(..., alias="confirmPassword")

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

    def validate_passwords_match(self) -> bool:
        return self.new_password == self.confirm_password


class UserPreferencesUpdate(BaseModel):
    """Schema for updating user preferences"""
    theme: Optional[str] = Field(None, pattern="^(light|dark|system)$")
    email_notifications: Optional[bool] = Field(None, alias="emailNotifications")
    date_format: Optional[str] = Field(None, alias="dateFormat", pattern="^(MM/DD/YYYY|DD/MM/YYYY|YYYY-MM-DD)$")
    time_format: Optional[str] = Field(None, alias="timeFormat", pattern="^(12h|24h)$")


class UserPreferencesResponse(BaseModel):
    """Schema for user preferences response"""
    theme: str
    email_notifications: bool = Field(alias="emailNotifications")
    date_format: str = Field(alias="dateFormat")
    time_format: str = Field(alias="timeFormat")

    model_config = {"from_attributes": True, "populate_by_name": True}
