#!/usr/bin/env python3
"""
Retry a specific failed report to diagnose timeout issues
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment to load .env
os.environ.setdefault('ENV_FILE', str(Path(__file__).parent.parent / '.env'))

from app.core.database import prisma
from prisma import enums, Json
from app.services.report_processor import process_report_async
import structlog

logger = structlog.get_logger(__name__)

# The failed report and encounter
FAILED_REPORT_ID = "8b9f1292-f8c7-4d10-9bf7-fc2ce03be65e"
ENCOUNTER_ID = "ed57974f-3241-3504-9d33-fc7e36250759"


async def reset_and_retry_report():
    """Reset failed report to PENDING and retry processing"""

    await prisma.connect()

    try:
        print("="*80)
        print("RETRY FAILED REPORT TEST")
        print("="*80)
        print(f"Report ID: {FAILED_REPORT_ID}")
        print(f"Encounter ID: {ENCOUNTER_ID}")
        print()

        # Check if report exists
        report = await prisma.report.find_unique(
            where={"id": FAILED_REPORT_ID},
            include={"encounter": True}
        )

        if not report:
            print(f"❌ Report {FAILED_REPORT_ID} not found")
            return

        print(f"Current Status: {report.status}")
        print(f"Error Message: {report.errorMessage}")
        print(f"Retry Count: {report.retryCount}")
        print()

        # Reset report to PENDING
        print("Resetting report to PENDING...")
        await prisma.report.update(
            where={"id": FAILED_REPORT_ID},
            data={
                "status": enums.ReportStatus.PENDING,
                "progressPercent": 0,
                "currentStep": "pending",
                "errorMessage": None,
                "errorDetails": Json(None),
                "processingStartedAt": None,
                "processingCompletedAt": None,
            }
        )
        print("✅ Report reset to PENDING")
        print()

        # Process report
        print("Starting report processing...")
        print("="*80)
        start_time = datetime.now()

        try:
            await process_report_async(FAILED_REPORT_ID)

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            # Fetch final report status
            final_report = await prisma.report.find_unique(
                where={"id": FAILED_REPORT_ID}
            )

            print()
            print("="*80)
            print("PROCESSING COMPLETE")
            print("="*80)
            print(f"Status: {final_report.status}")
            print(f"Processing Time: {processing_time:.1f}s")
            print(f"Progress: {final_report.progressPercent}%")
            print(f"Current Step: {final_report.currentStep}")

            if final_report.status == enums.ReportStatus.COMPLETE:
                print(f"✅ SUCCESS!")
                print(f"Incremental Revenue: ${final_report.incrementalRevenue or 0:.2f}")
                print(f"Suggested Codes: {len(final_report.suggestedCodes) if final_report.suggestedCodes else 0}")
            elif final_report.status == enums.ReportStatus.FAILED:
                print(f"❌ FAILED")
                print(f"Error: {final_report.errorMessage}")

        except Exception as e:
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            print()
            print("="*80)
            print("PROCESSING FAILED WITH EXCEPTION")
            print("="*80)
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            print(f"Processing Time: {processing_time:.1f}s")

            import traceback
            print()
            print("Full Traceback:")
            print(traceback.format_exc())

    finally:
        await prisma.disconnect()


if __name__ == "__main__":
    asyncio.run(reset_and_retry_report())
