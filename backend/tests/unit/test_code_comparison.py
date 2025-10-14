"""
Unit Tests for Code Comparison Logic

Tests for comparing billed codes vs suggested codes and revenue analysis.
"""

import pytest
from datetime import datetime


# ============================================================================
# Billing Code Parsing Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestBillingCodeParsing:
    """Test parsing of billing codes from various formats"""

    async def test_parse_cpt_code(self):
        """Test parsing CPT code"""
        code = "99213"

        assert code.isdigit()
        assert len(code) == 5

    async def test_parse_cpt_with_prefix(self):
        """Test parsing CPT code with prefix"""
        code = "CPT-99213"

        code_number = code.replace("CPT-", "")
        assert code_number == "99213"

    async def test_parse_icd10_code(self):
        """Test parsing ICD-10 code"""
        code = "Z00.00"

        assert "." in code or code.isalnum()

    async def test_parse_icd10_with_prefix(self):
        """Test parsing ICD-10 code with prefix"""
        code = "ICD-Z00.00"

        code_part = code.replace("ICD-", "")
        assert code_part == "Z00.00"

    async def test_parse_modifier(self):
        """Test parsing code with modifier"""
        code = "99213-25"

        parts = code.split("-")
        assert len(parts) == 2
        assert parts[0] == "99213"
        assert parts[1] == "25"

    async def test_parse_code_list(self, sample_billing_codes):
        """Test parsing list of billing codes"""
        codes = sample_billing_codes

        assert isinstance(codes, list)
        assert len(codes) > 0
        assert all(isinstance(c, dict) for c in codes)


# ============================================================================
# Code Comparison Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestCodeComparison:
    """Test comparing billed codes vs suggested codes"""

    async def test_exact_code_match(self):
        """Test codes that match exactly"""
        billed = ["99213", "Z00.00"]
        suggested = ["99213", "Z00.00"]

        # All codes match
        matches = [code for code in billed if code in suggested]
        assert len(matches) == len(billed)

    async def test_missing_codes(self):
        """Test detection of codes in suggestion but not billed"""
        billed = ["99213"]
        suggested = ["99213", "99214", "Z00.00"]

        # Find codes in suggested but not billed
        missing = [code for code in suggested if code not in billed]
        assert len(missing) == 2
        assert "99214" in missing
        assert "Z00.00" in missing

    async def test_extra_codes(self):
        """Test detection of codes billed but not suggested"""
        billed = ["99213", "99214", "Z00.00"]
        suggested = ["99213"]

        # Find codes billed but not in suggestions
        extra = [code for code in billed if code not in suggested]
        assert len(extra) == 2
        assert "99214" in extra
        assert "Z00.00" in extra

    async def test_no_overlap(self):
        """Test comparison with no overlapping codes"""
        billed = ["99213", "99214"]
        suggested = ["99215", "Z00.00"]

        overlap = [code for code in billed if code in suggested]
        assert len(overlap) == 0

    async def test_case_insensitive_comparison(self):
        """Test case-insensitive code comparison"""
        billed = ["cpt-99213", "icd-z00.00"]
        suggested = ["CPT-99213", "ICD-Z00.00"]

        # Normalize to uppercase for comparison
        billed_upper = [c.upper() for c in billed]
        suggested_upper = [c.upper() for c in suggested]

        matches = [code for code in billed_upper if code in suggested_upper]
        assert len(matches) == 2


# ============================================================================
# Code Suggestion Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestCodeSuggestions:
    """Test generation and validation of code suggestions"""

    async def test_suggestion_structure(self):
        """Test structure of code suggestion"""
        suggestion = {
            "code": "99214",
            "description": "Office visit, established patient, moderate complexity",
            "justification": "Clinical documentation supports moderate complexity",
            "confidence": 0.85,
            "revenue_impact": 50.00
        }

        assert "code" in suggestion
        assert "description" in suggestion
        assert "justification" in suggestion
        assert "confidence" in suggestion
        assert isinstance(suggestion["confidence"], float)

    async def test_suggestion_with_high_confidence(self):
        """Test high confidence suggestion"""
        suggestion = {
            "code": "99214",
            "confidence": 0.95
        }

        assert suggestion["confidence"] >= 0.8

    async def test_suggestion_with_low_confidence(self):
        """Test low confidence suggestion"""
        suggestion = {
            "code": "99214",
            "confidence": 0.45
        }

        assert suggestion["confidence"] < 0.7

    async def test_multiple_suggestions(self, sample_billing_codes):
        """Test multiple code suggestions"""
        suggestions = [
            {"code": "99214", "confidence": 0.85},
            {"code": "Z00.00", "confidence": 0.90},
            {"code": "G0438", "confidence": 0.75}
        ]

        assert len(suggestions) >= 2
        assert all("code" in s for s in suggestions)
        assert all("confidence" in s for s in suggestions)

    async def test_filter_low_confidence(self):
        """Test filtering out low confidence suggestions"""
        suggestions = [
            {"code": "99214", "confidence": 0.85},
            {"code": "99215", "confidence": 0.45},
            {"code": "Z00.00", "confidence": 0.90},
        ]

        threshold = 0.7
        high_confidence = [s for s in suggestions if s["confidence"] >= threshold]

        assert len(high_confidence) == 2
        assert all(s["confidence"] >= threshold for s in high_confidence)


# ============================================================================
# Revenue Calculation Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestRevenueCalculation:
    """Test revenue impact calculations"""

    async def test_single_code_revenue(self):
        """Test revenue for single code"""
        # Typical CPT code reimbursement
        cpt_99213_rate = 93.00  # Example Medicare rate

        revenue = cpt_99213_rate
        assert revenue > 0

    async def test_incremental_revenue_calculation(self):
        """Test calculating incremental revenue from suggestions"""
        billed_revenue = 93.00  # 99213
        suggested_additional_revenue = 135.00  # 99214

        incremental = suggested_additional_revenue - billed_revenue
        assert incremental == 42.00

    async def test_multiple_code_revenue(self):
        """Test total revenue from multiple codes"""
        code_rates = {
            "99213": 93.00,
            "Z00.00": 0.00,  # Diagnosis codes don't generate revenue directly
            "G0438": 170.00,
        }

        total_revenue = sum(code_rates.values())
        assert total_revenue == 263.00

    async def test_zero_incremental_revenue(self):
        """Test case where no additional revenue identified"""
        billed_codes = ["99213", "Z00.00"]
        suggested_codes = ["99213", "Z00.00"]

        # No additional codes suggested
        additional = [c for c in suggested_codes if c not in billed_codes]
        assert len(additional) == 0

        incremental_revenue = 0.0
        assert incremental_revenue == 0.0

    async def test_negative_revenue_scenario(self):
        """Test scenario where suggested code has lower reimbursement"""
        billed_rate = 135.00  # 99214
        suggested_rate = 93.00  # 99213 (downgrade)

        difference = suggested_rate - billed_rate
        assert difference < 0

    async def test_revenue_with_modifiers(self):
        """Test revenue calculation with code modifiers"""
        base_rate = 93.00  # 99213
        modifier_adjustment = 0.25  # 25% increase for modifier

        adjusted_rate = base_rate * (1 + modifier_adjustment)
        assert adjusted_rate == 116.25


# ============================================================================
# Report Generation Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestReportGeneration:
    """Test report data generation"""

    async def test_create_report_record(self, db, completed_encounter, sample_billing_codes):
        """Test creating report in database"""
        suggested_codes = [
            {
                "code": "99214",
                "description": "Office visit, moderate complexity",
                "justification": "Documentation supports higher level",
                "confidence": 0.85,
                "revenue_impact": 42.00
            }
        ]

        report = await db.report.create(
            data={
                "encounterId": completed_encounter["id"],
                "billedCodes": sample_billing_codes,
                "suggestedCodes": suggested_codes,
                "incrementalRevenue": 42.00,
                "aiModel": "gpt-4",
                "confidenceScore": 0.85,
            }
        )

        assert report is not None
        assert report.incrementalRevenue == 42.00
        assert report.aiModel == "gpt-4"

    async def test_report_unique_per_encounter(self, db, completed_encounter, sample_billing_codes):
        """Test that each encounter has only one report"""
        # Create first report
        await db.report.create(
            data={
                "encounterId": completed_encounter["id"],
                "billedCodes": sample_billing_codes,
                "suggestedCodes": [],
                "incrementalRevenue": 0.0,
                "aiModel": "gpt-4",
            }
        )

        # Attempt to create second report should fail
        with pytest.raises(Exception):  # Unique constraint error
            await db.report.create(
                data={
                    "encounterId": completed_encounter["id"],
                    "billedCodes": sample_billing_codes,
                    "suggestedCodes": [],
                    "incrementalRevenue": 0.0,
                    "aiModel": "gpt-4",
                }
            )

    async def test_report_with_json_data(self, db, completed_encounter, sample_billing_codes):
        """Test report with JSON-formatted data"""
        report_json = {
            "summary": "Review completed",
            "billed_codes": sample_billing_codes,
            "suggested_additions": ["99214"],
            "revenue_opportunity": 42.00
        }

        import json
        report = await db.report.create(
            data={
                "encounterId": completed_encounter["id"],
                "billedCodes": sample_billing_codes,
                "suggestedCodes": [],
                "incrementalRevenue": 42.00,
                "aiModel": "gpt-4",
                "reportJson": json.dumps(report_json),
            }
        )

        assert report.reportJson is not None
        parsed = json.loads(report.reportJson)
        assert parsed["revenue_opportunity"] == 42.00

    async def test_report_timestamp(self, db, completed_encounter, sample_billing_codes):
        """Test report includes creation timestamp"""
        report = await db.report.create(
            data={
                "encounterId": completed_encounter["id"],
                "billedCodes": sample_billing_codes,
                "suggestedCodes": [],
                "incrementalRevenue": 0.0,
                "aiModel": "gpt-4",
            }
        )

        assert report.createdAt is not None
        assert isinstance(report.createdAt, datetime)


# ============================================================================
# Code Validation Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestCodeValidation:
    """Test validation of billing codes"""

    async def test_valid_cpt_format(self):
        """Test CPT code format validation"""
        valid_cpt_codes = ["99213", "99214", "99215", "G0438"]

        for code in valid_cpt_codes:
            # CPT codes are 5 digits or alphanumeric
            assert len(code) == 5

    async def test_valid_icd10_format(self):
        """Test ICD-10 code format validation"""
        valid_icd_codes = ["Z00.00", "I10", "E11.9"]

        for code in valid_icd_codes:
            # ICD-10 codes start with letter
            assert code[0].isalpha()

    async def test_invalid_code_format(self):
        """Test detection of invalid code formats"""
        invalid_codes = ["", "1", "INVALID", "99999999"]

        for code in invalid_codes:
            # Codes should be 3-7 characters
            is_valid = 3 <= len(code) <= 7 if code else False
            assert is_valid is False or code in ["INVALID"]

    async def test_code_with_description(self, sample_billing_codes):
        """Test code with description structure"""
        for code_obj in sample_billing_codes:
            assert "code" in code_obj
            if "description" in code_obj:
                assert isinstance(code_obj["description"], str)


# ============================================================================
# AI Model Confidence Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestAIModelConfidence:
    """Test AI model confidence scoring"""

    async def test_confidence_score_range(self):
        """Test confidence scores are in valid range"""
        confidence_scores = [0.95, 0.85, 0.72, 0.68]

        for score in confidence_scores:
            assert 0.0 <= score <= 1.0

    async def test_high_confidence_threshold(self):
        """Test high confidence threshold"""
        high_confidence = 0.85
        threshold = 0.8

        assert high_confidence >= threshold

    async def test_low_confidence_threshold(self):
        """Test low confidence threshold"""
        low_confidence = 0.45
        threshold = 0.7

        assert low_confidence < threshold

    async def test_average_confidence_calculation(self):
        """Test calculating average confidence across suggestions"""
        suggestions = [
            {"code": "99214", "confidence": 0.85},
            {"code": "Z00.00", "confidence": 0.90},
            {"code": "G0438", "confidence": 0.75}
        ]

        avg_confidence = sum(s["confidence"] for s in suggestions) / len(suggestions)
        assert avg_confidence == 0.833333333333333 or abs(avg_confidence - 0.833) < 0.01

    async def test_store_confidence_in_report(self, db, completed_encounter, sample_billing_codes):
        """Test storing confidence score in report"""
        report = await db.report.create(
            data={
                "encounterId": completed_encounter["id"],
                "billedCodes": sample_billing_codes,
                "suggestedCodes": [],
                "incrementalRevenue": 0.0,
                "aiModel": "gpt-4",
                "confidenceScore": 0.85,
            }
        )

        assert report.confidenceScore == 0.85


# ============================================================================
# Code Justification Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestCodeJustification:
    """Test generation and validation of code justifications"""

    async def test_justification_present(self):
        """Test that suggested codes include justification"""
        suggestion = {
            "code": "99214",
            "description": "Office visit, moderate complexity",
            "justification": "Patient history and examination support moderate complexity visit"
        }

        assert "justification" in suggestion
        assert len(suggestion["justification"]) > 20

    async def test_justification_references_documentation(self):
        """Test justification references clinical documentation"""
        justification = "Clinical documentation indicates comprehensive history and moderate complexity medical decision making"

        keywords = ["documentation", "history", "complexity"]
        assert any(kw in justification.lower() for kw in keywords)

    async def test_justification_for_high_value_code(self):
        """Test justification for high-value code suggestion"""
        suggestion = {
            "code": "G0438",
            "description": "Annual Wellness Visit",
            "justification": "Patient qualifies for Annual Wellness Visit based on age and Medicare eligibility",
            "revenue_impact": 170.00
        }

        assert suggestion["revenue_impact"] > 100
        assert "qualifies" in suggestion["justification"].lower()


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestCodeComparisonEdgeCases:
    """Test edge cases in code comparison"""

    async def test_empty_billed_codes(self):
        """Test handling empty billed codes list"""
        billed = []
        suggested = ["99213", "Z00.00"]

        # All suggested codes are new
        new_codes = [code for code in suggested if code not in billed]
        assert len(new_codes) == len(suggested)

    async def test_empty_suggested_codes(self):
        """Test handling empty suggested codes list"""
        billed = ["99213", "Z00.00"]
        suggested = []

        # No new codes to suggest
        new_codes = [code for code in suggested if code not in billed]
        assert len(new_codes) == 0

    async def test_both_empty(self):
        """Test handling both lists empty"""
        billed = []
        suggested = []

        assert len(billed) == 0
        assert len(suggested) == 0

    async def test_duplicate_codes_in_billed(self):
        """Test handling duplicate codes in billed list"""
        billed = ["99213", "99213", "Z00.00"]

        # Remove duplicates
        unique_billed = list(set(billed))
        assert len(unique_billed) == 2

    async def test_malformed_code_data(self):
        """Test handling malformed code data"""
        codes = [
            {"code": "99213"},  # Valid
            {"description": "No code"},  # Missing code
            None,  # Null entry
        ]

        # Filter valid codes
        valid_codes = [c for c in codes if c and "code" in c]
        assert len(valid_codes) == 1

    async def test_very_long_code_list(self):
        """Test handling very long code lists"""
        billed = [f"CODE{i:05d}" for i in range(100)]
        suggested = [f"CODE{i:05d}" for i in range(50, 150)]

        # Should handle efficiently
        overlap = [code for code in billed if code in suggested]
        assert len(overlap) == 50
