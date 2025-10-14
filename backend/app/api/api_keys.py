"""
API Key Management Endpoints
Handles API key generation, listing, and revocation
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from prisma import models

from app.core.deps import get_current_user, get_db
from app.services.api_key_service import ApiKeyService
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyResponse,
    ApiKeyListResponse,
    ApiKeyUpdateRequest,
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api-keys", tags=["API Keys"])


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: ApiKeyCreate,
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
):
    """
    Create a new API key

    The API key will only be shown once. Make sure to save it securely.
    """
    try:
        full_key, api_key_record = await ApiKeyService.create_api_key(
            db=db,
            user_id=current_user.id,
            name=request.name,
            rate_limit=request.rate_limit or 100,
            expires_at=request.expires_at,
        )

        # Create audit log
        await db.auditlog.create(
            data={
                "userId": current_user.id,
                "action": "API_KEY_CREATED",
                "resourceType": "ApiKey",
                "resourceId": api_key_record.id,
                "metadata": {"name": request.name},
            }
        )

        return ApiKeyCreateResponse(
            api_key=full_key,
            key=ApiKeyResponse.from_orm(api_key_record),
        )

    except Exception as e:
        logger.error(f"Failed to create API key", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key",
        )


@router.get("", response_model=ApiKeyListResponse)
async def list_api_keys(
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
):
    """
    List all API keys for the current user

    Does not include the actual API key values, only metadata.
    """
    try:
        api_keys = await db.apikey.find_many(
            where={"userId": current_user.id},
            order={"createdAt": "desc"},
        )

        return ApiKeyListResponse(
            keys=[ApiKeyResponse.from_orm(key) for key in api_keys],
            total=len(api_keys),
        )

    except Exception as e:
        logger.error(f"Failed to list API keys", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys",
        )


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: str,
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
):
    """Get details of a specific API key"""
    try:
        api_key = await db.apikey.find_first(
            where={"id": key_id, "userId": current_user.id}
        )

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found",
            )

        return ApiKeyResponse.from_orm(api_key)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get API key", error=str(e), key_id=key_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get API key",
        )


@router.patch("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: str,
    request: ApiKeyUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
):
    """
    Update an API key

    Can update name, active status, and rate limit.
    """
    try:
        # Verify ownership
        api_key = await db.apikey.find_first(
            where={"id": key_id, "userId": current_user.id}
        )

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found",
            )

        # Build update data
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.is_active is not None:
            update_data["isActive"] = request.is_active
        if request.rate_limit is not None:
            update_data["rateLimit"] = request.rate_limit

        # Update
        updated_key = await db.apikey.update(
            where={"id": key_id},
            data=update_data,
        )

        # Audit log
        await db.auditlog.create(
            data={
                "userId": current_user.id,
                "action": "API_KEY_UPDATED",
                "resourceType": "ApiKey",
                "resourceId": key_id,
                "metadata": update_data,
            }
        )

        logger.info(f"API key updated", key_id=key_id, user_id=current_user.id)

        return ApiKeyResponse.from_orm(updated_key)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update API key", error=str(e), key_id=key_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API key",
        )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    current_user: models.User = Depends(get_current_user),
    db = Depends(get_db),
):
    """
    Revoke (delete) an API key

    This action cannot be undone.
    """
    try:
        success = await ApiKeyService.revoke_api_key(
            db=db,
            key_id=key_id,
            user_id=current_user.id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found",
            )

        # Audit log
        await db.auditlog.create(
            data={
                "userId": current_user.id,
                "action": "API_KEY_REVOKED",
                "resourceType": "ApiKey",
                "resourceId": key_id,
            }
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete API key", error=str(e), key_id=key_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete API key",
        )
