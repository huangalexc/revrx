"""
Load Testing Script for Async Report Processing
Tests system performance under concurrent load
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import statistics

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import prisma
from app.services.task_queue import queue_report_processing, get_queue_stats
from prisma import enums


async def create_test_data(num_reports: int) -> List[str]:
    """
    Create test encounters and reports for load testing

    Args:
        num_reports: Number of reports to create

    Returns:
        List of report IDs
    """
    print(f"Creating {num_reports} test encounters and reports...")

    # Get or create test user
    test_user = await prisma.user.find_first(where={"email": "loadtest@example.com"})
    if not test_user:
        test_user = await prisma.user.create(
            data={
                "email": "loadtest@example.com",
                "hashedPassword": "loadtest",
                "emailVerified": True,
                "role": "MEMBER"
            }
        )

    report_ids = []

    for i in range(num_reports):
        # Create encounter
        encounter = await prisma.encounter.create(
            data={
                "userId": test_user.id,
                "status": "COMPLETE"
            }
        )

        # Create PHI mapping
        await prisma.phimapping.create(
            data={
                "encounterId": encounter.id,
                "deidentifiedText": f"""
                Load test clinical note {i}.
                Patient presents with hypertension and type 2 diabetes mellitus.
                Blood pressure 140/90, glucose 180 mg/dL.
                Performed comprehensive office visit with examination.
                Discussed medication management and lifestyle modifications.
                """,
                "phiDetected": False
            }
        )

        # Create report
        report = await prisma.report.create(
            data={
                "encounterId": encounter.id,
                "status": enums.ReportStatus.PENDING,
                "progressPercent": 0,
                "currentStep": "queued",
                "billedCodes": [],
                "suggestedCodes": [],
                "additionalCodes": [],
                "extractedIcd10Codes": [],
                "extractedSnomedCodes": [],
                "cptSuggestions": [],
                "incrementalRevenue": 0.0,
                "aiModel": "gpt-4o-mini"
            }
        )

        report_ids.append(report.id)

        if (i + 1) % 10 == 0:
            print(f"Created {i + 1}/{num_reports} reports...")

    print(f"✓ Created {len(report_ids)} test reports")
    return report_ids


async def queue_all_reports(report_ids: List[str], batch_size: int = 10) -> Dict[str, Any]:
    """
    Queue all reports for processing in batches

    Args:
        report_ids: List of report IDs to queue
        batch_size: Number of reports to queue at once

    Returns:
        Dictionary with queuing metrics
    """
    print(f"\nQueuing {len(report_ids)} reports in batches of {batch_size}...")

    start_time = time.time()

    for i in range(0, len(report_ids), batch_size):
        batch = report_ids[i:i + batch_size]
        for report_id in batch:
            queue_report_processing(report_id)

        print(f"Queued {min(i + batch_size, len(report_ids))}/{len(report_ids)} reports...")

        # Small delay between batches
        await asyncio.sleep(0.5)

    queue_time = time.time() - start_time

    print(f"✓ All reports queued in {queue_time:.2f} seconds")

    return {
        "total_queued": len(report_ids),
        "queue_time_seconds": queue_time,
        "reports_per_second": len(report_ids) / queue_time
    }


async def monitor_processing(report_ids: List[str], max_wait_minutes: int = 30) -> Dict[str, Any]:
    """
    Monitor report processing until completion

    Args:
        report_ids: List of report IDs to monitor
        max_wait_minutes: Maximum time to wait

    Returns:
        Dictionary with processing metrics
    """
    print(f"\nMonitoring {len(report_ids)} reports (max wait: {max_wait_minutes} minutes)...")

    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60

    status_counts = {
        "PENDING": 0,
        "PROCESSING": 0,
        "COMPLETE": 0,
        "FAILED": 0
    }

    processing_times = []
    peak_concurrent = 0

    last_print = time.time()

    while time.time() - start_time < max_wait_seconds:
        # Get current status of all reports
        reports = await prisma.report.find_many(
            where={"id": {"in": report_ids}}
        )

        # Count statuses
        current_status = {
            "PENDING": 0,
            "PROCESSING": 0,
            "COMPLETE": 0,
            "FAILED": 0
        }

        for report in reports:
            current_status[report.status] += 1

            # Track processing times for completed reports
            if report.status == enums.ReportStatus.COMPLETE and report.processingTimeMs:
                if report.id not in [r.id for r in reports if r.processingTimeMs]:
                    processing_times.append(report.processingTimeMs)

        # Track peak concurrent processing
        if current_status["PROCESSING"] > peak_concurrent:
            peak_concurrent = current_status["PROCESSING"]

        status_counts = current_status

        # Print status every 5 seconds
        if time.time() - last_print >= 5:
            elapsed = time.time() - start_time
            print(f"[{elapsed:.0f}s] PENDING: {status_counts['PENDING']}, "
                  f"PROCESSING: {status_counts['PROCESSING']}, "
                  f"COMPLETE: {status_counts['COMPLETE']}, "
                  f"FAILED: {status_counts['FAILED']}")

            # Queue stats
            queue_stats = get_queue_stats()
            print(f"      Queue: {queue_stats['running_tasks']} running, "
                  f"{queue_stats['total_queued']} total queued")

            last_print = time.time()

        # Check if all done
        if status_counts["PENDING"] == 0 and status_counts["PROCESSING"] == 0:
            break

        await asyncio.sleep(2)

    total_time = time.time() - start_time

    # Get final processing times
    reports = await prisma.report.find_many(
        where={"id": {"in": report_ids}}
    )
    processing_times = [r.processingTimeMs for r in reports if r.processingTimeMs]

    print(f"\n✓ Monitoring complete ({total_time:.2f} seconds)")

    return {
        "total_time_seconds": total_time,
        "status_counts": status_counts,
        "peak_concurrent_processing": peak_concurrent,
        "processing_times_ms": processing_times,
        "avg_processing_time_ms": statistics.mean(processing_times) if processing_times else 0,
        "median_processing_time_ms": statistics.median(processing_times) if processing_times else 0,
        "min_processing_time_ms": min(processing_times) if processing_times else 0,
        "max_processing_time_ms": max(processing_times) if processing_times else 0,
        "throughput_reports_per_minute": (status_counts["COMPLETE"] / total_time) * 60,
    }


async def analyze_results(queue_metrics: Dict[str, Any], process_metrics: Dict[str, Any]) -> None:
    """
    Analyze and print load test results

    Args:
        queue_metrics: Metrics from queuing phase
        process_metrics: Metrics from processing phase
    """
    print("\n" + "=" * 80)
    print("LOAD TEST RESULTS")
    print("=" * 80)

    print("\n📊 QUEUING METRICS:")
    print(f"  Total Queued:       {queue_metrics['total_queued']} reports")
    print(f"  Queue Time:         {queue_metrics['queue_time_seconds']:.2f} seconds")
    print(f"  Queue Rate:         {queue_metrics['reports_per_second']:.2f} reports/second")

    print("\n⚡ PROCESSING METRICS:")
    print(f"  Total Time:         {process_metrics['total_time_seconds']:.2f} seconds")
    print(f"  Peak Concurrent:    {process_metrics['peak_concurrent_processing']} reports")
    print(f"  Throughput:         {process_metrics['throughput_reports_per_minute']:.2f} reports/minute")

    print("\n✅ COMPLETION STATUS:")
    print(f"  Completed:          {process_metrics['status_counts']['COMPLETE']} reports")
    print(f"  Failed:             {process_metrics['status_counts']['FAILED']} reports")
    print(f"  Pending:            {process_metrics['status_counts']['PENDING']} reports")
    print(f"  Processing:         {process_metrics['status_counts']['PROCESSING']} reports")

    if process_metrics['processing_times_ms']:
        print("\n⏱️  PROCESSING TIME DISTRIBUTION:")
        print(f"  Average:            {process_metrics['avg_processing_time_ms']:.0f} ms")
        print(f"  Median:             {process_metrics['median_processing_time_ms']:.0f} ms")
        print(f"  Min:                {process_metrics['min_processing_time_ms']:.0f} ms")
        print(f"  Max:                {process_metrics['max_processing_time_ms']:.0f} ms")

    # Success rate
    total = sum(process_metrics['status_counts'].values())
    success_rate = (process_metrics['status_counts']['COMPLETE'] / total * 100) if total > 0 else 0

    print("\n📈 SUCCESS RATE:")
    print(f"  {success_rate:.1f}% ({process_metrics['status_counts']['COMPLETE']}/{total})")

    # Performance assessment
    print("\n🎯 ASSESSMENT:")
    if success_rate >= 95:
        print("  ✓ Excellent - System handled load well")
    elif success_rate >= 80:
        print("  ⚠ Good - Some issues under load")
    else:
        print("  ✗ Poor - System struggled with load")

    if process_metrics['peak_concurrent_processing'] >= 5:
        print("  ✓ Good concurrency - Multiple reports processed simultaneously")
    else:
        print("  ⚠ Low concurrency - Consider scaling workers")

    print("\n" + "=" * 80)


async def cleanup_test_data(report_ids: List[str]) -> None:
    """
    Clean up test data after load test

    Args:
        report_ids: List of report IDs to clean up
    """
    print(f"\nCleaning up {len(report_ids)} test reports...")

    # Get all reports and their encounters
    reports = await prisma.report.find_many(
        where={"id": {"in": report_ids}},
        include={"encounter": True}
    )

    encounter_ids = [r.encounterId for r in reports]

    # Delete reports
    await prisma.report.delete_many(where={"id": {"in": report_ids}})

    # Delete PHI mappings
    await prisma.phimapping.delete_many(where={"encounterId": {"in": encounter_ids}})

    # Delete encounters
    await prisma.encounter.delete_many(where={"id": {"in": encounter_ids}})

    print("✓ Cleanup complete")


async def main():
    """Main load test execution"""
    print("=" * 80)
    print("ASYNC REPORT PROCESSING - LOAD TEST")
    print("=" * 80)

    # Configuration
    NUM_REPORTS = 100
    BATCH_SIZE = 10
    MAX_WAIT_MINUTES = 30

    print(f"\nConfiguration:")
    print(f"  Reports to process: {NUM_REPORTS}")
    print(f"  Queue batch size:   {BATCH_SIZE}")
    print(f"  Max wait time:      {MAX_WAIT_MINUTES} minutes")

    try:
        # Connect to database
        await prisma.connect()
        print("\n✓ Database connected")

        # Phase 1: Create test data
        report_ids = await create_test_data(NUM_REPORTS)

        # Phase 2: Queue all reports
        queue_metrics = await queue_all_reports(report_ids, BATCH_SIZE)

        # Phase 3: Monitor processing
        process_metrics = await monitor_processing(report_ids, MAX_WAIT_MINUTES)

        # Phase 4: Analyze results
        await analyze_results(queue_metrics, process_metrics)

        # Phase 5: Cleanup
        cleanup_input = input("\nCleanup test data? (y/n): ")
        if cleanup_input.lower() == 'y':
            await cleanup_test_data(report_ids)
        else:
            print(f"\nTest data retained. Report IDs saved to load_test_report_ids.txt")
            with open("load_test_report_ids.txt", "w") as f:
                f.write("\n".join(report_ids))

    except KeyboardInterrupt:
        print("\n\n⚠ Load test interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Error during load test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await prisma.disconnect()
        print("\n✓ Database disconnected")


if __name__ == "__main__":
    asyncio.run(main())
