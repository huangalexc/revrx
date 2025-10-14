"""
Report API Endpoints
Handles report generation, export, and dashboard summaries
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Depends, Query, Response
from fastapi.responses import StreamingResponse, JSONResponse
import structlog
import csv
import json
from io import StringIO, BytesIO

from app.core.database import prisma
from app.core.deps import (
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    verify_resource_ownership,
)
from app.core.audit import create_audit_log
from app.services.report_generator import report_generator
from app.services.enhanced_report_generator import enhanced_report_generator
from app.services.task_queue import queue_report_processing
from app.services.dead_letter_queue import (
    get_failed_reports,
    retry_failed_report,
    bulk_retry_failed_reports,
    get_failure_statistics
)
from prisma.models import User
from prisma import enums, Json


logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/encounters/{encounter_id}")
async def get_encounter_report(
    encounter_id: str,
    format: str = Query("json", regex="^(json|yaml|html|pdf|csv)$"),
    include_phi: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get encounter report in specified format

    Args:
        encounter_id: Encounter ID
        format: Export format (json, yaml, html, pdf, csv)
        include_phi: Include PHI in report (admin only)

    Returns:
        Report in requested format
    """
    logger.info(
        "Fetching encounter report",
        encounter_id=encounter_id,
        format=format,
        include_phi=include_phi,
        user_id=current_user.id,
    )

    # Get encounter to verify ownership
    encounter = await prisma.encounter.find_unique(
        where={"id": encounter_id},
        include={"report": True},
    )

    if not encounter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Encounter not found",
        )

    # Verify ownership or admin
    if current_user.role != "ADMIN" and encounter.userId != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view your own reports.",
        )

    # Check if report exists
    if not encounter.report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not yet generated for this encounter. Please check back later.",
        )

    # Check report status and handle accordingly
    if encounter.report.status == enums.ReportStatus.PENDING:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "PENDING",
                "message": "Report generation is queued",
                "reportId": encounter.report.id,
                "progressPercent": encounter.report.progressPercent,
                "currentStep": encounter.report.currentStep,
            }
        )

    if encounter.report.status == enums.ReportStatus.PROCESSING:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "PROCESSING",
                "message": "Report is being generated",
                "reportId": encounter.report.id,
                "progressPercent": encounter.report.progressPercent,
                "currentStep": encounter.report.currentStep,
                "processingStartedAt": encounter.report.processingStartedAt.isoformat() if encounter.report.processingStartedAt else None,
            }
        )

    if encounter.report.status == enums.ReportStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {encounter.report.errorMessage or 'Unknown error'}",
        )

    # Only admins can include PHI
    if include_phi and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view reports with PHI",
        )

    # Generate report data
    try:
        report_data = await report_generator.generate_report(
            encounter_id=encounter_id,
            include_phi=include_phi,
            user_id=current_user.id,
        )
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"\n\n{'='*80}\nERROR GENERATING REPORT for {encounter_id}:\n{tb}\n{'='*80}\n\n")
        logger.error("Failed to generate report", encounter_id=encounter_id, error=str(e), error_type=type(e).__name__, traceback=tb)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )

    # Log report access
    await create_audit_log(
        action="REPORT_ACCESSED",
        user_id=current_user.id,
        resource_type="Report",
        resource_id=encounter.report.id,
        metadata={
            "format": format,
            "include_phi": include_phi,
        },
    )

    # Return in requested format
    if format == "json":
        return JSONResponse(content=report_data)

    elif format == "yaml":
        yaml_content = report_generator.generate_yaml(report_data)
        return Response(
            content=yaml_content,
            media_type="application/x-yaml",
            headers={
                "Content-Disposition": f"attachment; filename=report_{encounter_id}.yaml"
            },
        )

    elif format == "html":
        html_content = report_generator.generate_html(report_data)
        return Response(
            content=html_content,
            media_type="text/html",
        )

    elif format == "pdf":
        # Use enhanced generator for PDF with new features
        html_content = enhanced_report_generator.generate_enhanced_html(report_data)

        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html_content).write_pdf()
        except ImportError:
            logger.error("WeasyPrint not installed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF generation not available. WeasyPrint not installed."
            )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=report_{encounter_id}.pdf"
            },
        )

    elif format == "csv":
        # Generate CSV with all enhanced features
        csv_content = enhanced_report_generator.generate_csv(report_data)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=report_{encounter_id}.csv"
            },
        )


@router.get("/summary")
async def get_reports_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get summary dashboard data

    Args:
        days: Number of days to look back (1-365)

    Returns:
        Summary statistics and chart data
    """
    logger.info(
        "Fetching reports summary",
        days=days,
        user_id=current_user.id,
    )

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Build query filters
    where_clause = {
        "createdAt": {"gte": start_date, "lte": end_date},
        "status": "COMPLETE",
    }

    # Non-admins can only see their own data
    if current_user.role != "ADMIN":
        where_clause["userId"] = current_user.id

    # Get encounters with reports
    encounters = await prisma.encounter.find_many(
        where=where_clause,
        include={"report": True},
        order={"createdAt": "desc"},
    )

    # Calculate summary statistics
    total_encounters = len(encounters)
    total_revenue = sum(
        float(e.report.incrementalRevenue) for e in encounters if e.report
    )
    avg_revenue = total_revenue / total_encounters if total_encounters > 0 else 0

    # Calculate processing time stats
    processing_times = [e.processingTime for e in encounters if e.processingTime]
    avg_processing_time = (
        sum(processing_times) / len(processing_times) if processing_times else 0
    )

    # Count code opportunities
    total_new_codes = 0
    total_upgrade_opportunities = 0

    for encounter in encounters:
        if encounter.report and encounter.report.suggestedCodes:
            for code in encounter.report.suggestedCodes:
                if isinstance(code, dict):
                    comp_type = code.get("comparison_type")
                    if comp_type == "new":
                        total_new_codes += 1
                    elif comp_type == "upgrade":
                        total_upgrade_opportunities += 1

    # Build time series data for chart
    chart_data = _build_chart_data(encounters, days)

    summary = {
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": days,
        },
        "overview": {
            "total_encounters": total_encounters,
            "total_incremental_revenue": round(total_revenue, 2),
            "average_revenue_per_encounter": round(avg_revenue, 2),
            "average_processing_time_ms": round(avg_processing_time, 0),
        },
        "opportunities": {
            "total_new_codes": total_new_codes,
            "total_upgrade_opportunities": total_upgrade_opportunities,
            "total_opportunities": total_new_codes + total_upgrade_opportunities,
        },
        "chart_data": chart_data,
    }

    # Log summary access
    await create_audit_log(
        action="SUMMARY_ACCESSED",
        user_id=current_user.id,
        resource_type="Report",
        resource_id="summary",
        metadata={"days": days, "total_encounters": total_encounters},
    )

    return summary


@router.get("/summary/export")
async def export_summary_csv(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
):
    """
    Export summary data as CSV

    Args:
        days: Number of days to look back

    Returns:
        CSV file with summary data
    """
    logger.info("Exporting summary CSV", days=days, user_id=current_user.id)

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Build query filters
    where_clause = {
        "createdAt": {"gte": start_date, "lte": end_date},
        "status": "COMPLETE",
    }

    if current_user.role != "ADMIN":
        where_clause["userId"] = current_user.id

    # Get encounters with reports
    encounters = await prisma.encounter.find_many(
        where=where_clause,
        include={"report": True, "user": True},
        order={"createdAt": "desc"},
    )

    # Build CSV
    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Encounter ID",
        "Date",
        "User Email",
        "Status",
        "Processing Time (ms)",
        "Incremental Revenue",
        "New Codes",
        "Upgrade Opportunities",
        "Confidence Score",
    ])

    # Data rows
    for encounter in encounters:
        new_codes = 0
        upgrades = 0

        if encounter.report and encounter.report.suggestedCodes:
            for code in encounter.report.suggestedCodes:
                if isinstance(code, dict):
                    comp_type = code.get("comparison_type")
                    if comp_type == "new":
                        new_codes += 1
                    elif comp_type == "upgrade":
                        upgrades += 1

        writer.writerow([
            encounter.id,
            encounter.createdAt.isoformat(),
            encounter.user.email if current_user.role == "ADMIN" else "***",
            encounter.status,
            encounter.processingTime or 0,
            float(encounter.report.incrementalRevenue) if encounter.report else 0,
            new_codes,
            upgrades,
            float(encounter.report.confidenceScore) if encounter.report else 0,
        ])

    # Log export
    await create_audit_log(
        action="SUMMARY_EXPORTED_CSV",
        user_id=current_user.id,
        resource_type="Report",
        resource_id="summary",
        metadata={"days": days, "row_count": len(encounters)},
    )

    # Return CSV
    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=coding_review_summary_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        },
    )


@router.get("/encounters/{encounter_id}/summary")
async def get_encounter_summary(
    encounter_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get quick summary for a single encounter

    Args:
        encounter_id: Encounter ID

    Returns:
        Encounter summary with key metrics
    """
    # Get encounter with report
    encounter = await prisma.encounter.find_unique(
        where={"id": encounter_id},
        include={"report": True},
    )

    if not encounter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Encounter not found",
        )

    # Verify ownership
    if current_user.role != "ADMIN" and encounter.userId != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Build summary
    new_codes = 0
    upgrades = 0

    if encounter.report and encounter.report.suggestedCodes:
        for code in encounter.report.suggestedCodes:
            if isinstance(code, dict):
                comp_type = code.get("comparison_type")
                if comp_type == "new":
                    new_codes += 1
                elif comp_type == "upgrade":
                    upgrades += 1

    summary = {
        "encounter_id": encounter.id,
        "status": encounter.status,
        "created_at": encounter.createdAt.isoformat(),
        "processing_time_ms": encounter.processingTime,
        "incremental_revenue": float(encounter.report.incrementalRevenue)
        if encounter.report
        else 0,
        "new_codes_count": new_codes,
        "upgrade_opportunities_count": upgrades,
        "confidence_score": float(encounter.report.confidenceScore)
        if encounter.report
        else 0,
    }

    return summary


@router.get("/summary/code-categories")
async def get_top_code_categories(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of categories to return"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get top code categories by revenue

    Args:
        days: Number of days to look back (1-365)
        limit: Maximum number of categories to return

    Returns:
        List of code categories with revenue and count
    """
    logger.info(
        "Fetching top code categories",
        days=days,
        limit=limit,
        user_id=current_user.id,
    )

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Build query filters
    where_clause = {
        "createdAt": {"gte": start_date, "lte": end_date},
        "status": "COMPLETE",
    }

    # Non-admins can only see their own data
    if current_user.role != "ADMIN":
        where_clause["userId"] = current_user.id

    # Get encounters with reports
    encounters = await prisma.encounter.find_many(
        where=where_clause,
        include={"report": True},
        order={"createdAt": "desc"},
    )

    # Aggregate code categories
    category_stats = {}

    for encounter in encounters:
        if encounter.report and encounter.report.suggestedCodes:
            for code in encounter.report.suggestedCodes:
                if isinstance(code, dict):
                    code_value = code.get("code", "")
                    revenue = float(code.get("incremental_revenue", 0))

                    # Determine category based on CPT code
                    category = _categorize_cpt_code(code_value)

                    if category not in category_stats:
                        category_stats[category] = {
                            "category": category,
                            "revenue": 0,
                            "count": 0,
                            "codes": set(),
                        }

                    category_stats[category]["revenue"] += revenue
                    category_stats[category]["count"] += 1
                    category_stats[category]["codes"].add(code_value)

    # Convert to list and sort by revenue
    categories = []
    for cat_name, stats in category_stats.items():
        categories.append({
            "category": cat_name,
            "revenue": round(stats["revenue"], 2),
            "count": stats["count"],
            "unique_codes": len(stats["codes"]),
        })

    categories.sort(key=lambda x: x["revenue"], reverse=True)

    # Return top N categories
    return categories[:limit]


def _categorize_cpt_code(code: str) -> str:
    """
    Categorize a CPT code into a category

    CPT Code Ranges:
    - 99201-99499: Office and Other Outpatient Services
    - 90000-99000: Medicine (various)
    - 70000-79999: Radiology
    - 80000-89999: Pathology and Laboratory
    - 10000-69999: Surgery
    """
    if not code:
        return "Other"

    # Extract numeric portion
    numeric_code = ''.join(filter(str.isdigit, code))
    if not numeric_code:
        return "Other"

    code_num = int(numeric_code)

    # Categorize based on CPT ranges
    if 99201 <= code_num <= 99215:
        return "Office Visits"
    elif 99217 <= code_num <= 99239:
        return "Hospital Care"
    elif 99241 <= code_num <= 99255:
        return "Consultations"
    elif 99281 <= code_num <= 99288:
        return "Emergency Department"
    elif 99291 <= code_num <= 99292:
        return "Critical Care"
    elif 99304 <= code_num <= 99318:
        return "Nursing Facility"
    elif 99324 <= code_num <= 99337:
        return "Home Services"
    elif 99341 <= code_num <= 99350:
        return "Home Visits"
    elif 99354 <= code_num <= 99360:
        return "Prolonged Services"
    elif 99381 <= code_num <= 99429:
        return "Preventive Medicine"
    elif 99441 <= code_num <= 99449:
        return "Telehealth"
    elif 99450 <= code_num <= 99456:
        return "Special Services"
    elif 99460 <= code_num <= 99480:
        return "Newborn Care"
    elif 99483 <= code_num <= 99499:
        return "Care Management"
    elif 90000 <= code_num <= 99000:
        return "Medicine Services"
    elif 70000 <= code_num <= 79999:
        return "Radiology"
    elif 80000 <= code_num <= 89999:
        return "Laboratory"
    elif 10000 <= code_num <= 19999:
        return "Integumentary Procedures"
    elif 20000 <= code_num <= 29999:
        return "Musculoskeletal Procedures"
    elif 30000 <= code_num <= 39999:
        return "Respiratory Procedures"
    elif 40000 <= code_num <= 49999:
        return "Digestive Procedures"
    elif 50000 <= code_num <= 59999:
        return "Urinary Procedures"
    elif 60000 <= code_num <= 69999:
        return "Surgical Procedures"
    else:
        return "Other"


def _build_chart_data(encounters: list, days: int) -> dict:
    """
    Build time series data for charts

    Returns data grouped by day for revenue and encounter counts
    """
    # Initialize daily buckets
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    daily_data = {}
    current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    while current <= end_date:
        date_key = current.strftime("%Y-%m-%d")
        daily_data[date_key] = {
            "date": date_key,
            "encounter_count": 0,
            "revenue": 0,
            "new_codes": 0,
            "upgrades": 0,
        }
        current += timedelta(days=1)

    # Aggregate encounter data
    for encounter in encounters:
        date_key = encounter.createdAt.strftime("%Y-%m-%d")

        if date_key in daily_data:
            daily_data[date_key]["encounter_count"] += 1

            if encounter.report:
                daily_data[date_key]["revenue"] += float(
                    encounter.report.incrementalRevenue
                )

                if encounter.report.suggestedCodes:
                    for code in encounter.report.suggestedCodes:
                        if isinstance(code, dict):
                            comp_type = code.get("comparison_type")
                            if comp_type == "new":
                                daily_data[date_key]["new_codes"] += 1
                            elif comp_type == "upgrade":
                                daily_data[date_key]["upgrades"] += 1

    # Convert to sorted list
    chart_data = {
        "labels": sorted(daily_data.keys()),
        "datasets": {
            "encounter_counts": [
                daily_data[date]["encounter_count"]
                for date in sorted(daily_data.keys())
            ],
            "revenue": [
                round(daily_data[date]["revenue"], 2)
                for date in sorted(daily_data.keys())
            ],
            "new_codes": [
                daily_data[date]["new_codes"] for date in sorted(daily_data.keys())
            ],
            "upgrades": [
                daily_data[date]["upgrades"] for date in sorted(daily_data.keys())
            ],
        },
    }

    return chart_data


# ================================================================
# ASYNC PROCESSING ENDPOINTS
# ================================================================

@router.post("/encounters/{encounter_id}/reports", status_code=status.HTTP_202_ACCEPTED)
async def trigger_report_generation(
    encounter_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Trigger asynchronous report generation for an encounter

    Returns 202 Accepted immediately and processes report in background.
    Use GET /reports/{report_id}/status to check progress.

    Args:
        encounter_id: Encounter ID

    Returns:
        202 Accepted with report ID and status
    """
    logger.info(
        "Triggering async report generation",
        encounter_id=encounter_id,
        user_id=current_user.id,
    )

    # Verify encounter exists and user has access
    encounter = await prisma.encounter.find_unique(
        where={"id": encounter_id},
        include={"report": True},
    )

    if not encounter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Encounter not found",
        )

    # Verify ownership
    if current_user.role != "ADMIN" and encounter.userId != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Check if report already exists
    if encounter.report:
        # If report exists and is complete, return existing report ID
        if encounter.report.status == enums.ReportStatus.COMPLETE:
            return {
                "reportId": encounter.report.id,
                "status": "COMPLETE",
                "message": "Report already exists and is complete",
            }

        # If report is pending or processing, return existing report ID
        if encounter.report.status in [enums.ReportStatus.PENDING, enums.ReportStatus.PROCESSING]:
            return {
                "reportId": encounter.report.id,
                "status": encounter.report.status,
                "message": "Report generation already in progress",
                "progressPercent": encounter.report.progressPercent,
                "currentStep": encounter.report.currentStep,
            }

        # If report failed, allow retry by creating new report
        if encounter.report.status == enums.ReportStatus.FAILED:
            # Delete failed report
            await prisma.report.delete(where={"id": encounter.report.id})

    # Create new report with PENDING status
    report = await prisma.report.create(
        data={
            "encounterId": encounter_id,
            "status": enums.ReportStatus.PENDING,
            "progressPercent": 0,
            "currentStep": "queued",
            "billedCodes": Json([]),
            "suggestedCodes": Json([]),
            "additionalCodes": Json([]),
            "extractedIcd10Codes": Json([]),
            "extractedSnomedCodes": Json([]),
            "cptSuggestions": Json([]),
            "incrementalRevenue": 0.0,
            "aiModel": "gpt-4o-mini",
        }
    )

    # Queue for background processing
    queue_report_processing(report.id)

    # Log audit
    await create_audit_log(
        action="REPORT_GENERATION_TRIGGERED",
        user_id=current_user.id,
        resource_type="Report",
        resource_id=report.id,
        metadata={"encounter_id": encounter_id},
    )

    logger.info(
        "Report generation queued",
        encounter_id=encounter_id,
        report_id=report.id,
        user_id=current_user.id,
    )

    return {
        "reportId": report.id,
        "status": "PENDING",
        "message": "Report generation queued",
        "progressPercent": 0,
        "currentStep": "queued",
    }


@router.get("/{report_id}/status")
async def get_report_status(
    report_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get current status of report generation

    Args:
        report_id: Report ID

    Returns:
        Status, progress, and timing information
    """
    # Get report with encounter for ownership verification
    report = await prisma.report.find_unique(
        where={"id": report_id},
        include={"encounter": True},
    )

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    # Verify ownership
    if current_user.role != "ADMIN" and report.encounter.userId != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Calculate estimated time remaining
    estimated_time_remaining_ms = None
    if report.status == enums.ReportStatus.PROCESSING and report.processingStartedAt:
        elapsed_ms = (datetime.utcnow() - report.processingStartedAt).total_seconds() * 1000

        # Estimate total time based on progress (assume average 30s total)
        if report.progressPercent and report.progressPercent > 0:
            estimated_total_ms = (elapsed_ms / report.progressPercent) * 100
            estimated_time_remaining_ms = max(0, int(estimated_total_ms - elapsed_ms))

    response = {
        "reportId": report.id,
        "encounterId": report.encounterId,
        "status": report.status,
        "progressPercent": report.progressPercent,
        "currentStep": report.currentStep,
    }

    # Add timing information
    if report.processingStartedAt:
        response["processingStartedAt"] = report.processingStartedAt.isoformat()

    if report.status == enums.ReportStatus.PROCESSING:
        response["processingTimeMs"] = int((datetime.utcnow() - report.processingStartedAt).total_seconds() * 1000)
        if estimated_time_remaining_ms is not None:
            response["estimatedTimeRemainingMs"] = estimated_time_remaining_ms

    if report.processingCompletedAt:
        response["processingCompletedAt"] = report.processingCompletedAt.isoformat()

    if report.processingTimeMs:
        response["processingTimeMs"] = report.processingTimeMs

    # Add error information if failed
    if report.status == enums.ReportStatus.FAILED:
        response["errorMessage"] = report.errorMessage
        if report.errorDetails:
            response["errorDetails"] = report.errorDetails
        response["retryCount"] = report.retryCount

    return response


@router.get("/batch/{batch_id}/status")
async def get_batch_status(
    batch_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get aggregated status for a batch of reports

    Note: This is a placeholder for future batch upload feature.
    Currently returns status for all user's reports.

    Args:
        batch_id: Batch ID (currently unused, returns all user reports)

    Returns:
        Aggregated status with counts and progress
    """
    # Build query - for now, get all reports for user
    # In future, this would filter by batch_id
    where_clause = {}

    if current_user.role != "ADMIN":
        # Get user's encounters
        user_encounters = await prisma.encounter.find_many(
            where={"userId": current_user.id},
            select={"id": True},
        )
        encounter_ids = [e.id for e in user_encounters]
        where_clause["encounterId"] = {"in": encounter_ids}

    # Get all reports
    reports = await prisma.report.find_many(where=where_clause)

    # Calculate aggregated status
    status_counts = {
        "PENDING": 0,
        "PROCESSING": 0,
        "COMPLETE": 0,
        "FAILED": 0,
    }

    total_progress = 0
    processing_reports = []

    for report in reports:
        status_counts[report.status] += 1

        if report.status == enums.ReportStatus.PROCESSING:
            total_progress += (report.progressPercent or 0)
            processing_reports.append({
                "reportId": report.id,
                "encounterId": report.encounterId,
                "progressPercent": report.progressPercent,
                "currentStep": report.currentStep,
            })

    # Calculate overall progress
    total_reports = len(reports)
    completed_reports = status_counts["COMPLETE"]
    failed_reports = status_counts["FAILED"]
    processing_count = status_counts["PROCESSING"]

    if total_reports > 0:
        # Weight: completed = 100%, processing = current%, failed = 0%, pending = 0%
        overall_progress = (
            (completed_reports * 100 + total_progress) / total_reports
        )
    else:
        overall_progress = 0

    return {
        "batchId": batch_id,
        "totalReports": total_reports,
        "statusCounts": status_counts,
        "overallProgressPercent": round(overall_progress, 1),
        "processingReports": processing_reports,
        "completedReports": completed_reports,
        "failedReports": failed_reports,
    }


# ================================================================
# DEAD LETTER QUEUE ENDPOINTS (Admin Only)
# ================================================================

@router.get("/failed", dependencies=[Depends(get_current_admin_user)])
async def get_failed_reports_endpoint(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    min_retry_count: int = Query(3, ge=0),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Get all permanently failed reports (admin only)

    Returns reports that have exceeded retry limits for debugging.

    Args:
        limit: Maximum number of reports to return (1-100)
        offset: Pagination offset
        min_retry_count: Minimum retry count to consider "permanently failed"

    Returns:
        List of failed reports with error details
    """
    logger.info(
        "Fetching failed reports",
        limit=limit,
        offset=offset,
        min_retry_count=min_retry_count,
        user_id=current_user.id
    )

    result = await get_failed_reports(
        limit=limit,
        offset=offset,
        min_retry_count=min_retry_count
    )

    # Log audit
    await create_audit_log(
        action="FAILED_REPORTS_ACCESSED",
        user_id=current_user.id,
        resource_type="Report",
        resource_id="failed_queue",
        metadata={"total_count": result["total_count"]}
    )

    return result


@router.post("/{report_id}/retry", dependencies=[Depends(get_current_admin_user)])
async def retry_failed_report_endpoint(
    report_id: str,
    force: bool = Query(False, description="Force retry even if retry count is high"),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Retry a failed report (admin only)

    Resets the report status to PENDING and queues for processing.

    Args:
        report_id: Report ID to retry
        force: Force retry even if retry count exceeds limits

    Returns:
        Retry status
    """
    logger.info(
        "Retrying failed report",
        report_id=report_id,
        force=force,
        user_id=current_user.id
    )

    try:
        result = await retry_failed_report(report_id, force=force)

        # Log audit
        await create_audit_log(
            action="FAILED_REPORT_RETRIED",
            user_id=current_user.id,
            resource_type="Report",
            resource_id=report_id,
            metadata={"force": force, "previous_retry_count": result["previous_retry_count"]}
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/failed/bulk-retry", dependencies=[Depends(get_current_admin_user)])
async def bulk_retry_failed_reports_endpoint(
    min_retry_count: int = Query(3, ge=0),
    max_age_hours: Optional[int] = Query(None, ge=1, le=168),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Bulk retry multiple failed reports (admin only)

    Retries multiple failed reports matching the criteria.

    Args:
        min_retry_count: Minimum retry count to include
        max_age_hours: Only retry reports failed within this many hours (1-168)
        limit: Maximum number of reports to retry (1-50)

    Returns:
        Bulk retry results
    """
    logger.info(
        "Bulk retrying failed reports",
        min_retry_count=min_retry_count,
        max_age_hours=max_age_hours,
        limit=limit,
        user_id=current_user.id
    )

    result = await bulk_retry_failed_reports(
        min_retry_count=min_retry_count,
        max_age_hours=max_age_hours,
        limit=limit
    )

    # Log audit
    await create_audit_log(
        action="BULK_RETRY_EXECUTED",
        user_id=current_user.id,
        resource_type="Report",
        resource_id="bulk_retry",
        metadata={
            "total_attempted": result["total_attempted"],
            "successful": result["successful"],
            "failed": result["failed"]
        }
    )

    return result


@router.get("/failed/statistics", dependencies=[Depends(get_current_admin_user)])
async def get_failure_statistics_endpoint(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Get failure statistics (admin only)

    Returns analysis of report failures over time.

    Args:
        days: Number of days to analyze (1-90)

    Returns:
        Failure statistics and patterns
    """
    logger.info(
        "Fetching failure statistics",
        days=days,
        user_id=current_user.id
    )

    result = await get_failure_statistics(days=days)

    # Log audit
    await create_audit_log(
        action="FAILURE_STATISTICS_ACCESSED",
        user_id=current_user.id,
        resource_type="Report",
        resource_id="statistics",
        metadata={"days": days, "total_failures": result["total_failures"]}
    )

    return result
