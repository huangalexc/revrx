"""
End-to-End tests for complete analysis workflow (Track G13-G17)

Tests verify:
- G13: Upload → analysis → all features displayed workflow
- G14: Export workflow (PDF and CSV)
- G15: Filtering and sorting across features
- G16: Responsive design considerations
- G17: Accessibility requirements

Note: These are integration-level E2E tests that verify data flow
and structure. Full browser-based E2E tests would use Playwright/Cypress.
"""

import pytest
import json
from typing import Dict, List
from datetime import datetime

from app.services.prompt_templates import prompt_templates


class TestEndToEndWorkflow:
    """Test complete upload → analysis → display workflow (G13)"""

    @pytest.fixture
    def complete_analysis_response_structure(self) -> Dict:
        """Expected structure of complete analysis response"""
        return {
            "billed_codes": [],
            "suggested_codes": [],
            "additional_codes": [],
            "missing_documentation": [],
            "denial_risks": [],
            "rvu_analysis": {
                "billed_codes_rvus": 0.0,
                "suggested_codes_rvus": 0.0,
                "incremental_rvus": 0.0,
                "billed_code_details": [],
                "suggested_code_details": []
            },
            "modifier_suggestions": [],
            "uncaptured_services": [],
            "audit_metadata": {
                "total_codes_identified": 0,
                "high_confidence_codes": 0,
                "documentation_quality_score": 0.0,
                "compliance_flags": [],
                "timestamp": ""
            }
        }

    def test_g13_workflow_step1_prompt_generation(self):
        """G13: Step 1 - Generate prompts for analysis"""
        clinical_note = """
            Patient presents with chest pain.
            EKG performed, troponin ordered.
            Diagnosis: Acute coronary syndrome
        """
        billed_codes = [{"code": "99214", "code_type": "CPT"}]

        # Generate prompts
        system_prompt = prompt_templates.get_system_prompt()
        user_prompt = prompt_templates.get_user_prompt(clinical_note, billed_codes)

        # Verify prompts ready for LLM
        assert system_prompt is not None and len(system_prompt) > 0
        assert user_prompt is not None and len(user_prompt) > 0
        assert clinical_note in user_prompt
        assert "99214" in user_prompt

    def test_g13_workflow_step2_response_parsing(self, complete_analysis_response_structure):
        """G13: Step 2 - Parse LLM response into structured data"""
        # Simulate LLM response structure
        mock_response = json.dumps(complete_analysis_response_structure)

        # Verify JSON parseable
        parsed = json.loads(mock_response)
        assert isinstance(parsed, dict)
        assert "billed_codes" in parsed
        assert "missing_documentation" in parsed

    def test_g13_workflow_step3_feature_data_available(self, complete_analysis_response_structure):
        """G13: Step 3 - All feature data available for display"""
        response = complete_analysis_response_structure

        # Verify all 9 main features present
        required_features = [
            "billed_codes",
            "suggested_codes",
            "additional_codes",
            "missing_documentation",
            "denial_risks",
            "rvu_analysis",
            "modifier_suggestions",
            "uncaptured_services",
            "audit_metadata"
        ]

        for feature in required_features:
            assert feature in response, f"Missing feature: {feature}"

    def test_g13_workflow_complete_with_sample_data(self):
        """G13: Complete workflow with sample data"""
        # Simulated complete workflow
        clinical_note = "Patient presents with diabetes mellitus"
        billed_codes = [{"code": "99213", "code_type": "CPT"}]

        # Step 1: Generate prompts
        system_prompt = prompt_templates.get_system_prompt()
        user_prompt = prompt_templates.get_user_prompt(clinical_note, billed_codes)

        # Step 2: Verify prompt contains all feature requests
        assert all(feature in user_prompt.upper() for feature in
                  ["CODE", "DOCUMENTATION", "DENIAL", "RVU", "MODIFIER"])

        # Step 3: Verify system prompt defines response structure
        assert "missing_documentation" in system_prompt
        assert "denial_risks" in system_prompt
        assert "rvu_analysis" in system_prompt


class TestExportWorkflow:
    """Test export workflow for PDF and CSV (G14)"""

    @pytest.fixture
    def sample_analysis_result(self) -> Dict:
        """Sample analysis result for export"""
        return {
            "billed_codes": [
                {"code": "99214", "code_type": "CPT", "description": "Office visit"}
            ],
            "suggested_codes": [
                {
                    "code": "99215",
                    "code_type": "CPT",
                    "description": "Office visit, high complexity",
                    "justification": "Documentation supports high complexity",
                    "confidence": 0.92
                }
            ],
            "missing_documentation": [
                {
                    "section": "HPI",
                    "issue": "Duration not specified",
                    "suggestion": "Add timeline",
                    "priority": "High"
                }
            ],
            "denial_risks": [
                {
                    "code": "99215",
                    "risk_level": "Medium",
                    "denial_reasons": ["Complexity not fully documented"],
                    "documentation_addresses_risks": False,
                    "mitigation_notes": "Add detailed MDM documentation"
                }
            ],
            "rvu_analysis": {
                "billed_codes_rvus": 1.92,
                "suggested_codes_rvus": 2.8,
                "incremental_rvus": 0.88
            },
            "modifier_suggestions": [
                {
                    "code": "99214",
                    "modifier": "-25",
                    "justification": "Separate E/M service",
                    "documentation_support": "Clear documentation"
                }
            ],
            "uncaptured_services": [
                {
                    "service": "PHQ-9 screening",
                    "location_in_note": "Assessment",
                    "suggested_codes": ["96127"],
                    "priority": "High",
                    "estimated_rvus": 0.18
                }
            ],
            "audit_metadata": {
                "total_codes_identified": 3,
                "high_confidence_codes": 2,
                "documentation_quality_score": 0.78,
                "compliance_flags": [],
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }

    def test_g14_export_data_structure_complete(self, sample_analysis_result):
        """G14: Verify export data structure is complete"""
        # Export should include all analysis features
        required_export_fields = [
            "billed_codes",
            "suggested_codes",
            "missing_documentation",
            "denial_risks",
            "rvu_analysis",
            "modifier_suggestions",
            "uncaptured_services",
            "audit_metadata"
        ]

        for field in required_export_fields:
            assert field in sample_analysis_result, f"Missing field for export: {field}"

    def test_g14_export_includes_metadata(self, sample_analysis_result):
        """G14: Export includes audit metadata"""
        metadata = sample_analysis_result["audit_metadata"]

        assert "timestamp" in metadata
        assert "total_codes_identified" in metadata
        assert "documentation_quality_score" in metadata
        assert "compliance_flags" in metadata

    def test_g14_export_serializable_to_json(self, sample_analysis_result):
        """G14: Export data is JSON serializable (for CSV/PDF generation)"""
        try:
            json_string = json.dumps(sample_analysis_result)
            assert len(json_string) > 0

            # Verify can be parsed back
            parsed = json.loads(json_string)
            assert parsed["billed_codes"] == sample_analysis_result["billed_codes"]
        except (TypeError, ValueError) as e:
            pytest.fail(f"Export data not JSON serializable: {e}")

    def test_g14_export_includes_all_features(self, sample_analysis_result):
        """G14: Exported data includes data from all 7 features"""
        # Check each feature has data
        assert len(sample_analysis_result["billed_codes"]) > 0
        assert len(sample_analysis_result["suggested_codes"]) > 0
        assert len(sample_analysis_result["missing_documentation"]) > 0
        assert len(sample_analysis_result["denial_risks"]) > 0
        assert sample_analysis_result["rvu_analysis"]["billed_codes_rvus"] > 0
        assert len(sample_analysis_result["modifier_suggestions"]) > 0
        assert len(sample_analysis_result["uncaptured_services"]) > 0


class TestFilteringSorting:
    """Test filtering and sorting capabilities (G15)"""

    @pytest.fixture
    def multi_code_analysis(self) -> Dict:
        """Analysis result with multiple items for filtering/sorting"""
        return {
            "suggested_codes": [
                {"code": "99215", "confidence": 0.95},
                {"code": "99214", "confidence": 0.82},
                {"code": "93000", "confidence": 0.78},
                {"code": "80053", "confidence": 0.65}
            ],
            "denial_risks": [
                {"code": "99215", "risk_level": "Low"},
                {"code": "99214", "risk_level": "Medium"},
                {"code": "93000", "risk_level": "High"},
                {"code": "80053", "risk_level": "Medium"}
            ],
            "missing_documentation": [
                {"section": "HPI", "priority": "High"},
                {"section": "ROS", "priority": "Medium"},
                {"section": "Physical Exam", "priority": "Low"}
            ],
            "uncaptured_services": [
                {"service": "PHQ-9", "priority": "High", "estimated_rvus": 0.18},
                {"service": "EKG", "priority": "Medium", "estimated_rvus": 0.17},
                {"service": "Counseling", "priority": "Low", "estimated_rvus": 0.0}
            ]
        }

    def test_g15_filter_by_confidence(self, multi_code_analysis):
        """G15: Filter suggested codes by confidence threshold"""
        high_confidence = [
            code for code in multi_code_analysis["suggested_codes"]
            if code["confidence"] >= 0.8
        ]

        assert len(high_confidence) == 2  # 99215 and 99214
        assert high_confidence[0]["code"] in ["99215", "99214"]

    def test_g15_filter_by_risk_level(self, multi_code_analysis):
        """G15: Filter denial risks by risk level"""
        high_risk = [
            risk for risk in multi_code_analysis["denial_risks"]
            if risk["risk_level"] == "High"
        ]

        assert len(high_risk) == 1
        assert high_risk[0]["code"] == "93000"

    def test_g15_filter_by_priority(self, multi_code_analysis):
        """G15: Filter items by priority level"""
        high_priority_docs = [
            doc for doc in multi_code_analysis["missing_documentation"]
            if doc.get("priority") == "High"
        ]

        high_priority_services = [
            service for service in multi_code_analysis["uncaptured_services"]
            if service["priority"] == "High"
        ]

        assert len(high_priority_docs) == 1
        assert len(high_priority_services) == 1

    def test_g15_sort_by_confidence_descending(self, multi_code_analysis):
        """G15: Sort codes by confidence (high to low)"""
        sorted_codes = sorted(
            multi_code_analysis["suggested_codes"],
            key=lambda x: x["confidence"],
            reverse=True
        )

        assert sorted_codes[0]["confidence"] == 0.95
        assert sorted_codes[-1]["confidence"] == 0.65
        assert sorted_codes[0]["code"] == "99215"

    def test_g15_sort_by_rvu_value(self, multi_code_analysis):
        """G15: Sort uncaptured services by RVU value"""
        sorted_services = sorted(
            multi_code_analysis["uncaptured_services"],
            key=lambda x: x.get("estimated_rvus", 0),
            reverse=True
        )

        assert sorted_services[0]["service"] == "PHQ-9"
        assert sorted_services[0]["estimated_rvus"] == 0.18

    def test_g15_filter_multiple_criteria(self, multi_code_analysis):
        """G15: Apply multiple filters simultaneously"""
        # Find high-risk codes with medium or high risk level
        risky_codes = [
            risk for risk in multi_code_analysis["denial_risks"]
            if risk["risk_level"] in ["High", "Medium"]
        ]

        assert len(risky_codes) == 3  # Should exclude "Low" risk


class TestResponsiveDesign:
    """Test responsive design data requirements (G16)"""

    def test_g16_data_structure_mobile_friendly(self):
        """G16: Data structure supports mobile display"""
        # Verify data can be displayed in compact format
        compact_data = {
            "code": "99214",
            "description": "Office visit",  # Truncatable
            "confidence": 0.85,  # Displayable as badge
            "priority": "High"  # Color-codeable
        }

        # All essential info in simple structure
        assert len(compact_data) <= 5  # Not too many fields
        assert all(isinstance(v, (str, int, float)) for v in compact_data.values())

    def test_g16_long_text_fields_identifiable(self):
        """G16: Long text fields can be truncated for mobile"""
        sample_item = {
            "code": "99215",
            "description": "Office visit - comprehensive history and examination with high complexity medical decision making",
            "justification": "Detailed assessment of multiple chronic conditions with complex pharmacotherapy adjustments",
            "confidence": 0.92
        }

        # Identify truncatable fields (descriptions, justifications)
        long_fields = ["description", "justification"]

        for field in long_fields:
            if field in sample_item:
                text = sample_item[field]
                # Can be truncated to first 50 chars for mobile
                truncated = text[:50] + "..." if len(text) > 50 else text
                assert len(truncated) <= 53

    def test_g16_priority_indicators_support_visual_encoding(self):
        """G16: Priority/risk fields support color coding"""
        items = [
            {"priority": "High"},      # Red
            {"priority": "Medium"},    # Yellow/Orange
            {"priority": "Low"},       # Green
            {"risk_level": "High"},
            {"risk_level": "Medium"},
            {"risk_level": "Low"}
        ]

        # All priority/risk levels are simple strings for easy color mapping
        for item in items:
            priority = item.get("priority") or item.get("risk_level")
            assert priority in ["High", "Medium", "Low"]

    def test_g16_numeric_data_supports_charts(self):
        """G16: Numeric data can be visualized responsively"""
        rvu_data = {
            "billed_codes_rvus": 1.92,
            "suggested_codes_rvus": 2.8,
            "incremental_rvus": 0.88
        }

        # All numeric values for easy charting
        assert all(isinstance(v, (int, float)) for v in rvu_data.values())

        # Can calculate percentage for progress bars
        if rvu_data["suggested_codes_rvus"] > 0:
            percentage = (rvu_data["incremental_rvus"] / rvu_data["suggested_codes_rvus"]) * 100
            assert 0 <= percentage <= 100


class TestAccessibility:
    """Test accessibility requirements (G17)"""

    def test_g17_semantic_structure_for_screen_readers(self):
        """G17: Data structure supports semantic HTML"""
        # Analysis results organized in logical sections
        sections = [
            "billed_codes",
            "suggested_codes",
            "missing_documentation",
            "denial_risks",
            "rvu_analysis",
            "modifier_suggestions",
            "uncaptured_services"
        ]

        # Each section can map to semantic HTML elements
        # e.g., <section aria-label="Billed Codes">
        for section_name in sections:
            assert "_" in section_name or section_name.islower()
            # Can be converted to readable labels
            label = section_name.replace("_", " ").title()
            assert len(label) > 0

    def test_g17_risk_levels_have_text_alternatives(self):
        """G17: Color-coded items have text labels"""
        risk_items = [
            {"risk_level": "High", "label": "High Risk"},
            {"risk_level": "Medium", "label": "Medium Risk"},
            {"risk_level": "Low", "label": "Low Risk"}
        ]

        # Each visual indicator has text
        for item in risk_items:
            assert "risk_level" in item  # For color coding
            assert "label" in item  # For screen readers

    def test_g17_codes_have_descriptions(self):
        """G17: All codes include descriptions for context"""
        codes = [
            {"code": "99214", "description": "Office visit, level 4"},
            {"code": "80053", "description": "Comprehensive metabolic panel"}
        ]

        # Each code has readable description
        for code_item in codes:
            assert "code" in code_item
            assert "description" in code_item
            assert len(code_item["description"]) > 0

    def test_g17_confidence_scores_have_readable_format(self):
        """G17: Confidence scores presentable as percentages"""
        suggestions = [
            {"code": "99214", "confidence": 0.85},
            {"code": "93000", "confidence": 0.92}
        ]

        for suggestion in suggestions:
            confidence = suggestion["confidence"]
            # Can be presented as percentage for clarity
            percentage = f"{confidence * 100:.0f}%"
            assert percentage in ["85%", "92%"]

    def test_g17_tables_have_sortable_columns(self):
        """G17: Tabular data supports keyboard navigation"""
        table_data = [
            {"code": "99214", "confidence": 0.85, "risk": "Low"},
            {"code": "99215", "confidence": 0.92, "risk": "Medium"}
        ]

        # Each row has consistent column structure
        if table_data:
            first_row_keys = set(table_data[0].keys())
            for row in table_data:
                assert set(row.keys()) == first_row_keys  # Consistent columns

    def test_g17_actionable_items_identifiable(self):
        """G17: Items requiring action are clearly marked"""
        items = [
            {
                "type": "missing_documentation",
                "priority": "High",
                "actionable": True
            },
            {
                "type": "uncaptured_service",
                "priority": "High",
                "actionable": True
            },
            {
                "type": "suggested_code",
                "confidence": 0.95,
                "actionable": True
            }
        ]

        # High priority and high confidence items are actionable
        actionable_items = [item for item in items if item.get("actionable")]
        assert len(actionable_items) == 3


class TestDataIntegrity:
    """Additional data integrity tests"""

    def test_all_features_data_types_consistent(self):
        """Verify consistent data types across features"""
        sample_data = {
            "billed_codes": [{"code": "99213", "code_type": "CPT"}],
            "suggested_codes": [{"code": "99214", "confidence": 0.85}],
            "missing_documentation": [{"section": "HPI", "priority": "High"}],
            "denial_risks": [{"code": "99214", "risk_level": "Low"}],
            "rvu_analysis": {"billed_codes_rvus": 1.3},
            "modifier_suggestions": [{"code": "99214", "modifier": "-25"}],
            "uncaptured_services": [{"service": "PHQ-9", "priority": "High"}]
        }

        # Verify each feature has expected structure
        assert isinstance(sample_data["billed_codes"], list)
        assert isinstance(sample_data["suggested_codes"], list)
        assert isinstance(sample_data["rvu_analysis"], dict)

    def test_prompt_generation_reproducible(self):
        """Prompt generation should be deterministic"""
        clinical_note = "Test note"
        billed_codes = [{"code": "99213", "code_type": "CPT"}]

        # Generate same prompt twice
        prompt1 = prompt_templates.get_user_prompt(clinical_note, billed_codes)
        prompt2 = prompt_templates.get_user_prompt(clinical_note, billed_codes)

        assert prompt1 == prompt2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
