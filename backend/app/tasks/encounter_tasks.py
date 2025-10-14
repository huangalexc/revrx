"""
Celery Tasks for Encounter Processing
Handles asynchronous AI analysis of clinical notes
"""

from datetime import datetime
from typing import Dict, Any
import structlog
import asyncio
import json

from app.core.celery_app import celery_app
from app.core.database import prisma
from app.services.phi_handler import phi_handler
from app.services.openai_service import openai_service
from app.services.code_comparison import code_comparison_engine


logger = structlog.get_logger(__name__)


@celery_app.task(
    name="process_encounter",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_encounter_task(self, encounter_id: str) -> Dict[str, Any]:
    """
    Process encounter asynchronously

    Steps:
    1. Get encounter and extract clinical text
    2. De-identify PHI
    3. Analyze with AI
    4. Compare codes
    5. Generate report
    6. Update encounter status

    Args:
        encounter_id: Encounter ID to process

    Returns:
        Processing result dictionary
    """
    logger.info("Starting encounter processing task", encounter_id=encounter_id)

    try:
        # Run async processing in sync context
        result = asyncio.run(_process_encounter_async(encounter_id))

        logger.info(
            "Encounter processing completed",
            encounter_id=encounter_id,
            processing_time_ms=result.get("processing_time_ms"),
        )

        return result

    except Exception as e:
        logger.error(
            "Encounter processing failed",
            encounter_id=encounter_id,
            error=str(e),
            attempt=self.request.retries + 1,
        )

        # Update encounter status to failed
        asyncio.run(_update_encounter_failed(encounter_id, str(e)))

        # Retry if not max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        raise


async def _process_encounter_async(encounter_id: str) -> Dict[str, Any]:
    """
    Async processing logic

    This is the main processing pipeline
    """
    start_time = datetime.utcnow()

    # Connect to database
    await prisma.connect()

    try:
        # 1. Get encounter with files
        encounter = await prisma.encounter.find_unique(
            where={"id": encounter_id},
            include={
                "uploadedFiles": True,
                "user": True,
            },
        )

        if not encounter:
            raise ValueError(f"Encounter {encounter_id} not found")

        # Update status to processing
        await prisma.encounter.update(
            where={"id": encounter_id},
            data={
                "status": "PROCESSING",
                "processingStartedAt": start_time,
            },
        )

        # 2. Get de-identified text (PHI should already be processed during upload)
        phi_result = await phi_handler.retrieve_phi_mapping(encounter_id)

        if not phi_result:
            raise ValueError(f"PHI mapping not found for encounter {encounter_id}")

        deidentified_text = phi_result.deidentified_text

        # 3. Get billed codes from report or uploaded codes
        # For now, parse from encounter metadata or use empty list
        billed_codes = []  # TODO: Extract from uploaded billing codes file

        # 4. Analyze with AI (using 2-prompt approach for reliability)
        logger.info("Analyzing with AI", encounter_id=encounter_id)
        ai_result = await openai_service.analyze_clinical_note_v2(
            clinical_note=deidentified_text,
            billed_codes=billed_codes,
        )

        # 5. Compare codes and calculate revenue
        logger.info("Comparing codes", encounter_id=encounter_id)
        comparison_result = code_comparison_engine.compare_codes(
            billed_codes=billed_codes,
            ai_result=ai_result,
        )

        # 6. Create/update report
        logger.info("Creating report", encounter_id=encounter_id)

        # Check if report exists
        existing_report = await prisma.report.find_unique(
            where={"encounterId": encounter_id}
        )

        # Prepare full AI analysis for reportJson
        full_analysis = {
            "billed_codes": [c.to_dict() for c in ai_result.billed_codes],
            "suggested_codes": [c.to_dict() for c in ai_result.additional_codes],
            "denial_risks": ai_result.denial_risks,
            "missing_documentation": ai_result.missing_documentation,
            "rvu_analysis": ai_result.rvu_analysis,
            "modifier_suggestions": ai_result.modifier_suggestions,
            "uncaptured_services": ai_result.uncaptured_services,
            "audit_metadata": ai_result.audit_metadata,
            "incremental_revenue": comparison_result.incremental_revenue,
            "ai_model": ai_result.model_used,
            "confidence_score": comparison_result.confidence_score,
            "processing_time_ms": ai_result.processing_time_ms,
            "tokens_used": ai_result.tokens_used,
            "cost_usd": ai_result.cost_usd,
        }

        report_data = {
            "billedCodes": json.dumps([c.to_dict() for c in ai_result.billed_codes]),
            "suggestedCodes": json.dumps([c.to_dict() for c in ai_result.additional_codes]),
            "incrementalRevenue": comparison_result.incremental_revenue,
            "aiModel": ai_result.model_used,
            "confidenceScore": comparison_result.confidence_score,
            "reportJson": json.dumps(full_analysis),
        }

        if existing_report:
            report = await prisma.report.update(
                where={"encounterId": encounter_id},
                data=report_data,
            )
        else:
            report = await prisma.report.create(
                data={
                    "encounterId": encounter_id,
                    **report_data,
                }
            )

        # 7. Update encounter status to completed
        processing_completed_at = datetime.utcnow()
        processing_time_ms = int(
            (processing_completed_at - start_time).total_seconds() * 1000
        )

        await prisma.encounter.update(
            where={"id": encounter_id},
            data={
                "status": "COMPLETE",
                "processingCompletedAt": processing_completed_at,
                "processingTime": processing_time_ms,
            },
        )

        # 8. Log completion
        # TODO: Fix AuditLog table - not created in database yet
        logger.info(
            "Encounter processing completed",
            encounter_id=encounter_id,
            processing_time_ms=processing_time_ms,
            ai_tokens=ai_result.tokens_used,
            ai_cost=ai_result.cost_usd,
            incremental_revenue=comparison_result.incremental_revenue,
            new_codes=comparison_result.new_codes_count,
        )

        return {
            "encounter_id": encounter_id,
            "status": "completed",
            "processing_time_ms": processing_time_ms,
            "incremental_revenue": comparison_result.incremental_revenue,
            "new_codes_count": comparison_result.new_codes_count,
            "tokens_used": ai_result.tokens_used,
            "cost_usd": ai_result.cost_usd,
        }

    finally:
        await prisma.disconnect()


async def _update_encounter_failed(encounter_id: str, error_message: str):
    """Update encounter status to failed"""
    await prisma.connect()

    try:
        encounter = await prisma.encounter.find_unique(where={"id": encounter_id})

        if encounter:
            await prisma.encounter.update(
                where={"id": encounter_id},
                data={
                    "status": "FAILED",
                    "errorMessage": error_message,
                    "retryCount": encounter.retryCount + 1,
                },
            )

            # Log failure
            # TODO: Fix AuditLog table - not created in database yet
            logger.error(
                "Encounter processing failed - logged for audit",
                encounter_id=encounter_id,
                user_id=encounter.userId,
                error=error_message,
                retry_count=encounter.retryCount + 1,
            )

    finally:
        await prisma.disconnect()


@celery_app.task(name="retry_failed_encounter")
def retry_failed_encounter_task(encounter_id: str) -> Dict[str, Any]:
    """
    Retry a failed encounter

    Args:
        encounter_id: Encounter ID to retry

    Returns:
        Result from process_encounter_task
    """
    logger.info("Retrying failed encounter", encounter_id=encounter_id)

    # Reset encounter status
    asyncio.run(_reset_encounter_status(encounter_id))

    # Reprocess
    return process_encounter_task(encounter_id)


async def _reset_encounter_status(encounter_id: str):
    """Reset encounter status to pending for retry"""
    await prisma.connect()

    try:
        await prisma.encounter.update(
            where={"id": encounter_id},
            data={
                "status": "PENDING",
                "errorMessage": None,
            },
        )
    finally:
        await prisma.disconnect()
