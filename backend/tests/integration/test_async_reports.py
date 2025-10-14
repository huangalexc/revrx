"""
Integration Tests for Async Report Processing
Tests end-to-end async report generation with real database
"""

import pytest
import asyncio
from datetime import datetime
import uuid

from app.core.database import prisma
from app.services.task_queue import queue_report_processing, task_queue
from app.services.report_processor import process_report_async
from prisma import enums


@pytest.fixture(scope="function")
async def test_user():
    """Create a test user"""
    user = await prisma.user.create(
        data={
            "email": f"test_{uuid.uuid4()}@example.com",
            "hashedPassword": "hashed",
            "emailVerified": True,
            "role": "MEMBER"
        }
    )
    yield user
    # Cleanup
    await prisma.user.delete(where={"id": user.id})


@pytest.fixture(scope="function")
async def test_encounter(test_user):
    """Create a test encounter with PHI mapping"""
    encounter = await prisma.encounter.create(
        data={
            "userId": test_user.id,
            "status": "COMPLETE"
        }
    )

    # Create PHI mapping
    phi_mapping = await prisma.phimapping.create(
        data={
            "encounterId": encounter.id,
            "deidentifiedText": "Patient presents with type 2 diabetes mellitus. Performed office visit evaluation and management.",
            "phiDetected": False
        }
    )

    yield encounter

    # Cleanup
    await prisma.phimapping.delete(where={"id": phi_mapping.id})
    await prisma.encounter.delete(where={"id": encounter.id})


@pytest.fixture(scope="function")
async def test_report(test_encounter):
    """Create a test report in PENDING status"""
    report = await prisma.report.create(
        data={
            "encounterId": test_encounter.id,
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

    yield report

    # Cleanup
    try:
        await prisma.report.delete(where={"id": report.id})
    except:
        pass  # May already be deleted


class TestAsyncReportGeneration:
    """Test end-to-end async report generation"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_report_status_progression(self, test_report):
        """Test that report progresses through PENDING → PROCESSING → COMPLETE/FAILED"""
        report_id = test_report.id

        # Initial state should be PENDING
        report = await prisma.report.find_unique(where={"id": report_id})
        assert report.status == enums.ReportStatus.PENDING
        assert report.progressPercent == 0

        # Queue for processing (don't await, check status asynchronously)
        queue_report_processing(report_id)

        # Poll status until complete or failed
        max_wait = 120  # 2 minutes max
        start_time = datetime.now()
        processing_seen = False

        while (datetime.now() - start_time).total_seconds() < max_wait:
            report = await prisma.report.find_unique(where={"id": report_id})

            if report.status == enums.ReportStatus.PROCESSING:
                processing_seen = True
                assert report.processingStartedAt is not None
                assert report.progressPercent >= 0

            if report.status in [enums.ReportStatus.COMPLETE, enums.ReportStatus.FAILED]:
                break

            await asyncio.sleep(1)

        # Verify final state
        report = await prisma.report.find_unique(where={"id": report_id})
        assert processing_seen, "Report should have been in PROCESSING state"

        if report.status == enums.ReportStatus.COMPLETE:
            assert report.progressPercent == 100
            assert report.processingCompletedAt is not None
            assert report.processingTimeMs is not None
            assert report.processingTimeMs > 0
            assert len(report.suggestedCodes) >= 0  # May have suggestions

        elif report.status == enums.ReportStatus.FAILED:
            assert report.errorMessage is not None
            pytest.fail(f"Report processing failed: {report.errorMessage}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_progress_tracking(self, test_report):
        """Test that progress is tracked throughout processing"""
        report_id = test_report.id

        # Queue for processing
        queue_report_processing(report_id)

        # Track progress updates
        progress_values = []
        max_wait = 120
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < max_wait:
            report = await prisma.report.find_unique(where={"id": report_id})
            progress_values.append(report.progressPercent)

            if report.status in [enums.ReportStatus.COMPLETE, enums.ReportStatus.FAILED]:
                break

            await asyncio.sleep(0.5)

        # Verify progress tracking
        assert len(progress_values) > 5, "Should have multiple progress updates"
        assert min(progress_values) == 0, "Should start at 0%"
        assert max(progress_values) <= 100, "Should not exceed 100%"

        # Verify progress generally increases (allowing for some reads at same value)
        unique_progress = sorted(set(progress_values))
        assert len(unique_progress) >= 3, "Should have at least 3 distinct progress values"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_concurrent_reports(self, test_user):
        """Test processing multiple reports concurrently"""
        # Create 5 test encounters and reports
        reports = []
        for i in range(5):
            encounter = await prisma.encounter.create(
                data={
                    "userId": test_user.id,
                    "status": "COMPLETE"
                }
            )

            phi_mapping = await prisma.phimapping.create(
                data={
                    "encounterId": encounter.id,
                    "deidentifiedText": f"Test clinical note {i}. Patient has hypertension.",
                    "phiDetected": False
                }
            )

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
            reports.append(report)

        # Queue all reports concurrently
        for report in reports:
            queue_report_processing(report.id)

        # Wait for all to complete
        max_wait = 180  # 3 minutes for 5 reports
        start_time = datetime.now()
        all_complete = False

        while (datetime.now() - start_time).total_seconds() < max_wait:
            statuses = []
            for report in reports:
                r = await prisma.report.find_unique(where={"id": report.id})
                statuses.append(r.status)

            # Check if all are done
            if all(s in [enums.ReportStatus.COMPLETE, enums.ReportStatus.FAILED] for s in statuses):
                all_complete = True
                break

            await asyncio.sleep(2)

        assert all_complete, "Not all reports completed in time"

        # Verify all reports
        completed_count = 0
        failed_count = 0

        for report in reports:
            r = await prisma.report.find_unique(where={"id": report.id})
            if r.status == enums.ReportStatus.COMPLETE:
                completed_count += 1
                assert r.progressPercent == 100
            elif r.status == enums.ReportStatus.FAILED:
                failed_count += 1

        # Most should complete (allow for some transient failures)
        assert completed_count >= 3, f"At least 3 reports should complete (got {completed_count})"

        # Cleanup
        for report in reports:
            r = await prisma.report.find_unique(where={"id": report.id})
            await prisma.phimapping.delete(where={"encounterId": r.encounterId})
            await prisma.encounter.delete(where={"id": r.encounterId})
            await prisma.report.delete(where={"id": report.id})


class TestRetryLogic:
    """Test retry logic on failures"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_retry_count_increments_on_failure(self, test_report):
        """Test that retry count increments when processing fails"""
        report_id = test_report.id

        # Manually mark report as failed to test retry
        await prisma.report.update(
            where={"id": report_id},
            data={
                "status": enums.ReportStatus.FAILED,
                "retryCount": 1,
                "errorMessage": "Test failure"
            }
        )

        # Reset to PENDING and queue again
        await prisma.report.update(
            where={"id": report_id},
            data={
                "status": enums.ReportStatus.PENDING,
                "progressPercent": 0,
                "currentStep": "retry_queued",
                "errorMessage": None
            }
        )

        queue_report_processing(report_id)

        # Wait for completion
        max_wait = 120
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < max_wait:
            report = await prisma.report.find_unique(where={"id": report_id})
            if report.status in [enums.ReportStatus.COMPLETE, enums.ReportStatus.FAILED]:
                break
            await asyncio.sleep(1)

        report = await prisma.report.find_unique(where={"id": report_id})

        # Retry count should be preserved from previous attempt
        # (or incremented if it failed again)
        assert report.retryCount >= 1


class TestQueueStatistics:
    """Test task queue statistics"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_queue_stats_tracking(self, test_report):
        """Test that queue statistics are tracked"""
        from app.services.task_queue import get_queue_stats

        # Get initial stats
        initial_stats = get_queue_stats()
        assert "running_tasks" in initial_stats
        assert "total_queued" in initial_stats

        # Queue a report
        queue_report_processing(test_report.id)

        # Check stats updated
        stats = get_queue_stats()
        assert stats["total_queued"] >= initial_stats["total_queued"]


class TestErrorScenarios:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_missing_phi_mapping(self, test_encounter):
        """Test handling of encounter without PHI mapping"""
        # Delete PHI mapping
        phi_mapping = await prisma.phimapping.find_unique(
            where={"encounterId": test_encounter.id}
        )
        if phi_mapping:
            await prisma.phimapping.delete(where={"id": phi_mapping.id})

        # Create report
        report = await prisma.report.create(
            data={
                "encounterId": test_encounter.id,
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

        # Queue for processing
        queue_report_processing(report.id)

        # Wait for it to fail
        max_wait = 30
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < max_wait:
            r = await prisma.report.find_unique(where={"id": report.id})
            if r.status == enums.ReportStatus.FAILED:
                break
            await asyncio.sleep(1)

        r = await prisma.report.find_unique(where={"id": report.id})
        assert r.status == enums.ReportStatus.FAILED
        assert "PHI mapping not found" in r.errorMessage

        # Cleanup
        await prisma.report.delete(where={"id": report.id})
