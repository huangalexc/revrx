"""
Fee Schedule Management API
Handles payer fee schedule uploads and queries
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from typing import List, Optional
from datetime import datetime
import structlog
import csv
import io

from app.core.deps import get_current_user
from app.core.database import prisma
from app.schemas.fee_schedule import (
    FeeScheduleResponse,
    FeeScheduleRateResponse,
    FeeScheduleUploadResponse,
)

router = APIRouter(prefix="/fee-schedules", tags=["fee-schedules"])
logger = structlog.get_logger(__name__)


@router.post("/{payer_id}/upload", response_model=FeeScheduleUploadResponse)
async def upload_fee_schedule(
    payer_id: str,
    file: UploadFile = File(...),
    name: str = Form(...),
    effective_date: str = Form(...),  # ISO date string
    expiration_date: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    user = Depends(get_current_user)
):
    """
    Upload fee schedule CSV for a payer

    CSV Format:
    cpt_code,description,allowed_amount,facility_rate,non_facility_rate,requires_auth,modifier_25_rate,modifier_59_rate
    99213,Office visit 15 min,75.50,70.00,75.50,false,,,
    99214,Office visit 25 min,110.25,105.00,110.25,false,,,
    45378,Colonoscopy diagnostic,550.00,550.00,550.00,true,,,

    Flow:
    1. Verify payer exists
    2. Parse and validate CSV
    3. Create FeeSchedule record
    4. Bulk insert FeeScheduleRate records
    5. Deactivate previous schedules (if needed)
    """
    try:
        # Verify payer exists
        payer = await prisma.payer.find_unique(where={"id": payer_id})
        if not payer:
            raise HTTPException(status_code=404, detail="Payer not found")

        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be CSV")

        # Parse effective date
        from dateutil import parser as date_parser
        effective_dt = date_parser.parse(effective_date)
        expiration_dt = date_parser.parse(expiration_date) if expiration_date else None

        # Parse CSV
        content = await file.read()
        text_content = content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(text_content))

        # Validate CSV headers
        required_headers = {'cpt_code', 'allowed_amount'}
        if not required_headers.issubset(set(reader.fieldnames)):
            raise HTTPException(
                status_code=400,
                detail=f"CSV missing required columns: {required_headers}"
            )

        # Parse rates
        rates_data = []
        invalid_rows = []

        for row_num, row in enumerate(reader, start=2):
            try:
                cpt_code = row.get('cpt_code', '').strip()

                # Validate CPT code format (5 digits or 5 digits + modifier)
                if not cpt_code or len(cpt_code) < 5:
                    invalid_rows.append(f"Row {row_num}: Invalid CPT code '{cpt_code}'")
                    continue

                # Parse amounts (handle empty strings)
                def parse_float(value: str) -> Optional[float]:
                    if not value or value.strip() == '':
                        return None
                    try:
                        return float(value.strip())
                    except ValueError:
                        return None

                def parse_bool(value: str) -> bool:
                    if not value or value.strip() == '':
                        return False
                    return value.lower() in ('true', 't', 'yes', 'y', '1')

                allowed_amount = parse_float(row.get('allowed_amount', ''))
                if allowed_amount is None or allowed_amount <= 0:
                    invalid_rows.append(f"Row {row_num}: Invalid allowed_amount")
                    continue

                rate_data = {
                    'cptCode': cpt_code,
                    'cptDescription': row.get('description', '').strip() or None,
                    'allowedAmount': allowed_amount,
                    'facilityRate': parse_float(row.get('facility_rate', '')),
                    'nonFacilityRate': parse_float(row.get('non_facility_rate', '')),
                    'modifier25Rate': parse_float(row.get('modifier_25_rate', '')),
                    'modifier59Rate': parse_float(row.get('modifier_59_rate', '')),
                    'modifierTCRate': parse_float(row.get('modifier_tc_rate', '')),
                    'modifierPCRate': parse_float(row.get('modifier_pc_rate', '')),
                    'requiresAuth': parse_bool(row.get('requires_auth', 'false')),
                    'authCriteria': row.get('auth_criteria', '').strip() or None,
                    'workRVU': parse_float(row.get('work_rvu', '')),
                    'practiceRVU': parse_float(row.get('practice_rvu', '')),
                    'malpracticeRVU': parse_float(row.get('malpractice_rvu', '')),
                    'totalRVU': parse_float(row.get('total_rvu', '')),
                    'notes': row.get('notes', '').strip() or None,
                }

                rates_data.append(rate_data)

            except Exception as e:
                invalid_rows.append(f"Row {row_num}: {str(e)}")
                continue

        if not rates_data:
            raise HTTPException(
                status_code=400,
                detail="No valid rates found in CSV"
            )

        # Create fee schedule
        fee_schedule = await prisma.feeschedule.create(
            data={
                'payerId': payer_id,
                'name': name,
                'description': description,
                'effectiveDate': effective_dt,
                'expirationDate': expiration_dt,
                'isActive': True,
                'uploadedByUserId': user.id,
                'uploadedFileName': file.filename,
            }
        )

        logger.info(
            "Fee schedule created",
            fee_schedule_id=fee_schedule.id,
            payer_id=payer_id,
            user_id=user.id,
            rate_count=len(rates_data)
        )

        # Bulk insert rates
        for rate_data in rates_data:
            rate_data['feeScheduleId'] = fee_schedule.id

        await prisma.feeschedulerate.create_many(
            data=rates_data,
            skip_duplicates=True
        )

        logger.info(
            "Fee schedule rates created",
            fee_schedule_id=fee_schedule.id,
            rates_created=len(rates_data)
        )

        # Optionally deactivate previous schedules for this payer
        if expiration_dt is None:  # If no expiration, deactivate old ones
            await prisma.feeschedule.update_many(
                where={
                    'payerId': payer_id,
                    'id': {'not': fee_schedule.id},
                    'isActive': True
                },
                data={'isActive': False}
            )

        return FeeScheduleUploadResponse(
            fee_schedule_id=fee_schedule.id,
            payer_id=payer_id,
            name=name,
            rates_uploaded=len(rates_data),
            invalid_rows=invalid_rows,
            status="success",
            message=f"Successfully uploaded {len(rates_data)} rates"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error uploading fee schedule", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload fee schedule: {str(e)}"
        )


@router.get("/{payer_id}/schedules", response_model=List[FeeScheduleResponse])
async def list_fee_schedules(
    payer_id: str,
    active_only: bool = True,
    user = Depends(get_current_user)
):
    """
    List all fee schedules for a payer
    """
    try:
        where_clause = {'payerId': payer_id}
        if active_only:
            where_clause['isActive'] = True

        schedules = await prisma.feeschedule.find_many(
            where=where_clause,
            order={'effectiveDate': 'desc'},
            include={'payer': True}
        )

        return [FeeScheduleResponse.model_validate(s) for s in schedules]

    except Exception as e:
        logger.error("Error listing fee schedules", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list fee schedules")


@router.get("/{fee_schedule_id}/rates", response_model=List[FeeScheduleRateResponse])
async def get_fee_schedule_rates(
    fee_schedule_id: str,
    cpt_code: Optional[str] = None,
    user = Depends(get_current_user)
):
    """
    Get rates for a fee schedule
    Optionally filter by CPT code
    """
    try:
        where_clause = {'feeScheduleId': fee_schedule_id}
        if cpt_code:
            where_clause['cptCode'] = cpt_code

        rates = await prisma.feeschedulerate.find_many(
            where=where_clause,
            order={'cptCode': 'asc'}
        )

        return [FeeScheduleRateResponse.model_validate(r) for r in rates]

    except Exception as e:
        logger.error("Error getting fee schedule rates", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get rates")
