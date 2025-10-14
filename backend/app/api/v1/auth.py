"""
Authentication endpoints
Handles user registration, login, email verification, password reset
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Body
from fastapi.responses import JSONResponse
import structlog

from app.core.database import prisma
from app.core.security import password_hasher, token_generator, jwt_manager
from app.core.deps import get_current_user, get_current_active_user
from app.core.config import settings
from app.services.email import email_service
from app.services.stripe_service import get_stripe_service
from app.schemas.auth import (
    UserRegistrationRequest,
    UserRegistrationResponse,
    UserLoginRequest,
    LoginResponse,
    TokenResponse,
    EmailVerificationRequest,
    EmailVerificationResponse,
    ResendVerificationRequest,
    PasswordResetRequest,
    PasswordResetResponse,
    PasswordResetConfirm,
    RefreshTokenRequest,
    UserResponse,
    UserProfileUpdateRequest,
    LogoutResponse,
)
from prisma.models import User


logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_user(request: UserRegistrationRequest):
    """
    Register a new user account

    Creates a new user with email and password, sends verification email.
    User must verify email before they can log in.
    """
    # Check if user already exists
    existing_user = await prisma.user.find_unique(where={"email": request.email})

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists"
        )

    # Hash password
    hashed_password = password_hasher.hash_password(request.password)

    # Create user
    user = await prisma.user.create(
        data={
            "email": request.email,
            "passwordHash": hashed_password,
            "role": "MEMBER",
            "emailVerified": False,
            "profileComplete": False,
            "subscriptionStatus": "INACTIVE",
        }
    )

    # Create Stripe customer (don't fail registration if Stripe fails)
    try:
        stripe_service = get_stripe_service()
        stripe_customer_id = await stripe_service.create_customer(
            email=user.email,
            user_id=user.id,
        )

        # Update user with Stripe customer ID
        user = await prisma.user.update(
            where={"id": user.id},
            data={"stripeCustomerId": stripe_customer_id},
        )

        logger.info("Stripe customer created", user_id=user.id, customer_id=stripe_customer_id)
    except Exception as e:
        logger.error("Failed to create Stripe customer during registration", user_id=user.id, error=str(e))
        # Continue with registration even if Stripe fails

    # Generate verification token
    verification_token = token_generator.generate_verification_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    # Store verification token
    await prisma.token.create(
        data={
            "userId": user.id,
            "token": verification_token,
            "tokenType": "EMAIL_VERIFICATION",
            "expiresAt": expires_at,
            "used": False,
        }
    )

    # Send verification email (don't fail registration if email fails)
    email_sent = False
    try:
        email_sent = await email_service.send_verification_email(
            to=user.email,
            token=verification_token
        )
        if email_sent:
            logger.info("Verification email sent", user_id=user.id, email=user.email)
        else:
            logger.warning("Verification email failed to send", user_id=user.id)
            # In development, log the token for testing
            if settings.APP_ENV == "development":
                logger.warning(
                    "DEV MODE: Email verification token (use this to test)",
                    token=verification_token,
                    verify_url=f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
                )
    except Exception as e:
        logger.error("Failed to send verification email", user_id=user.id, error=str(e))
        # In development, log the token for testing
        if settings.APP_ENV == "development":
            logger.warning(
                "DEV MODE: Email verification token (use this to test)",
                token=verification_token,
                verify_url=f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
            )

    # Log registration
    await prisma.auditlog.create(
        data={
            "userId": user.id,
            "action": "USER_REGISTERED",
            "resourceType": "User",
            "resourceId": user.id,
        }
    )

    return UserRegistrationResponse(
        message="Registration successful. Please check your email to verify your account.",
        userId=user.id,
        email=user.email
    )


@router.post("/verify-email", response_model=EmailVerificationResponse)
async def verify_email(request: EmailVerificationRequest):
    """
    Verify user email address using token

    Activates the user account and starts their trial period.
    """
    # Find token
    token_record = await prisma.token.find_unique(
        where={"token": request.token},
        include={"user": True}
    )

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )

    # Check if token is expired
    if token_record.expiresAt < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please request a new one."
        )

    # Check if token has been used
    if token_record.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has already been used"
        )

    # Check if token type is correct
    if token_record.tokenType != "EMAIL_VERIFICATION":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type"
        )

    # Update user - verify email and start trial
    trial_end_date = datetime.now(timezone.utc) + timedelta(days=7)

    user = await prisma.user.update(
        where={"id": token_record.userId},
        data={
            "emailVerified": True,
            "subscriptionStatus": "TRIAL",
            "trialEndDate": trial_end_date,
        }
    )

    # Mark token as used
    await prisma.token.update(
        where={"id": token_record.id},
        data={"used": True}
    )

    # Send welcome email
    try:
        await email_service.send_welcome_email(to=user.email, trial_days=7)
    except Exception as e:
        logger.error("Failed to send welcome email", user_id=user.id, error=str(e))

    # Log verification
    await prisma.auditlog.create(
        data={
            "userId": user.id,
            "action": "EMAIL_VERIFIED",
            "resourceType": "User",
            "resourceId": user.id,
        }
    )

    logger.info("Email verified", user_id=user.id, email=user.email)

    return EmailVerificationResponse(
        message="Email verified successfully. Your 7-day trial has started!",
        email=user.email
    )


@router.post("/resend-verification", response_model=dict)
async def resend_verification_email(request: ResendVerificationRequest):
    """
    Resend email verification token

    Sends a new verification email to the user if their email is not verified.
    """
    # Find user
    user = await prisma.user.find_unique(where={"email": request.email})

    if not user:
        # Don't reveal if user exists
        return {"message": "If an account with this email exists, a verification email has been sent."}

    if user.emailVerified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified"
        )

    # Delete old unused verification tokens
    await prisma.token.delete_many(
        where={
            "userId": user.id,
            "tokenType": "EMAIL_VERIFICATION",
            "used": False,
        }
    )

    # Generate new verification token
    verification_token = token_generator.generate_verification_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    # Store new token
    await prisma.token.create(
        data={
            "userId": user.id,
            "token": verification_token,
            "tokenType": "EMAIL_VERIFICATION",
            "expiresAt": expires_at,
            "used": False,
        }
    )

    # Send verification email
    try:
        await email_service.send_verification_email(
            to=user.email,
            token=verification_token
        )
        logger.info("Verification email resent", user_id=user.id)
    except Exception as e:
        logger.error("Failed to resend verification email", user_id=user.id, error=str(e))

    return {"message": "Verification email sent. Please check your inbox."}


@router.post("/login", response_model=LoginResponse)
async def login(request: UserLoginRequest):
    """
    Authenticate user and return JWT tokens

    Requires verified email address.
    """
    # Find user by email
    user = await prisma.user.find_unique(where={"email": request.email})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not password_hasher.verify_password(request.password, user.passwordHash):
        # Log failed login attempt
        await prisma.auditlog.create(
            data={
                "userId": user.id,
                "action": "LOGIN_FAILED",
                "resourceType": "User",
                "resourceId": user.id,
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if email is verified
    if not user.emailVerified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in"
        )

    # Create JWT tokens
    token_data = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
    }

    access_token = jwt_manager.create_access_token(data=token_data)
    refresh_token = jwt_manager.create_refresh_token(data=token_data)

    # Update last login time
    user = await prisma.user.update(
        where={"id": user.id},
        data={"lastLoginAt": datetime.now(timezone.utc)}
    )

    # Log successful login
    await prisma.auditlog.create(
        data={
            "userId": user.id,
            "action": "LOGIN_SUCCESS",
            "resourceType": "User",
            "resourceId": user.id,
        }
    )

    logger.info("User logged in", user_id=user.id, email=user.email)

    return LoginResponse(
        message="Login successful",
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            accessToken=access_token,
            refreshToken=refresh_token,
            tokenType="bearer",
            expiresIn=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token

    Returns a new access token if the refresh token is valid.
    """
    # Decode refresh token
    payload = jwt_manager.decode_token(request.refreshToken)

    # Verify it's a refresh token
    if not jwt_manager.verify_token_type(payload, "refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    # Extract user ID
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    # Verify user still exists
    user = await prisma.user.find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Create new access token
    token_data = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
    }

    access_token = jwt_manager.create_access_token(data=token_data)

    return TokenResponse(
        accessToken=access_token,
        refreshToken=request.refreshToken,  # Return same refresh token
        tokenType="bearer",
        expiresIn=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(request: PasswordResetRequest):
    """
    Initiate password reset flow

    Sends password reset email with token.
    """
    # Find user
    user = await prisma.user.find_unique(where={"email": request.email})

    # Don't reveal if user exists
    if not user:
        return PasswordResetResponse(
            message="If an account with this email exists, a password reset email has been sent."
        )

    # Delete old unused reset tokens
    await prisma.token.delete_many(
        where={
            "userId": user.id,
            "tokenType": "PASSWORD_RESET",
            "used": False,
        }
    )

    # Generate reset token
    reset_token = token_generator.generate_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    # Store reset token
    await prisma.token.create(
        data={
            "userId": user.id,
            "token": reset_token,
            "tokenType": "PASSWORD_RESET",
            "expiresAt": expires_at,
            "used": False,
        }
    )

    # Send password reset email
    email_sent = False
    try:
        email_sent = await email_service.send_password_reset_email(
            to=user.email,
            token=reset_token
        )
        if email_sent:
            logger.info("Password reset email sent", user_id=user.id)
        else:
            logger.warning("Password reset email failed to send", user_id=user.id)
            # In development, log the token for testing
            if settings.APP_ENV == "development":
                logger.warning(
                    "DEV MODE: Password reset token (use this to test)",
                    token=reset_token,
                    reset_url=f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
                )
    except Exception as e:
        logger.error("Failed to send password reset email", user_id=user.id, error=str(e))
        # In development, log the token for testing
        if settings.APP_ENV == "development":
            logger.warning(
                "DEV MODE: Password reset token (use this to test)",
                token=reset_token,
                reset_url=f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
            )

    # Log password reset request
    await prisma.auditlog.create(
        data={
            "userId": user.id,
            "action": "PASSWORD_RESET_REQUESTED",
            "resourceType": "User",
            "resourceId": user.id,
        }
    )

    return PasswordResetResponse(
        message="If an account with this email exists, a password reset email has been sent."
    )


@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(request: PasswordResetConfirm):
    """
    Reset password using token

    Validates token and updates user password.
    """
    # Find token
    token_record = await prisma.token.find_unique(
        where={"token": request.token},
        include={"user": True}
    )

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Check if token is expired
    if token_record.expiresAt < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one."
        )

    # Check if token has been used
    if token_record.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has already been used"
        )

    # Check if token type is correct
    if token_record.tokenType != "PASSWORD_RESET":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type"
        )

    # Hash new password
    hashed_password = password_hasher.hash_password(request.newPassword)

    # Update user password
    await prisma.user.update(
        where={"id": token_record.userId},
        data={"passwordHash": hashed_password}
    )

    # Mark token as used
    await prisma.token.update(
        where={"id": token_record.id},
        data={"used": True}
    )

    # Log password reset
    await prisma.auditlog.create(
        data={
            "userId": token_record.userId,
            "action": "PASSWORD_RESET_COMPLETED",
            "resourceType": "User",
            "resourceId": token_record.userId,
        }
    )

    logger.info("Password reset completed", user_id=token_record.userId)

    return PasswordResetResponse(
        message="Password reset successful. You can now log in with your new password."
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user profile

    Requires authentication.
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    request: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update current user profile

    Allows changing password. Requires current password for security.
    """
    update_data = {}

    # If changing password, verify current password
    if request.newPassword:
        if not request.currentPassword:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password required to change password"
            )

        # Verify current password
        if not password_hasher.verify_password(request.currentPassword, current_user.passwordHash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )

        # Hash new password
        update_data["passwordHash"] = password_hasher.hash_password(request.newPassword)

    # Update user if there are changes
    if update_data:
        user = await prisma.user.update(
            where={"id": current_user.id},
            data=update_data
        )

        # Log profile update
        await prisma.auditlog.create(
            data={
                "userId": current_user.id,
                "action": "PROFILE_UPDATED",
                "resourceType": "User",
                "resourceId": current_user.id,
            }
        )

        logger.info("User profile updated", user_id=current_user.id)

        return UserResponse.model_validate(user)

    return UserResponse.model_validate(current_user)


@router.post("/logout", response_model=LogoutResponse)
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout user

    Note: JWT tokens are stateless, so logout is handled client-side by removing tokens.
    This endpoint is provided for logging purposes and future token blacklisting.
    """
    # Log logout
    await prisma.auditlog.create(
        data={
            "userId": current_user.id,
            "action": "LOGOUT",
            "resourceType": "User",
            "resourceId": current_user.id,
        }
    )

    logger.info("User logged out", user_id=current_user.id)

    return LogoutResponse(
        message="Logout successful. Please remove your tokens from client storage."
    )
