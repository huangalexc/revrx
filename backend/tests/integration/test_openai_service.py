"""
Integration tests for OpenAI service with expanded features (Track C10-C11)

Tests verify:
- C10: API integration with all new features
- C11: Various note types (outpatient, inpatient, emergency, etc.)
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.openai_service import (
    OpenAIService,
    CodingSuggestionResult,
    CodeSuggestion,
    BilledCode
)


def create_mock_response(response_dict):
    """Helper to create properly structured mock OpenAI response"""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = response_dict["choices"][0]["message"]["content"]
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = response_dict["usage"]["prompt_tokens"]
    mock_response.usage.completion_tokens = response_dict["usage"]["completion_tokens"]
    mock_response.usage.total_tokens = response_dict["usage"]["total_tokens"]
    mock_response.model = response_dict["model"]
    return mock_response


class TestOpenAIServiceIntegration:
    """Test OpenAI service integration with expanded features"""

    @pytest.fixture
    def openai_service(self):
        """Create OpenAI service instance"""
        return OpenAIService()

    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI API response with all expanded features"""
        return {
            "id": "chatcmpl-test123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps({
                            "billed_codes": [
                                {
                                    "code": "99214",
                                    "code_type": "CPT",
                                    "description": "CPT 99214: Office visit, established patient, moderate complexity"
                                }
                            ],
                            "suggested_codes": [
                                {
                                    "code": "99215",
                                    "code_type": "CPT",
                                    "description": "CPT 99215: Office visit, established patient, high complexity",
                                    "justification": "Documentation supports high complexity MDM with multiple chronic conditions",
                                    "confidence": 0.92,
                                    "confidence_reason": "Clear documentation of complex medical decision making",
                                    "supporting_text": ["3 chronic conditions managed", "Medication adjustments documented"]
                                }
                            ],
                            "additional_codes": [],
                            "missing_documentation": [
                                {
                                    "section": "Review of Systems",
                                    "issue": "Only 2 systems documented",
                                    "suggestion": "Document at least 10 systems for comprehensive ROS",
                                    "priority": "Medium"
                                }
                            ],
                            "denial_risks": [
                                {
                                    "code": "99215",
                                    "risk_level": "Low",
                                    "denial_reasons": ["Medical necessity must be clear"],
                                    "documentation_addresses_risks": True,
                                    "mitigation_notes": "Complexity well-documented"
                                }
                            ],
                            "rvu_analysis": {
                                "billed_codes_rvus": 1.92,
                                "suggested_codes_rvus": 2.8,
                                "incremental_rvus": 0.88,
                                "billed_code_details": [
                                    {"code": "99214", "rvus": 1.92, "description": "Level 4 visit"}
                                ],
                                "suggested_code_details": [
                                    {"code": "99215", "rvus": 2.8, "description": "Level 5 visit"}
                                ]
                            },
                            "modifier_suggestions": [],
                            "uncaptured_services": [],
                            "audit_metadata": {
                                "total_codes_identified": 2,
                                "high_confidence_codes": 1,
                                "documentation_quality_score": 0.85,
                                "compliance_flags": [],
                                "timestamp": datetime.utcnow().isoformat() + "Z"
                            }
                        })
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 2500,
                "completion_tokens": 500,
                "total_tokens": 3000
            }
        }

    @pytest.mark.asyncio
    async def test_c10_analyze_with_all_features(self, openai_service, mock_openai_response):
        """C10: Test analysis includes all expanded features"""
        clinical_note = """
        Patient presents with uncontrolled diabetes, hypertension, and CKD.
        Multiple medications adjusted. Time spent: 35 minutes.
        """
        billed_codes = [
            {"code": "99214", "code_type": "CPT", "description": "Office visit L4"}
        ]

        with patch.object(openai_service.client.chat.completions, 'create',
                         new_callable=AsyncMock) as mock_create:
            mock_create.return_value = create_mock_response(mock_openai_response)

            # Execute analysis
            result = await openai_service.analyze_clinical_note(clinical_note, billed_codes)

            # Verify all expanded features present
            assert isinstance(result, CodingSuggestionResult)
            assert len(result.billed_codes) == 1
            assert len(result.suggested_codes) == 1
            assert len(result.missing_documentation) == 1
            assert len(result.denial_risks) == 1
            assert result.rvu_analysis is not None
            assert result.rvu_analysis["incremental_rvus"] == 0.88
            assert result.audit_metadata is not None
            assert result.audit_metadata["total_codes_identified"] == 2

    @pytest.mark.asyncio
    async def test_c11_outpatient_note_type(self, openai_service):
        """C11: Test with outpatient note"""
        outpatient_note = """
        OFFICE VISIT - ESTABLISHED PATIENT
        CC: Follow-up diabetes
        HPI: 60yo M with T2DM, A1c 8.2%
        Exam: BP 135/85, BMI 31.2
        Assessment: Uncontrolled DM
        Plan: Increase metformin, recheck A1c in 3 months
        """
        billed_codes = [{"code": "99213", "code_type": "CPT"}]

        # Verify prompts are generated
        system_prompt = openai_service._create_system_prompt()
        user_prompt = openai_service._create_user_prompt(outpatient_note, billed_codes)

        assert len(system_prompt) > 0
        assert outpatient_note in user_prompt
        assert "99213" in user_prompt
        assert "DOCUMENTATION QUALITY" in user_prompt or "documentation" in user_prompt.lower()

    @pytest.mark.asyncio
    async def test_c11_inpatient_note_type(self, openai_service):
        """C11: Test with inpatient note"""
        inpatient_note = """
        ADMISSION NOTE
        CC: Sepsis
        HPI: 75yo F with fever, hypotension, confusion
        Exam: BP 85/50, HR 120, Temp 102.5F
        Labs: WBC 22k, Lactate 4.2
        Assessment: Septic shock, likely UTI source
        Plan: Broad spectrum antibiotics, IVF, ICU
        """
        billed_codes = [{"code": "99223", "code_type": "CPT"}]

        user_prompt = openai_service._create_user_prompt(inpatient_note, billed_codes)

        assert inpatient_note in user_prompt
        assert "99223" in user_prompt

    @pytest.mark.asyncio
    async def test_c11_emergency_note_type(self, openai_service):
        """C11: Test with emergency department note"""
        emergency_note = """
        ED VISIT
        CC: Chest pain
        HPI: 55yo M, acute onset, 9/10, radiating to jaw
        Exam: Diaphoretic, BP 160/95
        EKG: ST elevation anterior
        Assessment: STEMI
        Plan: Emergent cath lab
        """
        billed_codes = [{"code": "99285", "code_type": "CPT"}]

        user_prompt = openai_service._create_user_prompt(emergency_note, billed_codes)

        assert emergency_note in user_prompt
        assert "99285" in user_prompt

    @pytest.mark.asyncio
    async def test_c11_procedure_note_type(self, openai_service):
        """C11: Test with procedure note"""
        procedure_note = """
        PROCEDURE: Colonoscopy
        Indication: Screening, family hx colon cancer
        Procedure: Colonoscopy with conscious sedation
        Findings: 3 polyps identified, removed with snare
        Pathology: Sent for histology
        """
        billed_codes = [{"code": "45385", "code_type": "CPT"}]

        user_prompt = openai_service._create_user_prompt(procedure_note, billed_codes)

        assert procedure_note in user_prompt

    @pytest.mark.asyncio
    async def test_prompt_includes_all_feature_requests(self, openai_service):
        """Verify prompts request all 7 expanded features"""
        clinical_note = "Test note"
        billed_codes = []

        system_prompt = openai_service._create_system_prompt()
        user_prompt = openai_service._create_user_prompt(clinical_note, billed_codes)

        # Check system prompt has all feature structures
        assert "missing_documentation" in system_prompt
        assert "denial_risks" in system_prompt
        assert "rvu_analysis" in system_prompt
        assert "modifier_suggestions" in system_prompt
        assert "uncaptured_services" in system_prompt
        assert "audit_metadata" in system_prompt

        # Check user prompt requests all features
        assert "DOCUMENTATION" in user_prompt.upper()
        assert "DENIAL" in user_prompt.upper() or "RISK" in user_prompt.upper()
        assert "RVU" in user_prompt.upper()
        assert "MODIFIER" in user_prompt.upper()

    @pytest.mark.asyncio
    async def test_response_parsing_with_expanded_features(self, openai_service, mock_openai_response):
        """Test parsing of LLM response with all expanded features"""
        clinical_note = "Test note"
        billed_codes = []

        with patch.object(openai_service.client.chat.completions, 'create',
                         new_callable=AsyncMock) as mock_create:
            mock_create.return_value = create_mock_response(mock_openai_response)

            result = await openai_service.analyze_clinical_note(clinical_note, billed_codes)

            # Verify expanded features parsed correctly
            assert isinstance(result.missing_documentation, list)
            assert isinstance(result.denial_risks, list)
            assert isinstance(result.rvu_analysis, dict)
            assert isinstance(result.modifier_suggestions, list)
            assert isinstance(result.uncaptured_services, list)
            assert isinstance(result.audit_metadata, dict)

            # Verify specific values
            assert result.missing_documentation[0]["section"] == "Review of Systems"
            assert result.denial_risks[0]["risk_level"] == "Low"
            assert result.rvu_analysis["incremental_rvus"] == 0.88

    @pytest.mark.asyncio
    async def test_to_dict_includes_all_features(self, openai_service, mock_openai_response):
        """Test that to_dict() includes all expanded features"""
        clinical_note = "Test"
        billed_codes = []

        with patch.object(openai_service.client.chat.completions, 'create',
                         new_callable=AsyncMock) as mock_create:
            mock_create.return_value = create_mock_response(mock_openai_response)

            result = await openai_service.analyze_clinical_note(clinical_note, billed_codes)
            result_dict = result.to_dict()

            # Verify all keys present
            required_keys = [
                "billed_codes",
                "suggested_codes",
                "additional_codes",
                "missing_documentation",
                "denial_risks",
                "rvu_analysis",
                "modifier_suggestions",
                "uncaptured_services",
                "audit_metadata",
                "total_incremental_revenue",
                "processing_time_ms",
                "model_used",
                "tokens_used",
                "cost_usd"
            ]

            for key in required_keys:
                assert key in result_dict, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_error_handling_json_parse_error(self, openai_service):
        """Test error handling for invalid JSON response"""
        clinical_note = "Test"
        billed_codes = []

        # Mock response with invalid JSON
        invalid_response = {
            "id": "test",
            "choices": [{
                "message": {
                    "content": "This is not valid JSON"
                }
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            "model": "gpt-4o-mini"
        }

        with patch.object(openai_service.client.chat.completions, 'create',
                         new_callable=AsyncMock) as mock_create:
            mock_create.return_value = create_mock_response(invalid_response)

            with pytest.raises(ValueError, match="Invalid JSON response"):
                await openai_service.analyze_clinical_note(clinical_note, billed_codes)

    @pytest.mark.asyncio
    async def test_default_values_for_missing_features(self, openai_service):
        """Test default values when LLM doesn't return some features"""
        clinical_note = "Test"
        billed_codes = []

        # Mock response with minimal features
        minimal_response = {
            "id": "test",
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "billed_codes": [],
                        "suggested_codes": [],
                        "additional_codes": []
                        # Missing all expanded features
                    })
                }
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            "model": "gpt-4o-mini"
        }

        with patch.object(openai_service.client.chat.completions, 'create',
                         new_callable=AsyncMock) as mock_create:
            mock_create.return_value = create_mock_response(minimal_response)

            result = await openai_service.analyze_clinical_note(clinical_note, billed_codes)

            # Verify defaults are set
            assert result.missing_documentation == []
            assert result.denial_risks == []
            assert result.rvu_analysis == {
                "billed_codes_rvus": 0.0,
                "suggested_codes_rvus": 0.0,
                "incremental_rvus": 0.0,
                "billed_code_details": [],
                "suggested_code_details": []
            }
            assert result.modifier_suggestions == []
            assert result.uncaptured_services == []
            assert isinstance(result.audit_metadata, dict)

    @pytest.mark.asyncio
    async def test_logging_includes_new_feature_counts(self, openai_service, mock_openai_response, caplog):
        """Test that logging includes counts for new features"""
        clinical_note = "Test"
        billed_codes = []

        with patch.object(openai_service.client.chat.completions, 'create',
                         new_callable=AsyncMock) as mock_create:
            mock_create.return_value = create_mock_response(mock_openai_response)

            await openai_service.analyze_clinical_note(clinical_note, billed_codes)

            # Check logs include new feature counts
            log_output = caplog.text
            assert "missing_documentation_count" in log_output or "completed" in log_output.lower()


class TestBatchAnalysis:
    """Test batch analysis with expanded features"""

    @pytest.fixture
    def openai_service(self):
        return OpenAIService()

    @pytest.mark.asyncio
    async def test_batch_analysis_preserves_features(self, openai_service):
        """Test batch analysis returns all features for each encounter"""
        encounters = [
            {
                "clinical_note": "Patient 1 note",
                "billed_codes": [{"code": "99213", "code_type": "CPT"}]
            },
            {
                "clinical_note": "Patient 2 note",
                "billed_codes": [{"code": "99214", "code_type": "CPT"}]
            }
        ]

        with patch.object(openai_service, 'analyze_clinical_note',
                         new_callable=AsyncMock) as mock_analyze:
            # Create mock result with all features
            mock_result = CodingSuggestionResult(
                suggested_codes=[],
                billed_codes=[],
                additional_codes=[],
                missing_documentation=[],
                denial_risks=[],
                rvu_analysis={"incremental_rvus": 0.0},
                modifier_suggestions=[],
                uncaptured_services=[],
                audit_metadata={},
                total_incremental_revenue=0.0,
                processing_time_ms=100,
                model_used="gpt-4o-mini",
                tokens_used=500,
                cost_usd=0.01
            )
            mock_analyze.return_value = mock_result

            results = await openai_service.batch_analyze(encounters, max_concurrent=2)

            assert len(results) == 2
            for result in results:
                assert hasattr(result, 'missing_documentation')
                assert hasattr(result, 'denial_risks')
                assert hasattr(result, 'rvu_analysis')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
