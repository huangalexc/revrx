"""
Integration API Endpoints
Programmatic API for submitting encounters via API key authentication
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from prisma.enums import EncounterStatus

from app.core.deps import get_current_user_or_api_key, get_db
from app.core.logging import get_logger
from app.schemas.encounter import EncounterResponse, BillingCode

logger = get_logger(__name__)
router = APIRouter(prefix="/integrations", tags=["Integrations"])


class EncounterSubmitRequest(BaseModel):
    """Request to submit an encounter programmatically"""
    clinical_note: str = Field(..., description="Clinical note text content", min_length=50)
    billed_codes: List[BillingCode] = Field(..., description="List of billed CPT/ICD codes")
    patient_age: Optional[int] = Field(None, description="Patient age (de-identified)", ge=0, le=120)
    patient_sex: Optional[str] = Field(None, description="Patient sex (de-identified)", max_length=10)
    visit_date: Optional[datetime] = Field(None, description="Visit date (optional)")
    external_id: Optional[str] = Field(None, description="External reference ID from your system", max_length=100)


class EncounterSubmitResponse(BaseModel):
    """Response after submitting an encounter"""
    encounter_id: str
    status: str
    message: str
    created_at: datetime


@router.post("/encounters", response_model=EncounterSubmitResponse, status_code=status.HTTP_201_CREATED)
async def submit_encounter(
    request: EncounterSubmitRequest,
    user = Depends(get_current_user_or_api_key),
    db = Depends(get_db),
):
    """
    Submit an encounter for processing via API

    This endpoint accepts clinical notes and billing codes in JSON format.
    Authentication via API key (X-API-Key header) or JWT token.

    The encounter will be queued for processing and a report will be generated.
    Use webhooks to receive notifications when processing is complete.

    **Note**: Clinical notes should be de-identified before submission.
    """
    try:
        # Validate clinical note length
        if len(request.clinical_note) < 50:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Clinical note must be at least 50 characters",
            )

        if len(request.clinical_note) > 50000:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Clinical note exceeds maximum length of 50,000 characters",
            )

        # Validate billing codes
        if not request.billed_codes or len(request.billed_codes) == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one billing code is required",
            )

        # Create encounter record
        encounter = await db.encounter.create(
            data={
                "userId": user.id,
                "status": EncounterStatus.PENDING,
                "patientAge": request.patient_age,
                "patientSex": request.patient_sex,
                "visitDate": request.visit_date,
            }
        )

        # Store clinical note as uploaded file (in-memory storage)
        # In production, you'd store this in S3
        await db.uploadedfile.create(
            data={
                "encounterId": encounter.id,
                "fileType": "CLINICAL_NOTE_TXT",
                "fileName": f"api_submission_{encounter.id}.txt",
                "filePath": f"encounters/{user.id}/{encounter.id}/note.txt",
                "fileSize": len(request.clinical_note.encode('utf-8')),
                "mimeType": "text/plain",
                "scanStatus": "CLEAN",  # Assuming API submissions are trusted
            }
        )

        # Store billing codes as uploaded file (JSON format)
        billing_codes_json = [code.dict() for code in request.billed_codes]
        await db.uploadedfile.create(
            data={
                "encounterId": encounter.id,
                "fileType": "BILLING_CODES_JSON",
                "fileName": f"api_billing_codes_{encounter.id}.json",
                "filePath": f"encounters/{user.id}/{encounter.id}/codes.json",
                "fileSize": len(str(billing_codes_json).encode('utf-8')),
                "mimeType": "application/json",
                "scanStatus": "CLEAN",
            }
        )

        # Create audit log
        await db.auditlog.create(
            data={
                "userId": user.id,
                "action": "ENCOUNTER_SUBMITTED_API",
                "resourceType": "Encounter",
                "resourceId": encounter.id,
                "metadata": {
                    "external_id": request.external_id,
                    "code_count": len(request.billed_codes),
                },
            }
        )

        # TODO: Queue for processing (would be done via Celery task)
        # from app.tasks.encounter_tasks import process_encounter
        # process_encounter.delay(encounter.id)

        logger.info(
            f"Encounter submitted via API",
            encounter_id=encounter.id,
            user_id=user.id,
            external_id=request.external_id,
        )

        return EncounterSubmitResponse(
            encounter_id=encounter.id,
            status="pending",
            message="Encounter submitted successfully and queued for processing",
            created_at=encounter.createdAt,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit encounter", error=str(e), user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit encounter",
        )


@router.get("/encounters/{encounter_id}", response_model=EncounterResponse)
async def get_encounter(
    encounter_id: str,
    user = Depends(get_current_user_or_api_key),
    db = Depends(get_db),
):
    """
    Get encounter details by ID

    Returns encounter status and processing information.
    """
    try:
        encounter = await db.encounter.find_first(
            where={
                "id": encounter_id,
                "userId": user.id,
            },
            include={
                "uploadedFiles": True,
                "report": True,
            },
        )

        if not encounter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Encounter not found",
            )

        return EncounterResponse.from_orm(encounter)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get encounter", error=str(e), encounter_id=encounter_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get encounter",
        )


@router.get("/encounters", response_model=List[EncounterResponse])
async def list_encounters(
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    user = Depends(get_current_user_or_api_key),
    db = Depends(get_db),
):
    """
    List encounters for the authenticated user

    Supports pagination and filtering by status.
    """
    try:
        where_clause = {"userId": user.id}

        if status_filter:
            where_clause["status"] = status_filter

        encounters = await db.encounter.find_many(
            where=where_clause,
            include={
                "uploadedFiles": True,
                "report": True,
            },
            order={"createdAt": "desc"},
            skip=offset,
            take=limit,
        )

        return [EncounterResponse.from_orm(enc) for enc in encounters]

    except Exception as e:
        logger.error(f"Failed to list encounters", error=str(e), user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list encounters",
        )
