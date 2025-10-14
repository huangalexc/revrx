"""
Tests for Enhanced Report Generator
"""

import pytest
from datetime import datetime
from app.services.enhanced_report_generator import enhanced_report_generator


@pytest.fixture
def sample_report_data():
    """Sample report data with all enhanced features"""
    return {
        "encounter_id": "test-encounter-123",
        "generated_at": datetime.utcnow().isoformat(),
        "status": "COMPLETE",
        "metadata": {
            "encounter_created": datetime.utcnow().isoformat(),
            "processing_time_ms": 5000,
            "user_email": "test@example.com",
            "phi_included": False,
            "phi_detected": True,
        },
        "clinical_note": {
            "text": "Sample clinical note [REDACTED]",
            "length": 500,
            "uploaded_files": [],
        },
        "code_analysis": {
            "billed_codes": [
                {"code": "99213", "code_type": "CPT", "description": "Office visit, low complexity"}
            ],
            "suggested_codes": [
                {
                    "code": "99214",
                    "code_type": "CPT",
                    "description": "Office visit, moderate complexity",
                    "comparison_type": "upgrade",
                    "revenue_impact": 50.00,
                    "confidence": 0.85,
                    "justification": "Documentation supports moderate complexity",
                    "supporting_text": ["Patient has 3 chronic conditions"]
                }
            ],
            "ai_model": "gpt-4",
            "confidence_score": 0.85,
        },
        "revenue_analysis": {
            "incremental_revenue": 50.00,
            "currency": "USD",
            "calculation_method": "Medicare 2024",
        },
        "summary": {
            "total_billed_codes": 1,
            "total_suggested_codes": 1,
            "new_code_opportunities": 0,
            "upgrade_opportunities": 1,
        },
        "missing_documentation": [
            {
                "section": "History of Present Illness",
                "issue": "Duration not specified",
                "suggestion": "Add specific timeline",
                "priority": "High",
            }
        ],
        "denial_risks": [
            {
                "code": "99214",
                "risk_level": "Low",
                "denial_reasons": ["Insufficient MDM", "Missing time"],
                "documentation_addresses_risks": True,
                "mitigation_notes": "MDM clearly documented",
            }
        ],
        "rvu_analysis": {
            "billed_codes_rvus": 1.3,
            "suggested_codes_rvus": 1.92,
            "incremental_rvus": 0.62,
            "billed_code_details": [
                {"code": "99213", "rvus": 1.3, "description": "Office visit, low complexity"}
            ],
            "suggested_code_details": [
                {"code": "99214", "rvus": 1.92, "description": "Office visit, moderate complexity"}
            ],
        },
        "modifier_suggestions": [
            {
                "code": "99214",
                "modifier": "-25",
                "justification": "Separate E/M service",
                "documentation_support": "Clear separate documentation",
            }
        ],
        "uncaptured_services": [
            {
                "service": "Depression screening",
                "location_in_note": "Assessment section",
                "suggested_codes": ["96127"],
                "priority": "High",
                "justification": "PHQ-9 administered",
                "estimated_rvus": 0.18,
            }
        ],
        "audit_metadata": {
            "total_codes_identified": 2,
            "high_confidence_codes": 1,
            "documentation_quality_score": 0.82,
            "compliance_flags": [],
            "timestamp": datetime.utcnow().isoformat(),
        },
    }


class TestCSVGeneration:
    """Test CSV export functionality"""

    def test_generate_csv_basic(self, sample_report_data):
        """Test basic CSV generation"""
        csv_output = enhanced_report_generator.generate_csv(sample_report_data)

        assert "RevRX - Medical Coding Analysis Report" in csv_output
        assert sample_report_data["encounter_id"] in csv_output
        assert "COMPLETE" in csv_output

    def test_csv_includes_summary(self, sample_report_data):
        """Test CSV includes summary section"""
        csv_output = enhanced_report_generator.generate_csv(sample_report_data)

        assert "=== SUMMARY ===" in csv_output
        assert "Total Billed Codes: 1" in csv_output
        assert "Incremental Revenue: $50.00" in csv_output

    def test_csv_includes_billed_codes(self, sample_report_data):
        """Test CSV includes billed codes"""
        csv_output = enhanced_report_generator.generate_csv(sample_report_data)

        assert "=== BILLED CODES ===" in csv_output
        assert "99213" in csv_output
        assert "CPT" in csv_output

    def test_csv_includes_suggested_codes(self, sample_report_data):
        """Test CSV includes suggested codes"""
        csv_output = enhanced_report_generator.generate_csv(sample_report_data)

        assert "=== SUGGESTED CODES ===" in csv_output
        assert "99214" in csv_output
        assert "85%" in csv_output  # Confidence
        assert "$50.00" in csv_output  # Revenue impact

    def test_csv_includes_documentation_quality(self, sample_report_data):
        """Test CSV includes documentation quality section"""
        csv_output = enhanced_report_generator.generate_csv(sample_report_data)

        assert "=== DOCUMENTATION QUALITY ===" in csv_output
        assert "Quality Score: 82%" in csv_output
        assert "High" in csv_output  # Priority
        assert "History of Present Illness" in csv_output

    def test_csv_includes_denial_risk(self, sample_report_data):
        """Test CSV includes denial risk section"""
        csv_output = enhanced_report_generator.generate_csv(sample_report_data)

        assert "=== DENIAL RISK ANALYSIS ===" in csv_output
        assert "99214" in csv_output
        assert "Low" in csv_output
        assert "Yes" in csv_output  # Addressed

    def test_csv_includes_rvu_analysis(self, sample_report_data):
        """Test CSV includes RVU analysis"""
        csv_output = enhanced_report_generator.generate_csv(sample_report_data)

        assert "=== RVU ANALYSIS ===" in csv_output
        assert "Billed RVUs: 1.30" in csv_output
        assert "Suggested RVUs: 1.92" in csv_output
        assert "Incremental RVUs: 0.62" in csv_output

    def test_csv_includes_modifier_suggestions(self, sample_report_data):
        """Test CSV includes modifier suggestions"""
        csv_output = enhanced_report_generator.generate_csv(sample_report_data)

        assert "=== MODIFIER SUGGESTIONS ===" in csv_output
        assert "-25" in csv_output
        assert "Separate E/M service" in csv_output

    def test_csv_includes_uncaptured_services(self, sample_report_data):
        """Test CSV includes uncaptured services"""
        csv_output = enhanced_report_generator.generate_csv(sample_report_data)

        assert "=== UNCAPTURED SERVICES ===" in csv_output
        assert "Depression screening" in csv_output
        assert "96127" in csv_output
        assert "High" in csv_output

    def test_csv_includes_compliance_notice(self, sample_report_data):
        """Test CSV includes compliance notice"""
        csv_output = enhanced_report_generator.generate_csv(sample_report_data)

        assert "=== COMPLIANCE NOTICE ===" in csv_output
        assert "informational purposes only" in csv_output
        assert "HIPAA compliance" in csv_output

    def test_csv_phi_redaction_notice(self, sample_report_data):
        """Test CSV shows PHI redaction status"""
        csv_output = enhanced_report_generator.generate_csv(sample_report_data)

        assert "PHI Redacted: True" in csv_output
        assert "PHI has been redacted" in csv_output


class TestEnhancedHTMLGeneration:
    """Test enhanced HTML export functionality"""

    def test_generate_html_basic(self, sample_report_data):
        """Test basic HTML generation"""
        html_output = enhanced_report_generator.generate_enhanced_html(sample_report_data)

        assert "<!DOCTYPE html>" in html_output
        assert "Enhanced Coding Review Report" in html_output
        assert sample_report_data["encounter_id"] in html_output

    def test_html_includes_watermark(self, sample_report_data):
        """Test HTML includes watermark"""
        html_output = enhanced_report_generator.generate_enhanced_html(sample_report_data)

        assert "CONFIDENTIAL MEDICAL CODING ANALYSIS" in html_output
        assert "PHI Redacted: Yes" in html_output

    def test_html_includes_summary_cards(self, sample_report_data):
        """Test HTML includes summary cards"""
        html_output = enhanced_report_generator.generate_enhanced_html(sample_report_data)

        assert "$50.00" in html_output  # Revenue
        assert "85%" in html_output  # Confidence

    def test_html_includes_code_comparison(self, sample_report_data):
        """Test HTML includes code comparison table"""
        html_output = enhanced_report_generator.generate_enhanced_html(sample_report_data)

        assert "Code Comparison" in html_output
        assert "99214" in html_output
        assert "upgrade" in html_output.lower()

    def test_html_includes_documentation_quality(self, sample_report_data):
        """Test HTML includes documentation quality section"""
        html_output = enhanced_report_generator.generate_enhanced_html(sample_report_data)

        assert "Documentation Quality Analysis" in html_output
        assert "History of Present Illness" in html_output

    def test_html_includes_denial_risk(self, sample_report_data):
        """Test HTML includes denial risk section"""
        html_output = enhanced_report_generator.generate_enhanced_html(sample_report_data)

        assert "Denial Risk Analysis" in html_output
        assert "99214" in html_output

    def test_html_includes_rvu_analysis(self, sample_report_data):
        """Test HTML includes RVU analysis"""
        html_output = enhanced_report_generator.generate_enhanced_html(sample_report_data)

        assert "RVU Analysis" in html_output
        assert "1.30" in html_output  # Billed RVUs
        assert "1.92" in html_output  # Suggested RVUs

    def test_html_includes_modifier_suggestions(self, sample_report_data):
        """Test HTML includes modifier suggestions"""
        html_output = enhanced_report_generator.generate_enhanced_html(sample_report_data)

        assert "Modifier Suggestions" in html_output
        assert "-25" in html_output

    def test_html_includes_uncaptured_services(self, sample_report_data):
        """Test HTML includes uncaptured services"""
        html_output = enhanced_report_generator.generate_enhanced_html(sample_report_data)

        assert "Uncaptured Services" in html_output or "Charge Capture" in html_output
        assert "Depression screening" in html_output

    def test_html_includes_compliance_notice(self, sample_report_data):
        """Test HTML includes compliance notice"""
        html_output = enhanced_report_generator.generate_enhanced_html(sample_report_data)

        assert "COMPLIANCE NOTICE" in html_output
        assert "informational purposes only" in html_output

    def test_html_includes_styling(self, sample_report_data):
        """Test HTML includes CSS styling"""
        html_output = enhanced_report_generator.generate_enhanced_html(sample_report_data)

        assert "<style>" in html_output
        assert ".container" in html_output
        assert ".badge" in html_output

    def test_html_badge_styling(self, sample_report_data):
        """Test HTML includes badge color classes"""
        html_output = enhanced_report_generator.generate_enhanced_html(sample_report_data)

        assert "badge-high" in html_output or "badge-low" in html_output
        assert ".badge-new" in html_output or ".badge-upgrade" in html_output


class TestEmptyData:
    """Test handling of missing optional data"""

    def test_csv_without_optional_features(self, sample_report_data):
        """Test CSV generation without optional features"""
        # Remove optional features
        del sample_report_data["missing_documentation"]
        del sample_report_data["denial_risks"]
        del sample_report_data["rvu_analysis"]
        del sample_report_data["modifier_suggestions"]
        del sample_report_data["uncaptured_services"]

        csv_output = enhanced_report_generator.generate_csv(sample_report_data)

        # Should still generate without errors
        assert "RevRX - Medical Coding Analysis Report" in csv_output
        assert "=== SUMMARY ===" in csv_output

    def test_html_without_optional_features(self, sample_report_data):
        """Test HTML generation without optional features"""
        # Remove optional features
        del sample_report_data["missing_documentation"]
        del sample_report_data["denial_risks"]

        html_output = enhanced_report_generator.generate_enhanced_html(sample_report_data)

        # Should still generate without errors
        assert "<!DOCTYPE html>" in html_output
        assert "Enhanced Coding Review Report" in html_output


class TestPHIRedaction:
    """Test PHI redaction indicators"""

    def test_csv_phi_indicators(self, sample_report_data):
        """Test CSV shows correct PHI status"""
        csv_output = enhanced_report_generator.generate_csv(sample_report_data)

        assert "PHI Redacted: True" in csv_output
        assert "PHI has been redacted" in csv_output

    def test_html_phi_watermark(self, sample_report_data):
        """Test HTML watermark shows PHI status"""
        html_output = enhanced_report_generator.generate_enhanced_html(sample_report_data)

        assert "PHI Redacted: Yes" in html_output

    def test_csv_with_phi_included(self, sample_report_data):
        """Test CSV when PHI is included"""
        sample_report_data["metadata"]["phi_included"] = True

        csv_output = enhanced_report_generator.generate_csv(sample_report_data)

        assert "PHI Redacted: False" in csv_output

    def test_html_with_phi_included(self, sample_report_data):
        """Test HTML when PHI is included"""
        sample_report_data["metadata"]["phi_included"] = True

        html_output = enhanced_report_generator.generate_enhanced_html(sample_report_data)

        assert "PHI Redacted: No" in html_output
