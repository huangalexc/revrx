"""
Encounters API Endpoints
Handle clinical note uploads and billing code uploads
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form, BackgroundTasks, Body
from fastapi import status as http_status
from typing import List, Optional
from pydantic import BaseModel
import io
import json
import csv
from datetime import datetime
import structlog

from app.schemas.encounter import (
    EncounterResponse,
    EncounterListResponse,
    FileUploadResponse,
    BillingCodesUpload,
    BillingCode,
    FileType,
    EncounterStatus,
)
from app.core.deps import get_current_user
from app.core.storage import storage_service, StorageError
from app.utils.file_validation import validate_upload_file, sanitize_filename
from app.utils.text_extraction import extract_text, validate_extracted_text, TextExtractionError
from app.utils.file_hash import compute_file_hash
from app.core.database import prisma
from app.tasks.phi_processing import process_encounter_phi
from app.services.duplicate_detection import duplicate_detection_service

router = APIRouter(prefix="/encounters", tags=["encounters"])
logger = structlog.get_logger(__name__)


class BulkDeleteRequest(BaseModel):
    encounter_ids: List[str]


@router.post("/upload-note", response_model=FileUploadResponse, status_code=http_status.HTTP_201_CREATED)
async def upload_clinical_note(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    batch_id: Optional[str] = Form(None),
    duplicate_handling: Optional[str] = Form(None),
    user = Depends(get_current_user)
):
    """
    Upload clinical note (TXT, PDF, or DOCX)

    - Validates file type and size
    - Extracts text from document
    - Stores encrypted file in S3
    - Creates encounter record in database
    """
    try:
        # Determine file type from extension
        file_ext = file.filename.split('.')[-1].lower()
        if file_ext not in ['txt', 'pdf', 'docx']:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Supported types: TXT, PDF, DOCX"
            )

        # Map file extension to FileType enum
        file_type_map = {
            'txt': FileType.TXT,
            'pdf': FileType.PDF,
            'docx': FileType.DOCX,
        }
        file_type = file_type_map[file_ext]

        # Validate and read file
        file_content, mime_type = await validate_upload_file(file, file_type)
        file_size = len(file_content)

        # Extract text from file
        try:
            extracted_text = extract_text(file_content, file_ext)
        except TextExtractionError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Failed to extract text from file: {str(e)}"
            )

        # Validate extracted text
        if not validate_extracted_text(extracted_text, min_length=50):
            raise HTTPException(
                status_code=422,
                detail="Extracted text is too short or empty. Minimum 50 characters required."
            )

        # Compute file hash for duplicate detection
        file_hash = compute_file_hash(file_content)
        logger.info("File hash computed", file_hash_preview=file_hash[:16])

        # Create encounter record in database with batch_id if provided
        encounter_data = {
            "user": {"connect": {"id": user.id}},
            "status": "PENDING",
        }
        if batch_id:
            encounter_data["batchId"] = batch_id

        encounter = await prisma.encounter.create(data=encounter_data)

        # Sanitize filename
        safe_filename = sanitize_filename(file.filename)

        # Upload raw file to S3 (skip for local dev if S3 not configured)
        file_key = storage_service.get_file_key(user.id, encounter.id, safe_filename)

        try:
            await storage_service.upload_file(
                file_obj=io.BytesIO(file_content),
                key=file_key,
                content_type=mime_type,
                metadata={
                    'user_id': user.id,
                    'encounter_id': encounter.id,
                    'original_filename': file.filename,
                    'file_type': file_ext,
                }
            )
            logger.info("File uploaded to S3 successfully", file_key=file_key)
        except Exception as e:
            # For local dev, continue without S3 storage
            logger.warning("S3 upload skipped (local dev mode)", error=str(e))
            file_key = f"local://{user.id}/{encounter.id}/{safe_filename}"

        # Map file extension to Prisma FileType enum value
        prisma_file_type_map = {
            'txt': 'CLINICAL_NOTE_TXT',
            'pdf': 'CLINICAL_NOTE_PDF',
            'docx': 'CLINICAL_NOTE_DOCX',
        }

        # Create uploaded file record with extracted text and hash
        uploaded_file = await prisma.uploadedfile.create(
            data={
                "encounter": {"connect": {"id": encounter.id}},
                "fileType": prisma_file_type_map[file_ext],
                "fileName": safe_filename,
                "filePath": file_key,
                "fileSize": file_size,
                "mimeType": mime_type,
                "extractedText": extracted_text,  # Store extracted text for PHI processing
                "fileHash": file_hash,  # Store hash for duplicate detection
                "duplicateHandling": duplicate_handling if duplicate_handling else None,
            }
        )

        # Trigger background task for PHI detection and de-identification
        # This will:
        # 1. Download file from S3
        # 2. Extract text
        # 3. Detect PHI using Amazon Comprehend Medical
        # 4. Redact PHI and store in PhiMapping (encrypted)
        # 5. Delete original file from S3 (HIPAA compliance)
        # 6. Update encounter status to COMPLETED
        background_tasks.add_task(process_encounter_phi, encounter.id)

        logger.info(
            "Clinical note uploaded successfully, PHI processing queued",
            encounter_id=encounter.id,
            user_id=user.id,
            file_size=file_size,
            text_length=len(extracted_text)
        )

        return FileUploadResponse(
            encounter_id=encounter.id,
            file_name=safe_filename,
            file_size=file_size,
            status="success",
            message="Clinical note uploaded successfully. Processing will begin shortly."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during file upload", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during upload"
        )


@router.post("/{encounter_id}/upload-codes", response_model=dict, status_code=http_status.HTTP_200_OK)
async def upload_billing_codes(
    encounter_id: str,
    file: Optional[UploadFile] = File(None),
    codes_json: Optional[str] = Form(None),
    user = Depends(get_current_user)
):
    """
    Upload billing codes for an encounter (CSV or JSON)

    Can accept either:
    - CSV file with columns: code, type, description (optional)
    - JSON file or form data with array of billing codes
    """
    try:
        # Verify encounter exists and belongs to user
        encounter = await prisma.encounter.find_unique(
            where={"id": encounter_id}
        )

        if not encounter:
            raise HTTPException(
                status_code=404,
                detail="Encounter not found"
            )

        if encounter.userId != user.id and user.role != "ADMIN":
            raise HTTPException(
                status_code=403,
                detail="Not authorized to modify this encounter"
            )

        # Parse billing codes from file or JSON
        billing_codes: List[BillingCode] = []

        if file:
            # Handle file upload (CSV or JSON)
            file_ext = file.filename.split('.')[-1].lower()

            if file_ext == 'csv':
                billing_codes = await parse_csv_codes(file)
            elif file_ext == 'json':
                billing_codes = await parse_json_codes_from_file(file)
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file type. Supported: CSV, JSON"
                )

        elif codes_json:
            # Handle JSON form data
            billing_codes = parse_json_codes_from_string(codes_json)

        else:
            raise HTTPException(
                status_code=400,
                detail="Either file or codes_json must be provided"
            )

        if not billing_codes:
            raise HTTPException(
                status_code=400,
                detail="No valid billing codes found"
            )

        # Store billing codes in database
        for code in billing_codes:
            await prisma.billingcode.create(
                data={
                    "encounterId": encounter_id,
                    "code": code.code,
                    "codeType": code.type.value,
                    "description": code.description,
                    "isBilled": True,  # These are the codes that were billed
                }
            )

        logger.info(
            "Billing codes uploaded",
            encounter_id=encounter_id,
            user_id=user.id,
            code_count=len(billing_codes)
        )

        # If report already exists, update it with the billed codes
        report = await prisma.report.find_unique(
            where={"encounterId": encounter_id}
        )

        if report:
            # Get all billed codes for this encounter
            all_billed_codes = await prisma.billingcode.find_many(
                where={"encounterId": encounter_id, "isBilled": True}
            )

            billed_codes_json = [
                {
                    "code": bc.code,
                    "code_type": bc.codeType,
                    "description": bc.description or f"{bc.codeType} {bc.code}"
                }
                for bc in all_billed_codes
            ]

            # Import Json type for Prisma
            from prisma import Json

            # Update report with billed codes
            await prisma.report.update(
                where={"id": report.id},
                data={"billedCodes": Json(billed_codes_json)}
            )

            logger.info(
                "Updated report with billed codes",
                encounter_id=encounter_id,
                report_id=report.id,
                billed_codes_count=len(billed_codes_json)
            )

        return {
            "encounter_id": encounter_id,
            "codes_uploaded": len(billing_codes),
            "status": "success",
            "message": f"Successfully uploaded {len(billing_codes)} billing codes"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error uploading billing codes", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to upload billing codes"
        )


async def parse_csv_codes(file: UploadFile) -> List[BillingCode]:
    """Parse billing codes from CSV file"""
    try:
        content = await file.read()
        text_content = content.decode('utf-8')

        reader = csv.DictReader(io.StringIO(text_content))
        codes = []

        for row_num, row in enumerate(reader, start=2):
            try:
                code = BillingCode(
                    code=row.get('code', '').strip(),
                    type=row.get('type', '').strip(),
                    description=row.get('description', '').strip() or None
                )
                codes.append(code)
            except Exception as e:
                logger.warning(
                    f"Skipping invalid code at row {row_num}",
                    error=str(e),
                    row=row
                )
                continue

        return codes

    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse CSV file: {str(e)}"
        )


async def parse_json_codes_from_file(file: UploadFile) -> List[BillingCode]:
    """Parse billing codes from JSON file"""
    try:
        content = await file.read()
        data = json.loads(content)

        if not isinstance(data, list):
            raise HTTPException(
                status_code=422,
                detail="JSON must contain an array of codes"
            )

        codes = []
        for item in data:
            try:
                code = BillingCode(**item)
                codes.append(code)
            except Exception as e:
                logger.warning("Skipping invalid code", error=str(e), item=item)
                continue

        return codes

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=422,
            detail="Invalid JSON format"
        )


def parse_json_codes_from_string(json_string: str) -> List[BillingCode]:
    """Parse billing codes from JSON string"""
    try:
        data = json.loads(json_string)

        if not isinstance(data, list):
            raise HTTPException(
                status_code=422,
                detail="JSON must contain an array of codes"
            )

        codes = []
        for item in data:
            try:
                code = BillingCode(**item)
                codes.append(code)
            except Exception as e:
                logger.warning("Skipping invalid code", error=str(e), item=item)
                continue

        return codes

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=422,
            detail="Invalid JSON format"
        )


@router.get("/", response_model=EncounterListResponse)
async def list_encounters(
    page: int = 1,
    page_size: int = 20,
    fhir_encounter_id: Optional[str] = None,
    fhir_patient_id: Optional[str] = None,
    encounter_source: Optional[str] = None,
    user = Depends(get_current_user)
):
    """
    List encounters for current user with pagination

    Optional filters:
    - fhir_encounter_id: Filter by FHIR Encounter ID
    - fhir_patient_id: Filter by FHIR Patient ID
    - encounter_source: Filter by source (FILE_UPLOAD or FHIR)
    """
    try:
        skip = (page - 1) * page_size

        # Build where clause with filters
        where_clause = {"userId": user.id}

        if fhir_encounter_id:
            where_clause["fhirEncounterId"] = fhir_encounter_id

        if fhir_patient_id:
            where_clause["fhirPatientId"] = fhir_patient_id

        if encounter_source:
            where_clause["encounterSource"] = encounter_source

        encounters = await prisma.encounter.find_many(
            where=where_clause,
            order={"createdAt": "desc"},
            skip=skip,
            take=page_size
        )

        total = await prisma.encounter.count(
            where=where_clause
        )

        return EncounterListResponse(
            encounters=[EncounterResponse(**e.model_dump()) for e in encounters],
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error("Error listing encounters", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve encounters"
        )


@router.get("/{encounter_id}", response_model=EncounterResponse)
async def get_encounter(
    encounter_id: str,
    user = Depends(get_current_user)
):
    """
    Get specific encounter details
    """
    try:
        encounter = await prisma.encounter.find_unique(
            where={"id": encounter_id}
        )

        if not encounter:
            raise HTTPException(
                status_code=404,
                detail="Encounter not found"
            )

        if encounter.userId != user.id and user.role != "ADMIN":
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view this encounter"
            )

        return EncounterResponse(**encounter.dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving encounter", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve encounter"
        )


@router.delete("/bulk-delete", status_code=http_status.HTTP_200_OK)
async def bulk_delete_encounters(
    request: BulkDeleteRequest,
    user = Depends(get_current_user)
):
    """
    Bulk delete encounters

    - Validates user ownership or admin role
    - Deletes encounters and associated data (PHI mappings, reports)
    - Uses CASCADE delete from database schema
    """
    try:
        encounter_ids = request.encounter_ids

        if not encounter_ids:
            raise HTTPException(
                status_code=400,
                detail="No encounter IDs provided"
            )

        logger.info(
            "Bulk delete request",
            user_id=user.id,
            encounter_count=len(encounter_ids)
        )

        # Verify ownership/permissions for each encounter
        encounters = await prisma.encounter.find_many(
            where={"id": {"in": encounter_ids}}
        )

        if len(encounters) != len(encounter_ids):
            raise HTTPException(
                status_code=404,
                detail="One or more encounters not found"
            )

        # Check permissions
        for encounter in encounters:
            if encounter.userId != user.id and user.role != "ADMIN":
                raise HTTPException(
                    status_code=403,
                    detail=f"Not authorized to delete encounter {encounter.id}"
                )

        # Delete encounters (CASCADE will handle related records)
        deleted = await prisma.encounter.delete_many(
            where={"id": {"in": encounter_ids}}
        )

        logger.info(
            "Bulk delete completed",
            user_id=user.id,
            deleted_count=deleted
        )

        return {
            "success": True,
            "deleted_count": deleted,
            "message": f"Successfully deleted {deleted} encounter(s)"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in bulk delete", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to delete encounters"
        )


@router.post("/check-duplicate")
async def check_duplicate_file(
    file: UploadFile = File(...),
    user = Depends(get_current_user)
):
    """
    Check if file has been previously uploaded (duplicate detection)

    Returns duplicate info if found, null otherwise
    """
    try:
        # Read file content and compute hash
        file_content = await file.read()
        file_hash = compute_file_hash(file_content)

        # Reset file pointer for potential subsequent reads
        await file.seek(0)

        # Check for duplicate
        duplicate_info = await duplicate_detection_service.check_duplicate(
            user_id=user.id,
            file_hash=file_hash
        )

        if duplicate_info:
            return {
                "is_duplicate": True,
                "duplicate_info": {
                    "file_id": duplicate_info["file_id"],
                    "encounter_id": duplicate_info["encounter_id"],
                    "original_filename": duplicate_info["original_filename"],
                    "upload_timestamp": duplicate_info["upload_timestamp"].isoformat(),
                    "file_size": duplicate_info["file_size"],
                }
            }
        else:
            return {
                "is_duplicate": False,
                "duplicate_info": None
            }

    except Exception as e:
        logger.error("Error checking duplicate", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to check for duplicates"
        )


@router.post("/batch/{batch_id}/status")
async def get_batch_status(
    batch_id: str,
    user = Depends(get_current_user)
):
    """
    Get status of all encounters in a bulk upload batch
    """
    try:
        # Get all encounters in this batch
        encounters = await prisma.encounter.find_many(
            where={
                "batchId": batch_id,
                "userId": user.id
            },
            include={
                "uploadedFiles": True,
                "report": True
            },
            order={"createdAt": "asc"}
        )

        if not encounters:
            raise HTTPException(
                status_code=404,
                detail="Batch not found or no encounters in batch"
            )

        # Calculate batch statistics
        total_files = len(encounters)
        completed = sum(1 for e in encounters if e.status == "COMPLETE")
        processing = sum(1 for e in encounters if e.status == "PROCESSING")
        failed = sum(1 for e in encounters if e.status == "FAILED")
        pending = sum(1 for e in encounters if e.status == "PENDING")

        # Build response with individual file statuses
        file_statuses = []
        for encounter in encounters:
            file_info = {
                "encounter_id": encounter.id,
                "status": encounter.status,
                "created_at": encounter.createdAt.isoformat(),
            }

            if encounter.uploadedFiles:
                file_info["filename"] = encounter.uploadedFiles[0].fileName
                file_info["file_size"] = encounter.uploadedFiles[0].fileSize

            if encounter.report:
                file_info["incremental_revenue"] = float(encounter.report.incrementalRevenue)
                file_info["suggested_codes_count"] = len(encounter.report.suggestedCodes) if encounter.report.suggestedCodes else 0

            if encounter.errorMessage:
                file_info["error_message"] = encounter.errorMessage

            file_statuses.append(file_info)

        return {
            "batch_id": batch_id,
            "total_files": total_files,
            "completed": completed,
            "processing": processing,
            "failed": failed,
            "pending": pending,
            "completion_percentage": round((completed / total_files) * 100, 1) if total_files > 0 else 0,
            "files": file_statuses
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting batch status", batch_id=batch_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve batch status"
        )
