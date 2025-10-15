"""
Unit Tests for Report Processor
Tests async report processing service with mocked external dependencies
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime

from app.services.report_processor import (
    update_report_progress,
    process_report_async,
    OPENAI_TIMEOUT,
    COMPREHEND_TIMEOUT
)
from prisma import enums


@pytest.fixture
def mock_prisma():
    """Mock Prisma client"""
    with patch("app.services.report_processor.prisma") as mock:
        yield mock


@pytest.fixture
def mock_comprehend():
    """Mock Comprehend Medical service"""
    with patch("app.services.report_processor.comprehend_medical_service") as mock:
        # Mock ICD-10 entities
        mock.infer_icd10_cm.return_value = [
            Mock(
                code="E11.9",
                description="Type 2 diabetes mellitus without complications",
                category="MEDICAL_CONDITION",
                type="DX_NAME",
                score=0.95,
                text="diabetes"
            )
        ]

        # Mock SNOMED entities
        mock.infer_snomed_ct.return_value = [
            Mock(
                code="44054006",
                description="Type 2 diabetes mellitus",
                category="MEDICAL_CONDITION",
                type="DX_NAME",
                score=0.92,
                text="diabetes"
            )
        ]

        # Mock medical entities
        mock.detect_entities.return_value = [
            Mock(
                text="diabetes",
                category="MEDICAL_CONDITION",
                type="DX_NAME",
                score=0.95,
                traits=[]
            )
        ]

        yield mock


@pytest.fixture
def mock_openai():
    """Mock OpenAI service"""
    with patch("app.services.report_processor.openai_service") as mock:
        # Mock filtering result
        mock.filter_clinical_relevance.return_value = {
            "filtered_text": "Patient has diabetes mellitus type 2",
            "encounter_type": "Office Visit",
            "original_length": 1000,
            "filtered_length": 500,
            "reduction_pct": 50.0
        }

        # Mock coding result
        mock_coding_result = Mock()
        mock_coding_result.suggested_codes = [
            Mock(
                to_dict=lambda: {
                    "code": "99213",
                    "description": "Office visit, established patient",
                    "confidence": 0.9
                }
            )
        ]
        mock_coding_result.additional_codes = []
        mock_coding_result.billed_codes = []
        mock_coding_result.tokens_used = 2500
        mock_coding_result.cost_usd = 0.005
        mock_coding_result.total_incremental_revenue = 100.0
        mock_coding_result.model_used = "gpt-4o-mini"

        mock.analyze_clinical_note.return_value = mock_coding_result

        yield mock


@pytest.fixture
def mock_icd10_filtering():
    """Mock ICD-10 filtering utilities"""
    with patch("app.services.report_processor.get_diagnosis_entities") as mock_get_diagnosis:
        with patch("app.services.report_processor.filter_icd10_codes") as mock_filter:
            with patch("app.services.report_processor.deduplicate_icd10_codes") as mock_dedup:
                mock_get_diagnosis.return_value = []
                mock_filter.return_value = ([], {"filtered_count": 0})
                mock_dedup.return_value = []

                yield {
                    "get_diagnosis_entities": mock_get_diagnosis,
                    "filter_icd10_codes": mock_filter,
                    "deduplicate_icd10_codes": mock_dedup
                }


class TestUpdateReportProgress:
    """Test update_report_progress function"""

    @pytest.mark.asyncio
    async def test_updates_progress_successfully(self, mock_prisma):
        """Test that progress is updated in database"""
        mock_prisma.report.update = AsyncMock()

        await update_report_progress("report-123", 50, "icd10_inference")

        mock_prisma.report.update.assert_called_once_with(
            where={"id": "report-123"},
            data={
                "progressPercent": 50,
                "currentStep": "icd10_inference"
            }
        )

    @pytest.mark.asyncio
    async def test_handles_database_errors(self, mock_prisma):
        """Test that database errors are logged but not raised"""
        mock_prisma.report.update = AsyncMock(side_effect=Exception("DB Error"))

        # Should not raise exception
        await update_report_progress("report-123", 50, "test_step")


class TestProcessReportAsync:
    """Test process_report_async function"""

    @pytest.mark.asyncio
    async def test_successful_report_processing(
        self,
        mock_prisma,
        mock_comprehend,
        mock_openai,
        mock_icd10_filtering
    ):
        """Test successful end-to-end report processing"""
        # Setup mock data
        mock_encounter = Mock()
        mock_encounter.id = "encounter-123"
        mock_encounter.phiMapping = Mock()
        mock_encounter.phiMapping.deidentifiedText = "Patient has diabetes"
        mock_encounter.phiMapping.phiDetected = True

        mock_report = Mock()
        mock_report.id = "report-123"
        mock_report.encounterId = "encounter-123"
        mock_report.encounter = mock_encounter
        mock_report.retryCount = 0

        # Mock database calls
        mock_prisma.report.find_unique = AsyncMock(return_value=mock_report)
        mock_prisma.report.update = AsyncMock()
        mock_prisma.billingcode.find_many = AsyncMock(return_value=[])

        # Execute
        await process_report_async("report-123")

        # Verify final update with COMPLETE status
        final_update = None
        for call in mock_prisma.report.update.call_args_list:
            if call[1]["data"].get("status") == enums.ReportStatus.COMPLETE:
                final_update = call[1]["data"]
                break

        assert final_update is not None
        assert final_update["progressPercent"] == 100
        assert final_update["currentStep"] == "complete"
        assert "processingCompletedAt" in final_update
        assert "processingTimeMs" in final_update

    @pytest.mark.asyncio
    async def test_handles_filtering_failure_gracefully(
        self,
        mock_prisma,
        mock_comprehend,
        mock_openai,
        mock_icd10_filtering
    ):
        """Test graceful degradation when clinical filtering fails"""
        # Setup mock data
        mock_encounter = Mock()
        mock_encounter.id = "encounter-123"
        mock_encounter.phiMapping = Mock()
        mock_encounter.phiMapping.deidentifiedText = "Original text"
        mock_encounter.phiMapping.phiDetected = False

        mock_report = Mock()
        mock_report.id = "report-123"
        mock_report.encounterId = "encounter-123"
        mock_report.encounter = mock_encounter
        mock_report.retryCount = 0

        mock_prisma.report.find_unique = AsyncMock(return_value=mock_report)
        mock_prisma.report.update = AsyncMock()
        mock_prisma.billingcode.find_many = AsyncMock(return_value=[])

        # Make filtering fail
        mock_openai.filter_clinical_relevance.side_effect = Exception("Filtering error")

        # Execute - should complete despite filtering failure
        await process_report_async("report-123")

        # Verify it still completed successfully
        final_update = None
        for call in mock_prisma.report.update.call_args_list:
            if call[1]["data"].get("status") == enums.ReportStatus.COMPLETE:
                final_update = call[1]["data"]
                break

        assert final_update is not None
        assert final_update["status"] == enums.ReportStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_handles_code_inference_failure_gracefully(
        self,
        mock_prisma,
        mock_comprehend,
        mock_openai,
        mock_icd10_filtering
    ):
        """Test graceful degradation when code inference fails"""
        # Setup mock data
        mock_encounter = Mock()
        mock_encounter.id = "encounter-123"
        mock_encounter.phiMapping = Mock()
        mock_encounter.phiMapping.deidentifiedText = "Text"
        mock_encounter.phiMapping.phiDetected = False

        mock_report = Mock()
        mock_report.id = "report-123"
        mock_report.encounterId = "encounter-123"
        mock_report.encounter = mock_encounter
        mock_report.retryCount = 0

        mock_prisma.report.find_unique = AsyncMock(return_value=mock_report)
        mock_prisma.report.update = AsyncMock()
        mock_prisma.billingcode.find_many = AsyncMock(return_value=[])

        # Make ICD-10 inference fail
        mock_comprehend.infer_icd10_cm.side_effect = Exception("ICD-10 error")
        mock_comprehend.infer_snomed_ct.side_effect = Exception("SNOMED error")

        # Execute - should complete despite code inference failures
        await process_report_async("report-123")

        # Verify it still completed successfully
        final_update = None
        for call in mock_prisma.report.update.call_args_list:
            if call[1]["data"].get("status") == enums.ReportStatus.COMPLETE:
                final_update = call[1]["data"]
                break

        assert final_update is not None

    @pytest.mark.asyncio
    async def test_marks_failed_on_ai_analysis_error(
        self,
        mock_prisma,
        mock_comprehend,
        mock_openai,
        mock_icd10_filtering
    ):
        """Test that AI analysis failures mark report as FAILED"""
        # Setup mock data
        mock_encounter = Mock()
        mock_encounter.id = "encounter-123"
        mock_encounter.phiMapping = Mock()
        mock_encounter.phiMapping.deidentifiedText = "Text"
        mock_encounter.phiMapping.phiDetected = False

        mock_report = Mock()
        mock_report.id = "report-123"
        mock_report.encounterId = "encounter-123"
        mock_report.encounter = mock_encounter
        mock_report.retryCount = 0

        mock_prisma.report.find_unique = AsyncMock(return_value=mock_report)
        mock_prisma.report.update = AsyncMock()
        mock_prisma.billingcode.find_many = AsyncMock(return_value=[])

        # Make AI analysis fail (critical step)
        mock_openai.analyze_clinical_note.side_effect = Exception("AI error")

        # Execute
        await process_report_async("report-123")

        # Verify it was marked as FAILED
        failed_update = None
        for call in mock_prisma.report.update.call_args_list:
            if call[1]["data"].get("status") == enums.ReportStatus.FAILED:
                failed_update = call[1]["data"]
                break

        assert failed_update is not None
        assert "errorMessage" in failed_update
        assert "errorDetails" in failed_update

    @pytest.mark.asyncio
    async def test_timeout_on_openai_filtering(
        self,
        mock_prisma,
        mock_comprehend,
        mock_openai,
        mock_icd10_filtering
    ):
        """Test timeout handling on OpenAI filtering"""
        # Setup mock data
        mock_encounter = Mock()
        mock_encounter.id = "encounter-123"
        mock_encounter.phiMapping = Mock()
        mock_encounter.phiMapping.deidentifiedText = "Text"
        mock_encounter.phiMapping.phiDetected = False

        mock_report = Mock()
        mock_report.id = "report-123"
        mock_report.encounterId = "encounter-123"
        mock_report.encounter = mock_encounter
        mock_report.retryCount = 0

        mock_prisma.report.find_unique = AsyncMock(return_value=mock_report)
        mock_prisma.report.update = AsyncMock()
        mock_prisma.billingcode.find_many = AsyncMock(return_value=[])

        # Make filtering timeout
        async def slow_filter(*args, **kwargs):
            await asyncio.sleep(OPENAI_TIMEOUT + 1)
            return {}

        mock_openai.filter_clinical_relevance.side_effect = slow_filter

        # Execute - should handle timeout gracefully
        await process_report_async("report-123")

        # Verify it completed (with fallback to original text)
        final_update = None
        for call in mock_prisma.report.update.call_args_list:
            if call[1]["data"].get("status") == enums.ReportStatus.COMPLETE:
                final_update = call[1]["data"]
                break

        assert final_update is not None

    @pytest.mark.asyncio
    async def test_retry_logic_on_failure(
        self,
        mock_prisma,
        mock_comprehend,
        mock_openai,
        mock_icd10_filtering
    ):
        """Test retry logic when processing fails"""
        # Setup mock data
        mock_encounter = Mock()
        mock_encounter.id = "encounter-123"
        mock_encounter.phiMapping = Mock()
        mock_encounter.phiMapping.deidentifiedText = "Text"
        mock_encounter.phiMapping.phiDetected = False

        mock_report = Mock()
        mock_report.id = "report-123"
        mock_report.encounterId = "encounter-123"
        mock_report.encounter = mock_encounter
        mock_report.retryCount = 1

        mock_prisma.report.find_unique = AsyncMock(return_value=mock_report)
        mock_prisma.report.update = AsyncMock()
        mock_prisma.billingcode.find_many = AsyncMock(return_value=[])

        # Make AI fail
        mock_openai.analyze_clinical_note.side_effect = Exception("Transient error")

        # Execute with max_retries=3
        await process_report_async("report-123", max_retries=3)

        # Verify retry count was incremented
        failed_update = None
        for call in mock_prisma.report.update.call_args_list:
            if call[1]["data"].get("status") == enums.ReportStatus.FAILED:
                failed_update = call[1]["data"]
                break

        assert failed_update is not None
        assert failed_update["retryCount"] == 2  # Incremented from 1 to 2

    @pytest.mark.asyncio
    async def test_progress_tracking_updates(
        self,
        mock_prisma,
        mock_comprehend,
        mock_openai,
        mock_icd10_filtering
    ):
        """Test that progress is tracked throughout processing"""
        # Setup mock data
        mock_encounter = Mock()
        mock_encounter.id = "encounter-123"
        mock_encounter.phiMapping = Mock()
        mock_encounter.phiMapping.deidentifiedText = "Text"
        mock_encounter.phiMapping.phiDetected = False

        mock_report = Mock()
        mock_report.id = "report-123"
        mock_report.encounterId = "encounter-123"
        mock_report.encounter = mock_encounter
        mock_report.retryCount = 0

        mock_prisma.report.find_unique = AsyncMock(return_value=mock_report)
        mock_prisma.report.update = AsyncMock()
        mock_prisma.billingcode.find_many = AsyncMock(return_value=[])

        # Execute
        await process_report_async("report-123")

        # Collect all progress updates
        progress_updates = []
        for call in mock_prisma.report.update.call_args_list:
            data = call[1]["data"]
            if "progressPercent" in data:
                progress_updates.append(data["progressPercent"])

        # Verify progress goes from 0 to 100
        assert 0 in progress_updates
        assert 100 in progress_updates
        # Verify progress is monotonically increasing
        assert progress_updates == sorted(progress_updates)
        # Verify multiple checkpoints
        assert len(progress_updates) >= 5  # At least 5 progress updates


class TestReportProcessorIntegration:
    """Integration-style tests for report processor"""

    @pytest.mark.asyncio
    async def test_report_not_found(self, mock_prisma):
        """Test handling of non-existent report"""
        mock_prisma.report.find_unique = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Report .* not found"):
            await process_report_async("nonexistent-report")

    @pytest.mark.asyncio
    async def test_encounter_not_found(self, mock_prisma):
        """Test handling of report without encounter"""
        mock_report = Mock()
        mock_report.id = "report-123"
        mock_report.encounter = None

        mock_prisma.report.find_unique = AsyncMock(return_value=mock_report)

        with pytest.raises(ValueError, match="Encounter not found"):
            await process_report_async("report-123")

    @pytest.mark.asyncio
    async def test_phi_mapping_not_found(self, mock_prisma):
        """Test handling of encounter without PHI mapping"""
        mock_encounter = Mock()
        mock_encounter.id = "encounter-123"
        mock_encounter.phiMapping = None

        mock_report = Mock()
        mock_report.id = "report-123"
        mock_report.encounter = mock_encounter

        mock_prisma.report.find_unique = AsyncMock(return_value=mock_report)

        with pytest.raises(ValueError, match="PHI mapping not found"):
            await process_report_async("report-123")
