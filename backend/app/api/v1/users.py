"""
User management endpoints
Handles user profile management and admin user operations
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from datetime import datetime
import structlog
import bcrypt

from app.core.database import prisma
from app.core.deps import (
    get_current_user,
    get_current_admin_user,
    get_current_active_user
)
from app.schemas.auth import UserResponse
from app.schemas.user import (
    UserProfileUpdate,
    ChangePasswordRequest,
    UserPreferencesUpdate,
    UserPreferencesResponse
)
from prisma.models import User


logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user's profile

    Requires authentication.
    """
    return UserResponse.model_validate(current_user)


@router.get("/me/subscription-status", response_model=dict)
async def get_subscription_status(current_user: User = Depends(get_current_user)):
    """
    Get current user's subscription status details

    Returns subscription status, trial info, and access permissions.
    """
    now = datetime.utcnow()

    response = {
        "subscriptionStatus": current_user.subscriptionStatus,
        "role": current_user.role,
        "hasActiveAccess": current_user.subscriptionStatus in ["ACTIVE", "TRIAL"],
    }

    # Add trial information if on trial
    if current_user.subscriptionStatus == "TRIAL" and current_user.trialEndDate:
        days_remaining = (current_user.trialEndDate - now).days
        response["trialInfo"] = {
            "trialEndDate": current_user.trialEndDate.isoformat(),
            "daysRemaining": max(0, days_remaining),
            "isExpired": current_user.trialEndDate < now,
        }

    # Get subscription details if exists
    if current_user.subscriptionStatus == "ACTIVE":
        subscription = await prisma.subscription.find_first(
            where={
                "userId": current_user.id,
                "status": "ACTIVE",
            },
            order={"createdAt": "desc"}
        )

        if subscription:
            response["subscription"] = {
                "currentPeriodStart": subscription.currentPeriodStart.isoformat(),
                "currentPeriodEnd": subscription.currentPeriodEnd.isoformat(),
                "billingInterval": subscription.billingInterval,
                "amount": subscription.amount,
                "currency": subscription.currency,
                "cancelAtPeriodEnd": subscription.cancelAtPeriodEnd,
            }

    return response


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update current user's profile information

    Allows updating: name, phone, timezone, language
    """
    # Build update data dict with only provided fields
    update_data = {}
    if profile_data.name is not None:
        update_data["name"] = profile_data.name
    if profile_data.phone is not None:
        update_data["phone"] = profile_data.phone
    if profile_data.timezone is not None:
        update_data["timezone"] = profile_data.timezone
    if profile_data.language is not None:
        update_data["language"] = profile_data.language

    # Update user in database
    updated_user = await prisma.user.update(
        where={"id": current_user.id},
        data=update_data
    )

    logger.info("User profile updated", user_id=current_user.id, fields_updated=list(update_data.keys()))

    return UserResponse.model_validate(updated_user)


@router.post("/me/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Change user password

    Requires current password for verification.
    New password must meet strength requirements.
    """
    # Validate passwords match
    if not request.validate_passwords_match():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match"
        )

    # Verify current password
    if not bcrypt.checkpw(
        request.current_password.encode('utf-8'),
        current_user.passwordHash.encode('utf-8')
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Hash new password
    new_password_hash = bcrypt.hashpw(
        request.new_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    # Update password in database
    await prisma.user.update(
        where={"id": current_user.id},
        data={"passwordHash": new_password_hash}
    )

    # Log password change
    await prisma.auditlog.create(
        data={
            "userId": current_user.id,
            "action": "PASSWORD_CHANGED",
            "resourceType": "User",
            "resourceId": current_user.id,
            "metadata": {}
        }
    )

    logger.info("Password changed", user_id=current_user.id)

    return {"message": "Password changed successfully"}


@router.get("/me/preferences", response_model=UserPreferencesResponse)
async def get_my_preferences(current_user: User = Depends(get_current_user)):
    """
    Get current user's preferences

    Returns theme, notification settings, date/time formats
    """
    return UserPreferencesResponse(
        theme=current_user.theme or "system",
        email_notifications=current_user.emailNotifications,
        date_format=current_user.dateFormat or "MM/DD/YYYY",
        time_format=current_user.timeFormat or "12h"
    )


@router.patch("/me/preferences", response_model=UserPreferencesResponse)
async def update_my_preferences(
    preferences: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update current user's preferences

    Allows updating: theme, emailNotifications, dateFormat, timeFormat
    """
    # Build update data dict with only provided fields
    update_data = {}
    if preferences.theme is not None:
        update_data["theme"] = preferences.theme
    if preferences.email_notifications is not None:
        update_data["emailNotifications"] = preferences.email_notifications
    if preferences.date_format is not None:
        update_data["dateFormat"] = preferences.date_format
    if preferences.time_format is not None:
        update_data["timeFormat"] = preferences.time_format

    # Update user preferences in database
    updated_user = await prisma.user.update(
        where={"id": current_user.id},
        data=update_data
    )

    logger.info("User preferences updated", user_id=current_user.id, fields_updated=list(update_data.keys()))

    return UserPreferencesResponse(
        theme=updated_user.theme or "system",
        email_notifications=updated_user.emailNotifications,
        date_format=updated_user.dateFormat or "MM/DD/YYYY",
        time_format=updated_user.timeFormat or "12h"
    )


# Admin-only endpoints below this line

@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[str] = Query(None),
    subscription_status: Optional[str] = Query(None, alias="subscriptionStatus"),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    List all users (Admin only)

    Supports filtering by role and subscription status, with pagination.
    """
    where_clause = {}

    if role:
        where_clause["role"] = role

    if subscription_status:
        where_clause["subscriptionStatus"] = subscription_status

    users = await prisma.user.find_many(
        where=where_clause,
        skip=skip,
        take=limit,
        order={"createdAt": "desc"}
    )

    return [UserResponse.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Get user by ID (Admin only)

    Returns detailed user information.
    """
    user = await prisma.user.find_unique(where={"id": user_id})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.model_validate(user)


@router.put("/{user_id}/suspend", response_model=UserResponse)
async def suspend_user(
    user_id: str,
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Suspend a user account (Admin only)

    Prevents user from accessing the system.
    """
    user = await prisma.user.find_unique(where={"id": user_id})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.subscriptionStatus == "SUSPENDED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already suspended"
        )

    # Update subscription status
    updated_user = await prisma.user.update(
        where={"id": user_id},
        data={"subscriptionStatus": "SUSPENDED"}
    )

    # Log suspension
    await prisma.auditlog.create(
        data={
            "userId": admin_user.id,
            "action": "USER_SUSPENDED",
            "resourceType": "User",
            "resourceId": user_id,
            "metadata": {"suspended_by": admin_user.email}
        }
    )

    logger.info("User suspended", user_id=user_id, admin_id=admin_user.id)

    return UserResponse.model_validate(updated_user)


@router.put("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: str,
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Activate a suspended user account (Admin only)

    Restores user access.
    """
    user = await prisma.user.find_unique(where={"id": user_id})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.subscriptionStatus != "SUSPENDED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not suspended"
        )

    # Determine new status based on trial/subscription
    new_status = "INACTIVE"
    if user.trialEndDate and user.trialEndDate > datetime.utcnow():
        new_status = "TRIAL"
    else:
        # Check if user has active subscription
        subscription = await prisma.subscription.find_first(
            where={
                "userId": user_id,
                "status": "ACTIVE",
            }
        )
        if subscription:
            new_status = "ACTIVE"

    # Update subscription status
    updated_user = await prisma.user.update(
        where={"id": user_id},
        data={"subscriptionStatus": new_status}
    )

    # Log activation
    await prisma.auditlog.create(
        data={
            "userId": admin_user.id,
            "action": "USER_ACTIVATED",
            "resourceType": "User",
            "resourceId": user_id,
            "metadata": {"activated_by": admin_user.email, "new_status": new_status}
        }
    )

    logger.info("User activated", user_id=user_id, admin_id=admin_user.id, new_status=new_status)

    return UserResponse.model_validate(updated_user)


@router.put("/{user_id}/grant-free-access", response_model=UserResponse)
async def grant_free_access(
    user_id: str,
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Grant free lifetime access to a user (Admin only)

    Sets user status to ACTIVE without requiring payment.
    """
    user = await prisma.user.find_unique(where={"id": user_id})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update subscription status
    updated_user = await prisma.user.update(
        where={"id": user_id},
        data={
            "subscriptionStatus": "ACTIVE",
            "trialEndDate": None,  # Remove trial end date
        }
    )

    # Log free access grant
    await prisma.auditlog.create(
        data={
            "userId": admin_user.id,
            "action": "FREE_ACCESS_GRANTED",
            "resourceType": "User",
            "resourceId": user_id,
            "metadata": {"granted_by": admin_user.email}
        }
    )

    logger.info("Free access granted", user_id=user_id, admin_id=admin_user.id)

    return UserResponse.model_validate(updated_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Delete a user account (Admin only)

    Permanently deletes user and all associated data.
    """
    user = await prisma.user.find_unique(where={"id": user_id})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-deletion
    if user.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    # Log deletion before deleting
    await prisma.auditlog.create(
        data={
            "userId": admin_user.id,
            "action": "USER_DELETED",
            "resourceType": "User",
            "resourceId": user_id,
            "metadata": {
                "deleted_by": admin_user.email,
                "deleted_user_email": user.email
            }
        }
    )

    # Delete user (cascades to related records)
    await prisma.user.delete(where={"id": user_id})

    logger.info("User deleted", user_id=user_id, admin_id=admin_user.id)

    return None
