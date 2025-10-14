#!/usr/bin/env python3
"""
Complete Async Report Processing Test with Andrea's Encounters

This script:
1. Processes 10 encounters through the FHIR coding pipeline (creates encounter records)
2. Creates PENDING reports for each encounter
3. Queues them for async processing
4. Monitors progress in real-time
5. Displays final results

This tests the full async report processing system end-to-end.
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
from test_fhir_local import LocalFhirClient, generate_synthetic_note
from app.services.fhir.encounter_service import FhirEncounterService
from app.services.fhir.note_service import FhirNoteService
from app.services.phi_handler import phi_handler
from app.services.openai_service import openai_service
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

BUNDLE_PATH = '/Users/alexander/code/revrx/synthetic_data/synthea_fhir4_100/Andrea7_Mercado213_77300ca5-921f-f1ac-1653-5fbfd2ff31ef.json'

# User credentials
TEST_USER_EMAIL = "huang.alex.c@gmail.com"


async def get_or_create_user() -> str:
    """Get or create test user"""
    user = await prisma.user.find_unique(where={'email': TEST_USER_EMAIL})

    if not user:
        # Create test user
        print(f"Creating test user: {TEST_USER_EMAIL}")
        from passlib.context import CryptContext
        import uuid

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash("Testing123")

        user = await prisma.user.create(
            data={
                "id": str(uuid.uuid4()),
                "email": TEST_USER_EMAIL,
                "passwordHash": hashed_password,
                "role": "MEMBER",
                "emailVerified": True,
                "profileComplete": True,
            }
        )
        print(f"Created user with ID: {user.id}")

    return user.id


async def process_encounter_and_create_pending_report(encounter_id: str, bundle_path: str, user_id: str) -> Dict:
    """
    Process encounter through FHIR pipeline and create PENDING report

    Returns:
        dict: Report creation result with report_id
    """
    try:
        # Check if encounter already exists
        existing_encounter = await prisma.encounter.find_unique(
            where={'id': encounter_id}
        )

        if existing_encounter:
            logger.info(f"Encounter {encounter_id[:8]} already exists, skipping FHIR processing")
        else:
            # Process through FHIR pipeline to create encounter record
            print(f"  Processing FHIR data...")

            async with LocalFhirClient(bundle_path) as client:
                encounter_service = FhirEncounterService(client)
                note_service = FhirNoteService(client)

                # Extract encounter metadata
                fhir_encounter = await encounter_service.fetch_encounter_by_id(encounter_id)
                metadata = encounter_service.extract_encounter_metadata(fhir_encounter)

                # Get clinical note
                doc_refs = await client.search_resources(
                    "DocumentReference",
                    {"encounter": f"Encounter/{encounter_id}"}
                )

                clinical_text = None
                if doc_refs:
                    doc_ref = doc_refs[0]
                    content = doc_ref.get("content", [{}])[0]
                    attachment = content.get("attachment", {})

                    if "data" in attachment:
                        import base64
                        clinical_text = base64.b64decode(attachment["data"]).decode("utf-8")

                # Fallback to synthetic note
                if not clinical_text:
                    conditions = await client.search_resources(
                        "Condition",
                        {"encounter": f"Encounter/{encounter_id}"}
                    )
                    procedures = await client.search_resources(
                        "Procedure",
                        {"encounter": f"Encounter/{encounter_id}"}
                    )
                    clinical_data = {"conditions": conditions, "procedures": procedures}
                    clinical_text = generate_synthetic_note(metadata, clinical_data)

                # Create encounter record FIRST (required for PHI mapping foreign key)
                print(f"  Creating encounter record...")

                # Convert date string to datetime (add time component)
                from datetime import datetime as dt
                date_str = metadata['date_of_service']
                if 'T' not in date_str:
                    date_str = f"{date_str}T00:00:00Z"

                encounter = await prisma.encounter.create(
                    data={
                        "id": encounter_id,
                        "user": {"connect": {"id": user_id}},
                        "dateOfService": date_str,
                        "encounterType": metadata.get('encounter_type', 'Unknown'),
                        "fhirPatientId": metadata['fhir_patient_id'],
                        "fhirProviderId": metadata.get('fhir_provider_id'),
                        "status": enums.EncounterStatus.COMPLETE,
                    }
                )

                # Process PHI (this will create PHI mapping linked to encounter)
                print(f"  Detecting PHI...")
                phi_result = await phi_handler.process_clinical_note(
                    encounter_id=encounter_id,
                    clinical_text=clinical_text,
                    user_id=user_id
                )

                logger.info(f"Created encounter {encounter_id[:8]}")

        # Check if report already exists
        existing_report = await prisma.report.find_first(
            where={'encounterId': encounter_id}
        )

        if existing_report:
            print(f"  Report already exists, resetting to PENDING...")

            # Reset to PENDING for reprocessing
            await prisma.report.update(
                where={'id': existing_report.id},
                data={
                    'status': enums.ReportStatus.PENDING,
                    'progressPercent': 0,
                    'currentStep': 'queued',
                }
            )

            report_id = existing_report.id
        else:
            # Create new PENDING report
            print(f"  Creating PENDING report...")
            report_data = {
                "encounter": {"connect": {"id": encounter_id}},
                "status": enums.ReportStatus.PENDING,
                "progressPercent": 0,
                "currentStep": "queued",
                # Empty initial data - will be populated by async worker
                "billedCodes": Json([]),
                "suggestedCodes": Json([]),
                "extractedIcd10Codes": Json([]),
                "extractedSnomedCodes": Json([]),
                "cptSuggestions": Json([]),
                "incrementalRevenue": 0.0,
                "aiModel": "gpt-4o-mini",
            }

            report = await prisma.report.create(data=report_data)
            report_id = report.id

        # Queue for async processing
        print(f"  Queuing for async processing...")
        task_id = queue_report_processing(report_id)

        return {
            'success': True,
            'encounter_id': encounter_id,
            'report_id': report_id,
            'task_id': task_id
        }

    except Exception as e:
        logger.error(f"Failed to process encounter {encounter_id}", error=str(e), exc_info=True)
        return {
            'success': False,
            'encounter_id': encounter_id,
            'error': str(e)
        }


async def monitor_reports(report_ids: List[str], timeout_seconds: int = 600) -> Dict:
    """
    Monitor async report processing progress

    Args:
        report_ids: List of report IDs to monitor
        timeout_seconds: Maximum time to wait (default 10 minutes)

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

    check_interval = 3  # Check every 3 seconds
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
                'processing_time_ms': report.processingTimeMs,
                'incremental_revenue': report.incrementalRevenue,
                'suggested_codes': report.suggestedCodes if report.suggestedCodes else []
            }

            if report.status == enums.ReportStatus.COMPLETE:
                pending_reports.remove(report_id)
                completed_reports.append(current_status)
                revenue = report.incrementalRevenue or 0
                print(f"✅ Report {report_id[:8]} completed in {report.processingTimeMs/1000:.1f}s | Revenue: ${revenue:.2f}")

            elif report.status == enums.ReportStatus.FAILED:
                pending_reports.remove(report_id)
                failed_reports.append({
                    **current_status,
                    'error': report.errorMessage
                })
                print(f"❌ Report {report_id[:8]} failed: {report.errorMessage}")

        # Print progress update every 15 seconds
        current_time = datetime.utcnow().timestamp()
        if last_update is None or current_time - last_update >= 15:
            elapsed = int(current_time - start_time.timestamp())
            print(f"[{elapsed}s] Queue: {queue_stats.get('total_tasks', 0)} tasks | "
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
    print("ANDREA COMPLETE ASYNC REPORT PROCESSING TEST")
    print("="*80)
    print(f"Bundle: {BUNDLE_PATH}")
    print(f"Encounters: {len(ANDREA_ENCOUNTERS)}")
    print()

    # Connect to database
    await prisma.connect()

    try:
        # Get or create user
        print(f"Fetching/creating user: {TEST_USER_EMAIL}")
        user_id = await get_or_create_user()
        print(f"User ID: {user_id}")
        print()

        # Phase 1: Process encounters and create PENDING reports
        print("="*80)
        print("PHASE 1: PROCESSING ENCOUNTERS & CREATING PENDING REPORTS")
        print("="*80)
        print()

        results = []
        for i, (enc_id, date, enc_type) in enumerate(ANDREA_ENCOUNTERS, 1):
            print(f"[{i}/{len(ANDREA_ENCOUNTERS)}] {date} | {enc_type}")
            result = await process_encounter_and_create_pending_report(enc_id, BUNDLE_PATH, user_id)
            results.append(result)

            if result['success']:
                print(f"  ✅ Queued: {result['report_id'][:8]}")
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
            print("COMPLETED REPORTS WITH REVENUE BREAKDOWN:")
            avg_time = sum(r['processing_time_ms'] for r in monitoring_result['completed']) / len(monitoring_result['completed'])
            total_revenue = sum(r.get('incremental_revenue', 0) or 0 for r in monitoring_result['completed'])

            for i, report in enumerate(monitoring_result['completed'], 1):
                revenue = report.get('incremental_revenue', 0) or 0
                print(f"  {i}. {report['report_id'][:8]} - {report['processing_time_ms']/1000:.1f}s - ${revenue:.2f}")

                # Show top 3 suggested codes with revenue
                codes = report.get('suggested_codes', [])
                for code in codes[:3]:
                    code_revenue = code.get('incremental_revenue') or 0
                    code_type = code.get('code_type', 'N/A')
                    code_num = code.get('code', 'N/A')
                    description = code.get('description', 'N/A')[:50]
                    print(f"     • {code_type} {code_num}: ${code_revenue:.2f} - {description}")

            print(f"\n  Average processing time: {avg_time/1000:.1f}s")
            avg_revenue = total_revenue / len(monitoring_result['completed']) if monitoring_result['completed'] else 0
            print(f"  Total Revenue Opportunity: ${total_revenue:.2f}")
            print(f"  Average Revenue per Encounter: ${avg_revenue:.2f}")

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
