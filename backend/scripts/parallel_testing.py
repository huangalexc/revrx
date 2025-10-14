"""
Parallel Testing Script for Async vs Sync Report Processing

This script tests both async and sync processing paths in parallel and
compares their performance, success rates, and accuracy.

Usage:
    python scripts/parallel_testing.py --count 100 --async-percentage 10
"""

import asyncio
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any
import statistics
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import prisma
from app.core import enums
from app.services.report_processor_sync import generate_report_sync, should_process_async
from app.services.task_queue import queue_report_processing
import structlog

logger = structlog.get_logger(__name__)


class ParallelTestResults:
    """Container for test results"""

    def __init__(self):
        self.sync_results: List[Dict[str, Any]] = []
        self.async_results: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []

    def add_sync_result(self, result: Dict[str, Any]):
        self.sync_results.append(result)

    def add_async_result(self, result: Dict[str, Any]):
        self.async_results.append(result)

    def add_error(self, mode: str, encounter_id: str, error: str):
        self.errors.append({
            "mode": mode,
            "encounter_id": encounter_id,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_summary(self) -> Dict[str, Any]:
        """Generate summary statistics"""

        # Sync statistics
        sync_count = len(self.sync_results)
        sync_success = sum(1 for r in self.sync_results if r["success"])
        sync_times = [r["processing_time_ms"] for r in self.sync_results if r["success"]]

        # Async statistics
        async_count = len(self.async_results)
        async_success = sum(1 for r in self.async_results if r["success"])
        async_times = [r["processing_time_ms"] for r in self.async_results if r["success"]]

        return {
            "sync": {
                "total": sync_count,
                "success": sync_success,
                "failed": sync_count - sync_success,
                "success_rate": (sync_success / sync_count * 100) if sync_count > 0 else 0,
                "processing_time": {
                    "min": min(sync_times) if sync_times else 0,
                    "max": max(sync_times) if sync_times else 0,
                    "mean": statistics.mean(sync_times) if sync_times else 0,
                    "median": statistics.median(sync_times) if sync_times else 0,
                    "p95": statistics.quantiles(sync_times, n=20)[18] if len(sync_times) > 10 else 0,
                    "p99": statistics.quantiles(sync_times, n=100)[98] if len(sync_times) > 100 else 0,
                } if sync_times else {}
            },
            "async": {
                "total": async_count,
                "success": async_success,
                "failed": async_count - async_success,
                "success_rate": (async_success / async_count * 100) if async_count > 0 else 0,
                "processing_time": {
                    "min": min(async_times) if async_times else 0,
                    "max": max(async_times) if async_times else 0,
                    "mean": statistics.mean(async_times) if async_times else 0,
                    "median": statistics.median(async_times) if async_times else 0,
                    "p95": statistics.quantiles(async_times, n=20)[18] if len(async_times) > 10 else 0,
                    "p99": statistics.quantiles(async_times, n=100)[98] if len(async_times) > 100 else 0,
                } if async_times else {}
            },
            "errors": len(self.errors),
            "error_details": self.errors
        }


async def test_sync_processing(encounter_id: str) -> Dict[str, Any]:
    """Test synchronous report processing"""

    start_time = datetime.utcnow()

    try:
        result = await generate_report_sync(encounter_id)

        end_time = datetime.utcnow()
        processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

        return {
            "encounter_id": encounter_id,
            "mode": "sync",
            "success": True,
            "processing_time_ms": processing_time_ms,
            "report_id": result.get("report_id"),
            "timestamp": start_time.isoformat()
        }

    except Exception as e:
        end_time = datetime.utcnow()
        processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.error("Sync processing failed", encounter_id=encounter_id, error=str(e))

        return {
            "encounter_id": encounter_id,
            "mode": "sync",
            "success": False,
            "processing_time_ms": processing_time_ms,
            "error": str(e),
            "timestamp": start_time.isoformat()
        }


async def test_async_processing(encounter_id: str, timeout_seconds: int = 120) -> Dict[str, Any]:
    """Test asynchronous report processing (wait for completion)"""

    start_time = datetime.utcnow()

    try:
        # Get report
        existing_report = await prisma.report.find_first(
            where={"encounterId": encounter_id}
        )

        if not existing_report:
            raise ValueError(f"No report found for encounter {encounter_id}")

        # Wait for completion (with timeout)
        deadline = datetime.utcnow() + timedelta(seconds=timeout_seconds)
        report_id = existing_report.id

        while datetime.utcnow() < deadline:
            report = await prisma.report.find_unique(where={"id": report_id})

            if not report:
                raise ValueError(f"Report {report_id} disappeared")

            if report.status == enums.ReportStatus.COMPLETE:
                end_time = datetime.utcnow()
                processing_time_ms = report.processingTimeMs or int((end_time - start_time).total_seconds() * 1000)

                return {
                    "encounter_id": encounter_id,
                    "mode": "async",
                    "success": True,
                    "processing_time_ms": processing_time_ms,
                    "report_id": report.id,
                    "timestamp": start_time.isoformat()
                }

            elif report.status == enums.ReportStatus.FAILED:
                end_time = datetime.utcnow()
                processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

                return {
                    "encounter_id": encounter_id,
                    "mode": "async",
                    "success": False,
                    "processing_time_ms": processing_time_ms,
                    "error": report.errorMessage or "Unknown error",
                    "timestamp": start_time.isoformat()
                }

            # Wait before checking again
            await asyncio.sleep(2)

        # Timeout
        end_time = datetime.utcnow()
        processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

        return {
            "encounter_id": encounter_id,
            "mode": "async",
            "success": False,
            "processing_time_ms": processing_time_ms,
            "error": f"Timeout after {timeout_seconds} seconds",
            "timestamp": start_time.isoformat()
        }

    except Exception as e:
        end_time = datetime.utcnow()
        processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.error("Async processing test failed", encounter_id=encounter_id, error=str(e))

        return {
            "encounter_id": encounter_id,
            "mode": "async",
            "success": False,
            "processing_time_ms": processing_time_ms,
            "error": str(e),
            "timestamp": start_time.isoformat()
        }


async def get_test_encounters(count: int) -> List[str]:
    """Get encounters for testing (must have PHI mapping and no existing report)"""

    # Find completed encounters with PHI mapping
    encounters = await prisma.encounter.find_many(
        where={
            "status": enums.EncounterStatus.COMPLETE,
            "phiMapping": {"isNot": None},
        },
        take=count * 2,  # Get more than needed in case some have reports
        order={"createdAt": "desc"},
        include={"report": True}
    )

    # Filter out encounters that already have reports
    test_encounters = [
        e.id for e in encounters
        if not e.report
    ][:count]

    if len(test_encounters) < count:
        logger.warning(
            f"Only found {len(test_encounters)} suitable encounters (requested {count})"
        )

    return test_encounters


async def run_parallel_tests(
    encounter_ids: List[str],
    async_percentage: int,
    results: ParallelTestResults
):
    """Run tests in parallel for sync and async processing"""

    tasks = []

    for i, encounter_id in enumerate(encounter_ids):
        # Determine mode based on percentage
        use_async = (i % 100) < async_percentage

        if use_async:
            # Queue async processing first
            try:
                report = await prisma.report.create(data={
                    "encounterId": encounter_id,
                    "status": enums.ReportStatus.PENDING,
                    "progressPercent": 0,
                    "currentStep": "queued"
                })
                queue_report_processing(report.id)

                # Create task to wait for completion
                task = test_async_processing(encounter_id)
                tasks.append(("async", encounter_id, task))

            except Exception as e:
                results.add_error("async", encounter_id, str(e))
        else:
            # Create sync processing task
            task = test_sync_processing(encounter_id)
            tasks.append(("sync", encounter_id, task))

    # Wait for all tasks to complete
    for mode, encounter_id, task in tasks:
        try:
            result = await task

            if mode == "sync":
                results.add_sync_result(result)
            else:
                results.add_async_result(result)

        except Exception as e:
            results.add_error(mode, encounter_id, str(e))


async def main():
    """Main test execution"""

    parser = argparse.ArgumentParser(description="Parallel Testing for Async vs Sync Processing")
    parser.add_argument("--count", type=int, default=50, help="Number of reports to test")
    parser.add_argument("--async-percentage", type=int, default=10, help="Percentage to process async (0-100)")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout for async processing (seconds)")

    args = parser.parse_args()

    # Validate arguments
    if not 0 <= args.async_percentage <= 100:
        print("Error: async-percentage must be between 0 and 100")
        return

    print(f"Starting parallel testing...")
    print(f"  Total reports: {args.count}")
    print(f"  Async percentage: {args.async_percentage}%")
    print(f"  Expected async: {int(args.count * args.async_percentage / 100)}")
    print(f"  Expected sync: {int(args.count * (100 - args.async_percentage) / 100)}")
    print()

    # Connect to database
    await prisma.connect()

    try:
        # Get test encounters
        print("Finding suitable test encounters...")
        encounter_ids = await get_test_encounters(args.count)
        print(f"Found {len(encounter_ids)} test encounters")
        print()

        if len(encounter_ids) < args.count:
            print(f"Warning: Only {len(encounter_ids)} encounters available (requested {args.count})")
            print()

        # Run tests
        results = ParallelTestResults()
        start_time = datetime.utcnow()

        print("Running parallel tests...")
        await run_parallel_tests(encounter_ids, args.async_percentage, results)

        end_time = datetime.utcnow()
        total_time = (end_time - start_time).total_seconds()

        # Generate summary
        print()
        print("=" * 80)
        print("TEST RESULTS")
        print("=" * 80)

        summary = results.get_summary()

        print(f"\nTotal execution time: {total_time:.2f} seconds")
        print()

        # Sync results
        print("SYNCHRONOUS PROCESSING:")
        sync_stats = summary["sync"]
        print(f"  Total: {sync_stats['total']}")
        print(f"  Success: {sync_stats['success']} ({sync_stats['success_rate']:.1f}%)")
        print(f"  Failed: {sync_stats['failed']}")
        if sync_stats.get("processing_time"):
            times = sync_stats["processing_time"]
            print(f"  Processing Time:")
            print(f"    Min: {times['min']/1000:.2f}s")
            print(f"    Max: {times['max']/1000:.2f}s")
            print(f"    Mean: {times['mean']/1000:.2f}s")
            print(f"    Median: {times['median']/1000:.2f}s")
            if times.get('p95'):
                print(f"    P95: {times['p95']/1000:.2f}s")

        print()

        # Async results
        print("ASYNCHRONOUS PROCESSING:")
        async_stats = summary["async"]
        print(f"  Total: {async_stats['total']}")
        print(f"  Success: {async_stats['success']} ({async_stats['success_rate']:.1f}%)")
        print(f"  Failed: {async_stats['failed']}")
        if async_stats.get("processing_time"):
            times = async_stats["processing_time"]
            print(f"  Processing Time:")
            print(f"    Min: {times['min']/1000:.2f}s")
            print(f"    Max: {times['max']/1000:.2f}s")
            print(f"    Mean: {times['mean']/1000:.2f}s")
            print(f"    Median: {times['median']/1000:.2f}s")
            if times.get('p95'):
                print(f"    P95: {times['p95']/1000:.2f}s")

        print()

        # Comparison
        if sync_stats['total'] > 0 and async_stats['total'] > 0:
            print("COMPARISON:")
            success_rate_diff = async_stats['success_rate'] - sync_stats['success_rate']
            print(f"  Success Rate Difference: {success_rate_diff:+.1f}% (async - sync)")

            if sync_stats.get("processing_time") and async_stats.get("processing_time"):
                mean_diff = async_stats['processing_time']['mean'] - sync_stats['processing_time']['mean']
                print(f"  Mean Processing Time Difference: {mean_diff/1000:+.2f}s (async - sync)")

                if async_stats['processing_time']['mean'] < sync_stats['processing_time']['mean']:
                    improvement = (1 - async_stats['processing_time']['mean'] / sync_stats['processing_time']['mean']) * 100
                    print(f"  Async is {improvement:.1f}% faster")
                else:
                    degradation = (async_stats['processing_time']['mean'] / sync_stats['processing_time']['mean'] - 1) * 100
                    print(f"  Async is {degradation:.1f}% slower")

        print()

        # Errors
        if summary["errors"] > 0:
            print(f"ERRORS: {summary['errors']}")
            for error in summary["error_details"][:5]:  # Show first 5 errors
                print(f"  [{error['mode']}] {error['encounter_id']}: {error['error']}")
            if summary["errors"] > 5:
                print(f"  ... and {summary['errors'] - 5} more errors")

        print()
        print("=" * 80)

        # Recommendations
        print("\nRECOMMENDATIONS:")
        if async_stats['success_rate'] >= sync_stats['success_rate'] - 1:  # Allow 1% margin
            print("  ✓ Async success rate is acceptable")
        else:
            print(f"  ✗ Async success rate is {sync_stats['success_rate'] - async_stats['success_rate']:.1f}% lower - investigate failures")

        if async_stats.get("processing_time") and sync_stats.get("processing_time"):
            if async_stats['processing_time']['p95'] < 60000:  # 60 seconds
                print("  ✓ Async p95 processing time is under 60 seconds")
            else:
                print(f"  ✗ Async p95 processing time is {async_stats['processing_time']['p95']/1000:.1f}s - optimize processing")

    finally:
        await prisma.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
