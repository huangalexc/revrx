"""
Payer Management API
Handles CRUD operations for insurance payers
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
import structlog

from app.core.deps import get_current_user
from app.core.database import prisma
from app.schemas.fee_schedule import (
    PayerResponse,
    PayerCreateRequest,
    PayerUpdateRequest,
)
from prisma.enums import PayerType

router = APIRouter(prefix="/payers", tags=["payers"])
logger = structlog.get_logger(__name__)


@router.get("/", response_model=List[PayerResponse])
async def list_payers(
    active_only: bool = True,
    payer_type: Optional[str] = None,
    user = Depends(get_current_user)
):
    """
    List all payers

    Query Parameters:
    - active_only: Filter by active payers only (default: True)
    - payer_type: Filter by payer type (COMMERCIAL, MEDICARE, etc.)
    """
    try:
        where_clause = {}

        if active_only:
            where_clause['isActive'] = True

        if payer_type:
            try:
                payer_type_enum = PayerType[payer_type.upper()]
                where_clause['payerType'] = payer_type_enum
            except KeyError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid payer type: {payer_type}"
                )

        payers = await prisma.payer.find_many(
            where=where_clause,
            order={'name': 'asc'}
        )

        return [PayerResponse.model_validate(p) for p in payers]

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error listing payers", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list payers")


@router.get("/{payer_id}", response_model=PayerResponse)
async def get_payer(
    payer_id: str,
    user = Depends(get_current_user)
):
    """
    Get a specific payer by ID
    """
    try:
        payer = await prisma.payer.find_unique(where={"id": payer_id})

        if not payer:
            raise HTTPException(status_code=404, detail="Payer not found")

        return PayerResponse.model_validate(payer)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting payer", payer_id=payer_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get payer")


@router.post("/", response_model=PayerResponse, status_code=201)
async def create_payer(
    payer_data: PayerCreateRequest,
    user = Depends(get_current_user)
):
    """
    Create a new payer

    Requires authentication
    """
    try:
        # Check if payer code already exists
        if payer_data.payer_code:
            existing = await prisma.payer.find_unique(
                where={"payerCode": payer_data.payer_code}
            )
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Payer code '{payer_data.payer_code}' already exists"
                )

        # Create payer
        payer = await prisma.payer.create(
            data={
                'name': payer_data.name,
                'payerCode': payer_data.payer_code,
                'payerType': payer_data.payer_type.value,
                'website': payer_data.website,
                'phone': payer_data.phone,
                'notes': payer_data.notes,
                'isActive': True
            }
        )

        logger.info(
            "Payer created",
            payer_id=payer.id,
            payer_name=payer.name,
            user_id=user.id
        )

        return PayerResponse.model_validate(payer)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating payer", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create payer")


@router.patch("/{payer_id}", response_model=PayerResponse)
async def update_payer(
    payer_id: str,
    payer_data: PayerUpdateRequest,
    user = Depends(get_current_user)
):
    """
    Update an existing payer

    Requires authentication
    """
    try:
        # Check if payer exists
        existing_payer = await prisma.payer.find_unique(where={"id": payer_id})
        if not existing_payer:
            raise HTTPException(status_code=404, detail="Payer not found")

        # Check if payer code is being changed and if it's already in use
        if payer_data.payer_code and payer_data.payer_code != existing_payer.payerCode:
            duplicate = await prisma.payer.find_unique(
                where={"payerCode": payer_data.payer_code}
            )
            if duplicate:
                raise HTTPException(
                    status_code=400,
                    detail=f"Payer code '{payer_data.payer_code}' already exists"
                )

        # Build update data (only include fields that are provided)
        update_data = {}
        if payer_data.name is not None:
            update_data['name'] = payer_data.name
        if payer_data.payer_code is not None:
            update_data['payerCode'] = payer_data.payer_code
        if payer_data.payer_type is not None:
            update_data['payerType'] = payer_data.payer_type.value
        if payer_data.website is not None:
            update_data['website'] = payer_data.website
        if payer_data.phone is not None:
            update_data['phone'] = payer_data.phone
        if payer_data.notes is not None:
            update_data['notes'] = payer_data.notes
        if payer_data.is_active is not None:
            update_data['isActive'] = payer_data.is_active

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Update payer
        payer = await prisma.payer.update(
            where={"id": payer_id},
            data=update_data
        )

        logger.info(
            "Payer updated",
            payer_id=payer.id,
            payer_name=payer.name,
            user_id=user.id,
            updated_fields=list(update_data.keys())
        )

        return PayerResponse.model_validate(payer)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating payer", payer_id=payer_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update payer")


@router.delete("/{payer_id}", status_code=204)
async def delete_payer(
    payer_id: str,
    user = Depends(get_current_user)
):
    """
    Delete a payer (soft delete by setting isActive to false)

    Requires authentication
    Note: This is a soft delete. The payer record remains in the database.
    """
    try:
        # Check if payer exists
        payer = await prisma.payer.find_unique(where={"id": payer_id})
        if not payer:
            raise HTTPException(status_code=404, detail="Payer not found")

        # Check if payer has active fee schedules
        active_schedules = await prisma.feeschedule.find_many(
            where={
                'payerId': payer_id,
                'isActive': True
            }
        )

        if active_schedules:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete payer with {len(active_schedules)} active fee schedules. " \
                       "Deactivate fee schedules first."
            )

        # Soft delete: set isActive to false
        await prisma.payer.update(
            where={"id": payer_id},
            data={'isActive': False}
        )

        logger.info(
            "Payer deactivated",
            payer_id=payer_id,
            payer_name=payer.name,
            user_id=user.id
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting payer", payer_id=payer_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete payer")
