"""
Pydantic schemas for authentication endpoints
Request/response models for registration, login, verification, etc.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


# Registration schemas
class UserRegistrationRequest(BaseModel):
    """Request schema for user registration"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    confirmPassword: str = Field(..., alias="confirm_password")

    @validator('confirmPassword')
    def passwords_match(cls, v, values):
        """Validate that password and confirmPassword match"""
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

    @validator('password')
    def password_strength(cls, v):
        """Validate password strength"""
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


class UserRegistrationResponse(BaseModel):
    """Response schema for successful registration"""
    message: str
    userId: str = Field(..., alias="user_id")
    email: str

    model_config = {"populate_by_name": True}


# Login schemas
class UserLoginRequest(BaseModel):
    """Request schema for user login"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response schema for JWT tokens"""
    accessToken: str
    refreshToken: str
    tokenType: str = "bearer"
    expiresIn: int  # seconds


class LoginResponse(BaseModel):
    """Response schema for successful login"""
    message: str
    user: "UserResponse"
    tokens: TokenResponse


# Email verification schemas
class EmailVerificationRequest(BaseModel):
    """Request schema for email verification"""
    token: str


class EmailVerificationResponse(BaseModel):
    """Response schema for email verification"""
    message: str
    email: str


class ResendVerificationRequest(BaseModel):
    """Request schema to resend verification email"""
    email: EmailStr


# Password reset schemas
class PasswordResetRequest(BaseModel):
    """Request schema to initiate password reset"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Request schema to confirm password reset"""
    token: str
    newPassword: str = Field(..., min_length=8, max_length=100, alias="new_password")
    confirmPassword: str = Field(..., alias="confirm_password")

    @validator('confirmPassword')
    def passwords_match(cls, v, values):
        """Validate that newPassword and confirmPassword match"""
        if 'newPassword' in values and v != values['newPassword']:
            raise ValueError('Passwords do not match')
        return v

    @validator('newPassword')
    def password_strength(cls, v):
        """Validate password strength"""
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


class PasswordResetResponse(BaseModel):
    """Response schema for password reset"""
    message: str


# Token refresh schemas
class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh"""
    refreshToken: str = Field(..., alias="refresh_token")


# User response schemas
class UserResponse(BaseModel):
    """Response schema for user data"""
    id: str
    email: str
    role: str
    emailVerified: bool
    profileComplete: bool
    subscriptionStatus: str
    trialEndDate: Optional[datetime] = None
    createdAt: datetime
    lastLoginAt: Optional[datetime] = None

    # Profile fields
    name: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None

    # Preference fields
    theme: Optional[str] = None
    emailNotifications: Optional[bool] = None
    dateFormat: Optional[str] = None
    timeFormat: Optional[str] = None

    model_config = {"from_attributes": True}


class UserProfileUpdateRequest(BaseModel):
    """Request schema for updating user profile"""
    currentPassword: Optional[str] = Field(None, alias="current_password")
    newPassword: Optional[str] = Field(None, min_length=8, max_length=100, alias="new_password")
    confirmPassword: Optional[str] = Field(None, alias="confirm_password")

    @validator('confirmPassword')
    def passwords_match(cls, v, values):
        """Validate password match if changing password"""
        if v and 'newPassword' in values:
            if v != values['newPassword']:
                raise ValueError('Passwords do not match')
        return v

    @validator('newPassword')
    def password_change_validation(cls, v, values):
        """Validate that current password is provided when changing password"""
        if v and 'currentPassword' not in values:
            raise ValueError('Current password required to change password')
        return v


# Logout schema
class LogoutResponse(BaseModel):
    """Response schema for logout"""
    message: str


# Error response schema
class ErrorResponse(BaseModel):
    """Standard error response schema"""
    detail: str
    code: Optional[str] = None
