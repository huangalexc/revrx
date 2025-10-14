"""
FHIR Encounter Ingestion API Endpoints
Handle FHIR encounter ingestion and batch synchronization
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi import status as http_status
import structlog

from app.schemas.fhir import (
    FhirEncounterIngestRequest,
    FhirEncounterIngestResponse,
    FhirSyncEncountersRequest,
    FhirSyncEncountersResponse,
    FhirSyncStatusResponse,
)
from app.core.deps import get_current_user
from app.core.database import prisma
from app.tasks.fhir_processing import process_fhir_encounter
from app.services.fhir.sync_service import create_sync_service

router = APIRouter(prefix="/fhir", tags=["fhir"])
logger = structlog.get_logger(__name__)


@router.post("/ingest-encounter", response_model=FhirEncounterIngestResponse)
async def ingest_fhir_encounter(
    request: FhirEncounterIngestRequest,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user)
):
    """
    Ingest a single FHIR encounter

    - Validates FHIR connection exists and belongs to user
    - Checks for duplicates (already-processed encounters)
    - Processes encounter in background
    - Returns encounter ID and status
    """
    try:
        logger.info(
            "ingest_fhir_encounter",
            user_id=user.id,
            fhir_connection_id=request.fhir_connection_id,
            fhir_encounter_id=request.fhir_encounter_id,
        )

        # Validate FHIR connection exists and belongs to user
        connection = await prisma.fhirconnection.find_unique(
            where={"id": request.fhir_connection_id},
        )

        if not connection:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="FHIR connection not found",
            )

        if connection.userId != user.id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to use this FHIR connection",
            )

        if not connection.isActive:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="FHIR connection is inactive",
            )

        # Check for duplicates
        existing_encounter = await prisma.encounter.find_unique(
            where={"fhirEncounterId": request.fhir_encounter_id},
        )

        if existing_encounter:
            logger.info(
                "fhir_encounter_duplicate",
                fhir_encounter_id=request.fhir_encounter_id,
                existing_encounter_id=existing_encounter.id,
            )

            return FhirEncounterIngestResponse(
                success=True,
                encounter_id=existing_encounter.id,
                fhir_encounter_id=request.fhir_encounter_id,
                status=existing_encounter.status.value,
                message="Encounter already processed",
                is_duplicate=True,
            )

        # Queue for background processing
        # Note: For now, we process synchronously. In production, use Celery.
        logger.info(
            "queue_fhir_encounter_processing",
            fhir_encounter_id=request.fhir_encounter_id,
        )

        # Process encounter (this will create the encounter record)
        encounter_id = await process_fhir_encounter(
            fhir_connection_id=request.fhir_connection_id,
            fhir_encounter_id=request.fhir_encounter_id,
            user_id=user.id,
        )

        if encounter_id:
            logger.info(
                "fhir_encounter_ingested",
                encounter_id=encounter_id,
                fhir_encounter_id=request.fhir_encounter_id,
            )

            return FhirEncounterIngestResponse(
                success=True,
                encounter_id=encounter_id,
                fhir_encounter_id=request.fhir_encounter_id,
                status="COMPLETE",
                message="Encounter processed successfully",
                is_duplicate=False,
            )
        else:
            logger.error(
                "fhir_encounter_ingestion_failed",
                fhir_encounter_id=request.fhir_encounter_id,
            )

            return FhirEncounterIngestResponse(
                success=False,
                encounter_id=None,
                fhir_encounter_id=request.fhir_encounter_id,
                status="FAILED",
                message="Failed to process encounter",
                is_duplicate=False,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "ingest_fhir_encounter_error",
            fhir_encounter_id=request.fhir_encounter_id,
            user_id=user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest FHIR encounter: {str(e)}",
        )


@router.post("/sync-encounters", response_model=FhirSyncEncountersResponse)
async def sync_fhir_encounters(
    request: FhirSyncEncountersRequest,
    user = Depends(get_current_user)
):
    """
    Batch sync FHIR encounters

    - Validates FHIR connection exists and belongs to user
    - Queries FHIR server for encounters matching filters
    - Processes new encounters (skips duplicates)
    - Returns sync summary with statistics
    """
    try:
        logger.info(
            "sync_fhir_encounters",
            user_id=user.id,
            fhir_connection_id=request.fhir_connection_id,
            date_range_start=request.date_range_start,
            date_range_end=request.date_range_end,
            patient_ids=request.patient_ids,
        )

        # Validate FHIR connection exists and belongs to user
        connection = await prisma.fhirconnection.find_unique(
            where={"id": request.fhir_connection_id},
        )

        if not connection:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="FHIR connection not found",
            )

        if connection.userId != user.id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to use this FHIR connection",
            )

        if not connection.isActive:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="FHIR connection is inactive",
            )

        # Initialize sync service
        sync_service = await create_sync_service(request.fhir_connection_id)

        # Build date range tuple
        date_range = None
        if request.date_range_start or request.date_range_end:
            date_range = (
                request.date_range_start or "",
                request.date_range_end or "",
            )

        # Sync encounters
        sync_results = await sync_service.sync_encounters(
            date_range=date_range,
            patient_ids=request.patient_ids,
            status=request.status,
            limit=request.limit,
            process_async=False,  # Process synchronously for now
        )

        logger.info(
            "fhir_encounters_synced",
            user_id=user.id,
            fhir_connection_id=request.fhir_connection_id,
            total_found=sync_results["total_found"],
            new=sync_results["new"],
            processed=sync_results["processed"],
        )

        # Build success message
        message_parts = [
            f"Found {sync_results['total_found']} encounters",
            f"{sync_results['new']} new",
            f"{sync_results['skipped']} skipped (duplicates)",
            f"{sync_results['processed']} processed successfully",
        ]

        if sync_results["failed"] > 0:
            message_parts.append(f"{sync_results['failed']} failed")

        return FhirSyncEncountersResponse(
            success=sync_results["failed"] == 0,
            total_found=sync_results["total_found"],
            new=sync_results["new"],
            skipped=sync_results["skipped"],
            processed=sync_results["processed"],
            failed=sync_results["failed"],
            encounter_ids=sync_results["encounter_ids"],
            errors=sync_results["errors"],
            message=", ".join(message_parts),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "sync_fhir_encounters_error",
            user_id=user.id,
            fhir_connection_id=request.fhir_connection_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync FHIR encounters: {str(e)}",
        )


@router.get("/sync-status/{connection_id}", response_model=FhirSyncStatusResponse)
async def get_fhir_sync_status(
    connection_id: str,
    user = Depends(get_current_user)
):
    """
    Get FHIR sync status for a connection

    - Validates FHIR connection exists and belongs to user
    - Returns sync statistics and last sync timestamp
    """
    try:
        logger.info(
            "get_fhir_sync_status",
            connection_id=connection_id,
            user_id=user.id,
        )

        # Validate FHIR connection exists and belongs to user
        connection = await prisma.fhirconnection.find_unique(
            where={"id": connection_id},
        )

        if not connection:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="FHIR connection not found",
            )

        if connection.userId != user.id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this FHIR connection",
            )

        # Initialize sync service and get status
        sync_service = await create_sync_service(connection_id)
        sync_status = await sync_service.get_sync_status()

        logger.info(
            "fhir_sync_status_retrieved",
            connection_id=connection_id,
            total_synced=sync_status["total_encounters_synced"],
        )

        return FhirSyncStatusResponse(**sync_status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_fhir_sync_status_error",
            connection_id=connection_id,
            user_id=user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync status: {str(e)}",
        )
