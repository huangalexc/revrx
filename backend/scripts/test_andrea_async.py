#!/usr/bin/env python3
"""
Test Async Report Processing with Andrea's Encounters

This script tests the async report processing system by:
1. Creating PENDING reports for 10 encounters
2. Queuing them for async processing
3. Monitoring progress in real-time
4. Displaying final results
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment to load .env
os.environ.setdefault('ENV_FILE', str(Path(__file__).parent.parent / '.env'))

from app.core.database import prisma
from prisma import enums, Json
from app.services.task_queue import queue_report_processing, get_queue_stats
import structlog

logger = structlog.get_logger(__name__)

# Andrea's encounters
ANDREA_ENCOUNTERS = [
    ('77300ca5-921f-f1ac-662d-a21722ab9648', '1946-07-10', 'Well child visit (procedure)'),
    ('77300ca5-921f-f1ac-be94-7fa1e7365e67', '1947-07-16', 'General examination of patient (procedure)'),
    ('77300ca5-921f-f1ac-7d21-0ccd50ccb2fe', '1951-07-25', 'General examination of patient (procedure)'),
    ('77300ca5-921f-f1ac-a02a-cde162cbb602', '1954-06-26', 'Encounter for problem (procedure)'),
    ('77300ca5-921f-f1ac-a797-f22e5f0d4241', '1954-07-09', 'Encounter for problem (procedure)'),
    ('77300ca5-921f-f1ac-912f-74df401ff567', '1957-06-27', 'Prenatal visit (regime/therapy)'),
    ('77300ca5-921f-f1ac-9740-abe984073501', '1966-08-10', 'General examination of patient (procedure)'),
    ('77300ca5-921f-f1ac-c653-d0d154515f09', '1969-05-28', 'General examination of patient (procedure)'),
    ('77300ca5-921f-f1ac-c2df-463bf548cecb', '1971-06-02', 'General examination of patient (procedure)'),
    ('77300ca5-921f-f1ac-0229-0a3dbd46d39d', '1971-06-23', 'Follow-up encounter (procedure)'),
]


async def create_pending_report(encounter_id: str) -> Dict:
    """
    Create a PENDING report and queue for async processing

    Returns:
        dict: Report creation result with report_id
    """
    try:
        # Check if encounter exists
        encounter = await prisma.encounter.find_unique(
            where={'id': encounter_id}
        )

        if not encounter:
            return {
                'success': False,
                'encounter_id': encounter_id,
                'error': 'Encounter not found in database'
            }

        # Check if report already exists
        existing_report = await prisma.report.find_first(
            where={'encounterId': encounter_id}
        )

        if existing_report:
            logger.info(f"Report already exists for encounter {encounter_id[:8]}, using existing report")

            # If it's already completed or failed, update to PENDING to reprocess
            if existing_report.status in [enums.ReportStatus.COMPLETE, enums.ReportStatus.FAILED]:
                await prisma.report.update(
                    where={'id': existing_report.id},
                    data={
                        'status': enums.ReportStatus.PENDING,
                        'progressPercent': 0,
                        'currentStep': 'queued',
                    }
                )

            # Queue for processing
            task_id = queue_report_processing(existing_report.id)

            return {
                'success': True,
                'encounter_id': encounter_id,
                'report_id': existing_report.id,
                'task_id': task_id,
                'reused': True
            }

        # Create new PENDING report for async processing
        report_data = {
            "encounterId": encounter_id,
            "status": enums.ReportStatus.PENDING,
            "progressPercent": 0,
            "currentStep": "queued",
            # Empty initial data - will be populated by async worker
            "billedCodes": Json([]),
            "suggestedCodes": Json([]),
            "additionalCodes": Json([]),
            "extractedIcd10Codes": Json([]),
            "extractedSnomedCodes": Json([]),
            "cptSuggestions": Json([]),
            "incrementalRevenue": 0.0,
            "aiModel": "gpt-4o-mini",
        }

        report = await prisma.report.create(data=report_data)

        # Queue for async processing
        task_id = queue_report_processing(report.id)

        return {
            'success': True,
            'encounter_id': encounter_id,
            'report_id': report.id,
            'task_id': task_id,
            'reused': False
        }

    except Exception as e:
        logger.error(f"Failed to create report for encounter {encounter_id}", error=str(e))
        return {
            'success': False,
            'encounter_id': encounter_id,
            'error': str(e)
        }


async def monitor_reports(report_ids: List[str], timeout_seconds: int = 300) -> Dict:
    """
    Monitor async report processing progress

    Args:
        report_ids: List of report IDs to monitor
        timeout_seconds: Maximum time to wait (default 5 minutes)

    Returns:
        dict: Summary of processing results
    """
    start_time = datetime.utcnow()
    deadline = start_time.timestamp() + timeout_seconds

    completed_reports = []
    failed_reports = []
    pending_reports = list(report_ids)

    print(f"\n{'='*80}")
    print(f"MONITORING ASYNC REPORT PROCESSING")
    print(f"{'='*80}")
    print(f"Reports queued: {len(report_ids)}")
    print(f"Timeout: {timeout_seconds} seconds")
    print()

    check_interval = 2  # Check every 2 seconds
    last_update = None

    while pending_reports and datetime.utcnow().timestamp() < deadline:
        # Get queue stats
        queue_stats = get_queue_stats()

        # Check status of pending reports
        for report_id in list(pending_reports):
            report = await prisma.report.find_unique(where={'id': report_id})

            if not report:
                pending_reports.remove(report_id)
                failed_reports.append({
                    'report_id': report_id,
                    'error': 'Report disappeared'
                })
                continue

            current_status = {
                'report_id': report_id,
                'status': report.status,
                'progress': report.progressPercent,
                'current_step': report.currentStep,
                'processing_time_ms': report.processingTimeMs
            }

            if report.status == enums.ReportStatus.COMPLETE:
                pending_reports.remove(report_id)
                completed_reports.append(current_status)
                print(f"✅ Report {report_id[:8]} completed in {report.processingTimeMs/1000:.1f}s")

            elif report.status == enums.ReportStatus.FAILED:
                pending_reports.remove(report_id)
                failed_reports.append({
                    **current_status,
                    'error': report.errorMessage
                })
                print(f"❌ Report {report_id[:8]} failed: {report.errorMessage}")

        # Print progress update every 10 seconds
        current_time = datetime.utcnow().timestamp()
        if last_update is None or current_time - last_update >= 10:
            elapsed = int(current_time - start_time.timestamp())
            print(f"[{elapsed}s] Queue: {queue_stats.get('total_tasks', 0)} | "
                  f"Completed: {len(completed_reports)} | "
                  f"Pending: {len(pending_reports)} | "
                  f"Failed: {len(failed_reports)}")
            last_update = current_time

        # Wait before next check
        if pending_reports:
            await asyncio.sleep(check_interval)

    # Check for timeout
    if pending_reports:
        for report_id in pending_reports:
            report = await prisma.report.find_unique(where={'id': report_id})
            failed_reports.append({
                'report_id': report_id,
                'status': report.status if report else 'unknown',
                'progress': report.progressPercent if report else 0,
                'error': f'Timeout after {timeout_seconds} seconds'
            })

    total_time = int(datetime.utcnow().timestamp() - start_time.timestamp())

    return {
        'completed': completed_reports,
        'failed': failed_reports,
        'total_time_seconds': total_time,
        'success_count': len(completed_reports),
        'fail_count': len(failed_reports),
        'total_count': len(report_ids)
    }


async def main():
    """Main test execution"""

    print("="*80)
    print("ANDREA ASYNC REPORT PROCESSING TEST")
    print("="*80)
    print(f"Encounters: {len(ANDREA_ENCOUNTERS)}")
    print()

    # Connect to database
    await prisma.connect()

    try:
        # Phase 1: Create PENDING reports and queue them
        print("="*80)
        print("PHASE 1: CREATING PENDING REPORTS & QUEUING")
        print("="*80)
        print()

        results = []
        for i, (enc_id, date, enc_type) in enumerate(ANDREA_ENCOUNTERS, 1):
            print(f"[{i}/{len(ANDREA_ENCOUNTERS)}] {date} | {enc_type}")
            result = await create_pending_report(enc_id)
            results.append(result)

            if result['success']:
                status = "reused" if result.get('reused') else "created"
                print(f"  ✅ Report {status}: {result['report_id'][:8]}")
            else:
                print(f"  ❌ Failed: {result['error']}")
            print()

        # Get successful report IDs
        report_ids = [r['report_id'] for r in results if r['success']]

        print(f"{'='*80}")
        print(f"PHASE 1 COMPLETE")
        print(f"{'='*80}")
        print(f"Successfully queued: {len(report_ids)}/{len(ANDREA_ENCOUNTERS)}")
        print()

        if not report_ids:
            print("❌ No reports were successfully queued. Exiting.")
            return

        # Phase 2: Monitor async processing
        print("="*80)
        print("PHASE 2: MONITORING ASYNC PROCESSING")
        print("="*80)
        print()

        monitoring_result = await monitor_reports(report_ids, timeout_seconds=600)

        # Phase 3: Display results
        print()
        print("="*80)
        print("FINAL RESULTS")
        print("="*80)
        print()
        print(f"Total Processing Time: {monitoring_result['total_time_seconds']} seconds")
        print(f"Success Rate: {monitoring_result['success_count']}/{monitoring_result['total_count']} "
              f"({monitoring_result['success_count']/monitoring_result['total_count']*100:.1f}%)")
        print()

        if monitoring_result['completed']:
            print("COMPLETED REPORTS:")
            for i, report in enumerate(monitoring_result['completed'], 1):
                print(f"  {i}. {report['report_id'][:8]} - {report['processing_time_ms']/1000:.1f}s")

        if monitoring_result['failed']:
            print()
            print("FAILED REPORTS:")
            for i, report in enumerate(monitoring_result['failed'], 1):
                print(f"  {i}. {report['report_id'][:8]} - {report.get('error', 'Unknown error')}")

        print()
        print("="*80)

        # Success/failure indication
        if monitoring_result['success_count'] == monitoring_result['total_count']:
            print("✅ ALL REPORTS PROCESSED SUCCESSFULLY")
        elif monitoring_result['success_count'] > 0:
            print(f"⚠️  PARTIAL SUCCESS: {monitoring_result['fail_count']} reports failed")
        else:
            print("❌ ALL REPORTS FAILED")

        print("="*80)

    finally:
        await prisma.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
