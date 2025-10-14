"""
Unit tests for prompt template formatting and structure (Track G1)

Tests verify:
- Prompt structure and completeness
- JSON format requirements
- All feature sections present
- Token efficiency
- Proper formatting of user and system prompts
"""

import pytest
import json
import re
from app.services.prompt_templates import PromptTemplates, prompt_templates


class TestPromptStructure:
    """Test basic prompt structure and format"""

    def test_system_prompt_exists(self):
        """System prompt should return non-empty string"""
        system_prompt = PromptTemplates.get_system_prompt()
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0

    def test_system_prompt_contains_role_description(self):
        """System prompt should describe the AI role"""
        system_prompt = PromptTemplates.get_system_prompt()
        assert "medical coding specialist" in system_prompt.lower()
        assert "CPT" in system_prompt
        assert "ICD-10" in system_prompt

    def test_system_prompt_has_json_format(self):
        """System prompt should include JSON response format"""
        system_prompt = PromptTemplates.get_system_prompt()
        assert "JSON" in system_prompt or "json" in system_prompt
        assert "billed_codes" in system_prompt
        assert "suggested_codes" in system_prompt

    def test_system_prompt_includes_all_feature_fields(self):
        """System prompt should include all feature expansion fields"""
        system_prompt = PromptTemplates.get_system_prompt()

        # Check all required fields from feature expansion
        required_fields = [
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

        for field in required_fields:
            assert field in system_prompt, f"Missing field: {field}"

    def test_user_prompt_with_empty_billed_codes(self):
        """User prompt should handle empty billed codes"""
        clinical_note = "Patient presents with acute bronchitis."
        user_prompt = PromptTemplates.get_user_prompt(clinical_note, [])

        assert isinstance(user_prompt, str)
        assert len(user_prompt) > 0
        assert clinical_note in user_prompt
        assert "None provided" in user_prompt or "No codes" in user_prompt

    def test_user_prompt_with_billed_codes(self):
        """User prompt should properly format billed codes"""
        clinical_note = "Patient presents with acute bronchitis."
        billed_codes = [
            {"code": "99213", "code_type": "CPT", "description": "Office visit, level 3"}
        ]
        user_prompt = PromptTemplates.get_user_prompt(clinical_note, billed_codes)

        assert "99213" in user_prompt
        assert "CPT" in user_prompt
        assert clinical_note in user_prompt

    def test_user_prompt_formats_multiple_codes(self):
        """User prompt should format multiple billed codes correctly"""
        clinical_note = "Test note"
        billed_codes = [
            {"code": "99213", "code_type": "CPT", "description": "Office visit"},
            {"code": "J13", "code_type": "ICD-10", "description": "Pneumonia"}
        ]
        user_prompt = PromptTemplates.get_user_prompt(clinical_note, billed_codes)

        assert "99213" in user_prompt
        assert "J13" in user_prompt
        assert user_prompt.count("-") >= 2  # At least 2 bullet points


class TestFeatureSections:
    """Test individual feature section prompts"""

    def test_documentation_quality_section(self):
        """Documentation quality prompt section should be complete"""
        section = PromptTemplates.get_documentation_quality_prompt_section()

        assert isinstance(section, str)
        assert "missing documentation" in section.lower()
        assert "section" in section
        assert "issue" in section
        assert "suggestion" in section
        assert "priority" in section.lower()

    def test_denial_risk_section(self):
        """Denial risk prompt section should be complete"""
        section = PromptTemplates.get_denial_risk_prompt_section()

        assert isinstance(section, str)
        assert "denial" in section.lower()
        assert "risk_level" in section or "risk level" in section.lower()
        assert "Low" in section and "Medium" in section and "High" in section
        assert "denial_reasons" in section or "denial reasons" in section.lower()

    def test_rvu_analysis_section(self):
        """RVU analysis prompt section should include RVU values"""
        section = PromptTemplates.get_rvu_analysis_prompt_section()

        assert isinstance(section, str)
        assert "RVU" in section
        assert "99213" in section  # Example code
        assert "1.3" in section or "1.92" in section  # RVU values
        assert "billed_codes_rvus" in section
        assert "suggested_codes_rvus" in section
        assert "incremental_rvus" in section

    def test_modifier_suggestions_section(self):
        """Modifier suggestions prompt section should list common modifiers"""
        section = PromptTemplates.get_modifier_suggestions_prompt_section()

        assert isinstance(section, str)
        assert "modifier" in section.lower()
        assert "-25" in section
        assert "-59" in section
        assert "justification" in section

    def test_charge_capture_section(self):
        """Charge capture prompt section should identify uncaptured services"""
        section = PromptTemplates.get_charge_capture_prompt_section()

        assert isinstance(section, str)
        assert "uncaptured" in section.lower() or "charge capture" in section.lower()
        assert "service" in section
        assert "suggested_codes" in section or "codes" in section
        assert "priority" in section.lower()

    def test_audit_compliance_section(self):
        """Audit compliance prompt section should include metadata requirements"""
        section = PromptTemplates.get_audit_compliance_prompt_section()

        assert isinstance(section, str)
        assert "audit" in section.lower()
        assert "timestamp" in section
        assert "compliance" in section.lower()


class TestPromptContent:
    """Test prompt content for specific requirements"""

    def test_system_prompt_defines_confidence_scores(self):
        """System prompt should define confidence score ranges"""
        system_prompt = PromptTemplates.get_system_prompt()

        # Check for confidence score guidelines
        assert "confidence" in system_prompt.lower()
        assert "0.9" in system_prompt or "0.8" in system_prompt
        assert "0.0-1.0" in system_prompt or "0.0 to 1.0" in system_prompt

    def test_user_prompt_requests_all_features(self):
        """User prompt should request all 7 feature categories"""
        user_prompt = PromptTemplates.get_user_prompt("Test note", [])

        features = [
            "CODE",  # Code extraction
            "DOCUMENTATION",  # Documentation quality
            "DENIAL",  # Denial risk
            "RVU",  # RVU analysis
            "MODIFIER",  # Modifier suggestions
            "CHARGE CAPTURE" or "UNCAPTURED",  # Charge capture
            "AUDIT"  # Audit compliance
        ]

        # At least 6 of 7 features should be mentioned
        found_features = sum(1 for f in features if f in user_prompt.upper())
        assert found_features >= 6, f"Only found {found_features} of 7 features"

    def test_system_prompt_includes_description_format(self):
        """System prompt should specify description format"""
        system_prompt = PromptTemplates.get_system_prompt()

        # Should specify format like "CPT 99213: Description"
        assert "CODE_TYPE CODE:" in system_prompt or "CPT CODE:" in system_prompt

    def test_user_prompt_includes_bundling_reminder(self):
        """User prompt should remind about bundling rules"""
        user_prompt = PromptTemplates.get_user_prompt("Test note", [])

        assert "bundl" in user_prompt.lower()

    def test_combined_prompt_is_concise(self):
        """Combined analysis prompt should be token-efficient"""
        combined = PromptTemplates.get_combined_analysis_prompt()

        assert isinstance(combined, str)
        assert len(combined) < 2000  # Should be under 2000 chars for efficiency
        assert "1." in combined or "2." in combined  # Numbered list


class TestPromptFormatting:
    """Test prompt formatting and structure"""

    def test_user_prompt_separates_sections(self):
        """User prompt should have clear section headers"""
        user_prompt = PromptTemplates.get_user_prompt("Test note", [])

        # Should have section headers (typically in CAPS or with colons)
        section_pattern = r'[A-Z\s]{10,}:'
        sections = re.findall(section_pattern, user_prompt)
        assert len(sections) >= 5, "Should have at least 5 major sections"

    def test_billed_codes_formatting(self):
        """Billed codes should be formatted with bullets"""
        billed_codes = [
            {"code": "99213", "code_type": "CPT", "description": "Visit"},
            {"code": "80053", "code_type": "CPT", "description": "Panel"}
        ]
        user_prompt = PromptTemplates.get_user_prompt("Test", billed_codes)

        # Should use bullet points or dashes
        assert user_prompt.count("-") >= 2 or user_prompt.count("•") >= 2

    def test_system_prompt_has_json_example(self):
        """System prompt should include JSON example structure"""
        system_prompt = PromptTemplates.get_system_prompt()

        # Should have opening and closing braces for JSON
        assert "{" in system_prompt
        assert "}" in system_prompt
        assert system_prompt.count("{") >= 3  # Multiple nested objects


class TestPromptValidation:
    """Test prompt validation and error handling"""

    def test_user_prompt_handles_none_description(self):
        """User prompt should handle missing code descriptions"""
        billed_codes = [
            {"code": "99213", "code_type": "CPT"}  # No description
        ]
        user_prompt = PromptTemplates.get_user_prompt("Test", billed_codes)

        assert "99213" in user_prompt
        # Should handle gracefully, not crash

    def test_user_prompt_handles_missing_code_type(self):
        """User prompt should handle missing code type"""
        billed_codes = [
            {"code": "99213", "description": "Visit"}  # No code_type
        ]
        user_prompt = PromptTemplates.get_user_prompt("Test", billed_codes)

        assert "99213" in user_prompt
        # Should show N/A or similar

    def test_empty_clinical_note(self):
        """User prompt should handle empty clinical note"""
        user_prompt = PromptTemplates.get_user_prompt("", [])

        assert isinstance(user_prompt, str)
        assert len(user_prompt) > 0

    def test_very_long_clinical_note(self):
        """User prompt should handle very long clinical notes"""
        long_note = "Test sentence. " * 1000  # ~15,000 characters
        user_prompt = PromptTemplates.get_user_prompt(long_note, [])

        assert long_note in user_prompt
        assert isinstance(user_prompt, str)


class TestPromptConsistency:
    """Test consistency across different prompt methods"""

    def test_singleton_instance(self):
        """Exported prompt_templates should be usable"""
        assert prompt_templates is not None
        system_prompt = prompt_templates.get_system_prompt()
        assert isinstance(system_prompt, str)

    def test_static_methods_accessible(self):
        """All static methods should be accessible"""
        methods = [
            'get_system_prompt',
            'get_user_prompt',
            'get_documentation_quality_prompt_section',
            'get_denial_risk_prompt_section',
            'get_rvu_analysis_prompt_section',
            'get_modifier_suggestions_prompt_section',
            'get_charge_capture_prompt_section',
            'get_audit_compliance_prompt_section',
            'get_combined_analysis_prompt'
        ]

        for method_name in methods:
            assert hasattr(PromptTemplates, method_name)

    def test_feature_sections_non_empty(self):
        """All feature section methods should return non-empty strings"""
        methods = [
            PromptTemplates.get_documentation_quality_prompt_section,
            PromptTemplates.get_denial_risk_prompt_section,
            PromptTemplates.get_rvu_analysis_prompt_section,
            PromptTemplates.get_modifier_suggestions_prompt_section,
            PromptTemplates.get_charge_capture_prompt_section,
            PromptTemplates.get_audit_compliance_prompt_section
        ]

        for method in methods:
            result = method()
            assert isinstance(result, str)
            assert len(result) > 50  # Should be substantial


class TestPromptCompleteness:
    """Test that prompts include all required guidance"""

    def test_system_prompt_has_guidelines(self):
        """System prompt should include core guidelines"""
        system_prompt = PromptTemplates.get_system_prompt()

        assert "guideline" in system_prompt.lower() or "core" in system_prompt.lower()
        # Should have numbered or bulleted guidelines
        assert "1." in system_prompt or "2." in system_prompt

    def test_user_prompt_has_important_reminders(self):
        """User prompt should include important reminders"""
        user_prompt = PromptTemplates.get_user_prompt("Test", [])

        assert "IMPORTANT" in user_prompt.upper() or "reminder" in user_prompt.lower()

    def test_rvu_values_are_reasonable(self):
        """RVU section should include reasonable RVU values"""
        section = PromptTemplates.get_rvu_analysis_prompt_section()

        # Check for some common CPT codes with their RVUs
        rvu_patterns = [
            r'99213.*1\.3',  # 99213 with RVU 1.3
            r'99214.*1\.9',  # 99214 with RVU 1.92
            r'99215.*2\.8',  # 99215 with RVU 2.8
        ]

        found = sum(1 for pattern in rvu_patterns if re.search(pattern, section))
        assert found >= 2, "Should include at least 2 example RVU values"

    def test_modifier_section_includes_common_modifiers(self):
        """Modifier section should list commonly used modifiers"""
        section = PromptTemplates.get_modifier_suggestions_prompt_section()

        common_modifiers = ["-25", "-59", "-76", "-77", "-91", "-95"]
        found_modifiers = sum(1 for mod in common_modifiers if mod in section)

        assert found_modifiers >= 4, f"Should include at least 4 common modifiers, found {found_modifiers}"


class TestPromptTokenEfficiency:
    """Test prompts for token efficiency"""

    def test_system_prompt_length(self):
        """System prompt should be comprehensive but not excessive"""
        system_prompt = PromptTemplates.get_system_prompt()

        # Should be between 1000-5000 characters
        assert 1000 <= len(system_prompt) <= 6000

    def test_combined_prompt_more_concise(self):
        """Combined prompt should be more concise than full user prompt"""
        user_prompt = PromptTemplates.get_user_prompt("Test note", [])
        combined_prompt = PromptTemplates.get_combined_analysis_prompt()

        # Combined should be shorter than full user prompt
        assert len(combined_prompt) < len(user_prompt)

    def test_no_excessive_repetition(self):
        """Prompts should not have excessive repetition"""
        system_prompt = PromptTemplates.get_system_prompt()

        # Check that common phrases don't repeat too many times
        common_phrases = ["documentation", "code", "suggest", "provide"]

        for phrase in common_phrases:
            count = system_prompt.lower().count(phrase)
            # Should appear multiple times but not excessively (< 30 times)
            assert count < 30, f"Phrase '{phrase}' appears {count} times (excessive)"


class TestPromptGuidanceQuality:
    """Test quality and clarity of guidance in prompts"""

    def test_confidence_score_has_ranges(self):
        """Confidence score guidance should define clear ranges"""
        system_prompt = PromptTemplates.get_system_prompt()

        # Should define multiple ranges
        assert "0.9" in system_prompt or "0.8" in system_prompt
        assert "0.7" in system_prompt or "0.5" in system_prompt
        assert "0.3" in system_prompt or "0.0" in system_prompt

    def test_risk_levels_defined(self):
        """Denial risk section should define Low/Medium/High"""
        section = PromptTemplates.get_denial_risk_prompt_section()

        assert "Low" in section
        assert "Medium" in section
        assert "High" in section

    def test_priority_levels_defined(self):
        """Documentation quality section should define priority levels"""
        section = PromptTemplates.get_documentation_quality_prompt_section()

        # Should mention High/Medium/Low priority
        priority_count = section.count("High") + section.count("Medium") + section.count("Low")
        assert priority_count >= 3

    def test_examples_provided(self):
        """Feature sections should include examples"""
        sections = [
            PromptTemplates.get_documentation_quality_prompt_section(),
            PromptTemplates.get_denial_risk_prompt_section(),
            PromptTemplates.get_modifier_suggestions_prompt_section(),
        ]

        for section in sections:
            # Should have JSON example with braces
            assert "{" in section and "}" in section


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
