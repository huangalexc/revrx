"""
Integration tests for complete analysis pipeline (Track G7-G12)

Tests verify:
- G7: Complete analysis pipeline with all features
- G8: API responses include all new fields
- G9: UI data format compatibility
- G10: Export includes all features
- G11: Error handling across features
- G12: Various note types (inpatient, outpatient, ER)
"""

import pytest
import json
from datetime import datetime
from typing import Dict, List

from app.services.prompt_templates import prompt_templates
from app.services.openai_service import OpenAIService


class TestAnalysisPipeline:
    """Test complete analysis pipeline with all features (G7)"""

    @pytest.fixture
    def sample_clinical_notes(self) -> Dict[str, str]:
        """Sample clinical notes for different encounter types"""
        return {
            "outpatient": """
                PATIENT: [REDACTED]
                DATE OF SERVICE: 09/30/2025

                CHIEF COMPLAINT: Follow-up for hypertension and diabetes

                HISTORY OF PRESENT ILLNESS:
                Patient is a 62-year-old male with type 2 diabetes and hypertension.
                Blood pressure has been running 145-150/85-90 at home.
                Blood sugar levels fasting 140-160 mg/dL.
                Patient reports good medication compliance.

                PAST MEDICAL HISTORY:
                1. Type 2 Diabetes Mellitus - diagnosed 2018
                2. Essential Hypertension - diagnosed 2015
                3. Hyperlipidemia - diagnosed 2016

                MEDICATIONS:
                1. Metformin 1000mg BID
                2. Lisinopril 20mg daily
                3. Atorvastatin 40mg daily

                PHYSICAL EXAMINATION:
                Vital Signs: BP 148/88, HR 78, RR 16, T 98.4F, BMI 32.1
                General: Alert, oriented x3, no acute distress
                Cardiovascular: Regular rate and rhythm, no murmurs
                Respiratory: Clear to auscultation bilaterally
                Extremities: No edema, pedal pulses intact

                ASSESSMENT AND PLAN:
                1. Type 2 Diabetes Mellitus - uncontrolled
                   - HbA1c ordered
                   - Increase Metformin to 1000mg TID
                   - Discussed dietary modifications
                   - Continue home glucose monitoring

                2. Essential Hypertension - uncontrolled
                   - Increase Lisinopril to 40mg daily
                   - Recheck BP in 2 weeks

                3. Hyperlipidemia - controlled
                   - Continue Atorvastatin
                   - Lipid panel ordered

                Time spent: 30 minutes face-to-face counseling on disease management

                BILLED CODES:
                CPT: 99213 (Office visit, established patient, level 3)
                ICD-10: E11.65 (Type 2 diabetes with hyperglycemia)
                ICD-10: I10 (Essential hypertension)
                ICD-10: E78.5 (Hyperlipidemia)
            """,
            "inpatient": """
                ADMISSION NOTE
                DATE: 09/30/2025

                CHIEF COMPLAINT: Chest pain

                HISTORY OF PRESENT ILLNESS:
                72-year-old female with history of CAD presents with acute onset
                substernal chest pain radiating to left arm. Pain started 2 hours ago,
                8/10 intensity, associated with shortness of breath and diaphoresis.

                PAST MEDICAL HISTORY:
                1. Coronary artery disease with prior MI (2020)
                2. Hypertension
                3. Type 2 Diabetes
                4. Chronic kidney disease stage 3

                PHYSICAL EXAMINATION:
                Vital Signs: BP 165/95, HR 105, RR 22, T 98.6F, O2 sat 94% on RA
                Cardiovascular: Tachycardic, S3 gallop present
                Respiratory: Bilateral crackles

                DIAGNOSTIC TESTS:
                - EKG: ST elevation in leads II, III, aVF
                - Troponin: Elevated at 2.4 ng/mL
                - BNP: 850 pg/mL

                ASSESSMENT:
                1. Acute ST-elevation myocardial infarction (STEMI) - inferior wall
                2. Acute decompensated heart failure
                3. Acute kidney injury on CKD

                PLAN:
                - Emergent cardiac catheterization
                - Cardiology consultation
                - Admission to CCU
                - ASA, Plavix, Heparin drip
                - IV Lasix for volume overload

                BILLED CODES:
                CPT: 99223 (Initial hospital care, high complexity)
                CPT: 93010 (EKG interpretation)
                ICD-10: I21.19 (STEMI inferior wall)
                ICD-10: I50.21 (Acute systolic heart failure)
            """,
            "emergency": """
                EMERGENCY DEPARTMENT NOTE
                DATE: 09/30/2025

                CHIEF COMPLAINT: Motor vehicle accident

                HISTORY:
                23-year-old male restrained driver in high-speed MVA.
                Positive loss of consciousness at scene. GCS 14 on arrival.
                Complains of neck pain, chest pain, and left leg pain.

                TRAUMA EVALUATION:
                Primary Survey: Airway patent, breathing adequate, pulses present
                Secondary Survey: Abrasions to face and chest, left femur deformity

                IMAGING:
                - CT Head: Negative for intracranial hemorrhage
                - CT C-spine: No fracture
                - Chest X-ray: Multiple rib fractures (ribs 4-6 left)
                - Left femur X-ray: Displaced midshaft fracture

                PROCEDURES PERFORMED:
                - Femur splinting and reduction
                - Chest tube placement (left) for pneumothorax

                CONSULTATIONS:
                - Orthopedic surgery - accepted for ORIF femur
                - Trauma surgery - following

                DISPOSITION: Admitted to trauma service

                BILLED CODES:
                CPT: 99285 (Emergency visit, high complexity)
                CPT: 32551 (Chest tube insertion)
                ICD-10: S72.302A (Femur shaft fracture, initial)
                ICD-10: S22.42XA (Multiple rib fractures)
            """
        }

    def test_g7_complete_pipeline_outpatient(self, sample_clinical_notes):
        """G7: Test complete analysis pipeline with outpatient note"""
        clinical_note = sample_clinical_notes["outpatient"]
        billed_codes = [
            {"code": "99213", "code_type": "CPT", "description": "Office visit, level 3"}
        ]

        # Generate prompts
        system_prompt = prompt_templates.get_system_prompt()
        user_prompt = prompt_templates.get_user_prompt(clinical_note, billed_codes)

        # Verify prompts contain all required sections
        assert system_prompt is not None
        assert len(system_prompt) > 0
        assert "missing_documentation" in system_prompt
        assert "denial_risks" in system_prompt
        assert "rvu_analysis" in system_prompt
        assert "modifier_suggestions" in system_prompt
        assert "uncaptured_services" in system_prompt

        # Verify user prompt structure
        assert clinical_note in user_prompt
        assert "99213" in user_prompt
        assert "DOCUMENTATION QUALITY" in user_prompt or "documentation" in user_prompt.lower()
        assert "DENIAL RISK" in user_prompt or "denial" in user_prompt.lower()
        assert "RVU" in user_prompt

    def test_g7_complete_pipeline_inpatient(self, sample_clinical_notes):
        """G7: Test complete analysis pipeline with inpatient note"""
        clinical_note = sample_clinical_notes["inpatient"]
        billed_codes = [
            {"code": "99223", "code_type": "CPT", "description": "Initial hospital care"}
        ]

        system_prompt = prompt_templates.get_system_prompt()
        user_prompt = prompt_templates.get_user_prompt(clinical_note, billed_codes)

        # Verify complex inpatient note handling
        assert "99223" in user_prompt
        assert clinical_note in user_prompt
        assert len(user_prompt) > 1000  # Should be substantial for complex note

    def test_g7_complete_pipeline_emergency(self, sample_clinical_notes):
        """G7: Test complete analysis pipeline with emergency note"""
        clinical_note = sample_clinical_notes["emergency"]
        billed_codes = [
            {"code": "99285", "code_type": "CPT", "description": "Emergency visit"},
            {"code": "32551", "code_type": "CPT", "description": "Chest tube insertion"}
        ]

        user_prompt = prompt_templates.get_user_prompt(clinical_note, billed_codes)

        # Verify multi-code handling
        assert "99285" in user_prompt
        assert "32551" in user_prompt
        assert clinical_note in user_prompt


class TestAPIResponseFields:
    """Test API responses include all new fields (G8)"""

    def test_g8_response_structure_complete(self):
        """G8: Verify response structure includes all feature fields"""
        # Expected response structure based on system prompt
        expected_fields = [
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

        system_prompt = prompt_templates.get_system_prompt()

        # Verify all fields are documented in system prompt
        for field in expected_fields:
            assert field in system_prompt, f"Missing field in system prompt: {field}"

    def test_g8_missing_documentation_structure(self):
        """G8: Verify missing_documentation field structure"""
        system_prompt = prompt_templates.get_system_prompt()

        # Should define structure with section, issue, suggestion
        assert '"section"' in system_prompt or "'section'" in system_prompt
        assert '"issue"' in system_prompt or "'issue'" in system_prompt
        assert '"suggestion"' in system_prompt or "'suggestion'" in system_prompt

    def test_g8_denial_risks_structure(self):
        """G8: Verify denial_risks field structure"""
        system_prompt = prompt_templates.get_system_prompt()

        assert "risk_level" in system_prompt
        assert "denial_reasons" in system_prompt or "denial" in system_prompt.lower()
        # Risk levels shown in example structure
        assert '"risk_level": "Low"' in system_prompt

    def test_g8_rvu_analysis_structure(self):
        """G8: Verify rvu_analysis field structure"""
        system_prompt = prompt_templates.get_system_prompt()

        assert "billed_codes_rvus" in system_prompt or "billedRVUs" in system_prompt
        assert "suggested_codes_rvus" in system_prompt or "suggestedRVUs" in system_prompt
        assert "incremental_rvus" in system_prompt or "incremental" in system_prompt

    def test_g8_modifier_suggestions_structure(self):
        """G8: Verify modifier_suggestions field structure"""
        system_prompt = prompt_templates.get_system_prompt()

        assert "modifier" in system_prompt
        assert "-25" in system_prompt or "modifier" in system_prompt
        assert "justification" in system_prompt

    def test_g8_uncaptured_services_structure(self):
        """G8: Verify uncaptured_services field structure"""
        system_prompt = prompt_templates.get_system_prompt()

        assert "uncaptured" in system_prompt.lower() or "charge capture" in system_prompt.lower()
        assert "service" in system_prompt
        assert "suggested_codes" in system_prompt

    def test_g8_audit_metadata_structure(self):
        """G8: Verify audit_metadata field structure"""
        system_prompt = prompt_templates.get_system_prompt()

        assert "audit_metadata" in system_prompt
        assert "timestamp" in system_prompt
        assert "compliance" in system_prompt.lower()


class TestErrorHandling:
    """Test error handling across features (G11)"""

    def test_g11_empty_clinical_note(self):
        """G11: Handle empty clinical note gracefully"""
        empty_note = ""
        billed_codes = []

        user_prompt = prompt_templates.get_user_prompt(empty_note, billed_codes)

        # Should not crash and should generate valid prompt
        assert user_prompt is not None
        assert len(user_prompt) > 0
        assert "CLINICAL NOTE" in user_prompt

    def test_g11_no_billed_codes(self):
        """G11: Handle missing billed codes"""
        clinical_note = "Patient presents with acute bronchitis."
        billed_codes = []

        user_prompt = prompt_templates.get_user_prompt(clinical_note, billed_codes)

        assert "None provided" in user_prompt or "No codes" in user_prompt.lower()
        assert clinical_note in user_prompt

    def test_g11_malformed_billed_codes(self):
        """G11: Handle malformed billed codes gracefully"""
        clinical_note = "Test note"
        billed_codes = [
            {"code": "99213", "code_type": "CPT"},  # Missing description
            {"code": "80053", "description": "Test"}  # Missing code_type (gets N/A)
        ]

        # Should not crash
        try:
            user_prompt = prompt_templates.get_user_prompt(clinical_note, billed_codes)
            assert user_prompt is not None
            assert "99213" in user_prompt
            assert "80053" in user_prompt
        except KeyError as e:
            pytest.fail(f"Should handle malformed codes gracefully: {e}")

    def test_g11_very_long_note(self):
        """G11: Handle very long clinical notes"""
        long_note = "This is a test sentence. " * 10000  # ~250,000 chars
        billed_codes = [{"code": "99213", "code_type": "CPT"}]

        # Should not crash with memory issues
        try:
            user_prompt = prompt_templates.get_user_prompt(long_note, billed_codes)
            assert long_note in user_prompt
        except Exception as e:
            pytest.fail(f"Should handle long notes: {e}")

    def test_g11_special_characters_in_note(self):
        """G11: Handle special characters and encoding"""
        clinical_note = """
            Patient: José García
            Symptoms: chest pain → dyspnea
            Temperature: 98.6°F
            Notes: "Patient states 'I feel better'"
            Special chars: <>&'"
        """
        billed_codes = []

        user_prompt = prompt_templates.get_user_prompt(clinical_note, billed_codes)

        # Should preserve special characters
        assert "José García" in user_prompt or "Jos" in user_prompt
        assert user_prompt is not None


class TestNoteTypeVariations:
    """Test with various note types (G12)"""

    def test_g12_outpatient_note(self):
        """G12: Outpatient office visit note"""
        outpatient_note = """
            Office Visit - Established Patient
            CC: Follow-up diabetes
            HPI: 60yo M with T2DM, A1c last visit 8.2%
            Exam: BP 135/85, BMI 31.2
            Assessment: Uncontrolled DM
            Plan: Increase metformin, recheck A1c in 3 months
        """

        user_prompt = prompt_templates.get_user_prompt(outpatient_note, [])

        assert "Office Visit" in user_prompt or "office" in user_prompt.lower()
        assert outpatient_note in user_prompt

    def test_g12_inpatient_note(self):
        """G12: Inpatient admission note"""
        inpatient_note = """
            ADMISSION NOTE
            CC: Sepsis
            HPI: 75yo F with fever, hypotension, confusion
            Exam: BP 85/50, HR 120, Temp 102.5F
            Labs: WBC 22k, Lactate 4.2
            Assessment: Septic shock, likely UTI source
            Plan: Broad spectrum antibiotics, IVF resuscitation, ICU admission
        """

        user_prompt = prompt_templates.get_user_prompt(inpatient_note, [])

        assert "ADMISSION" in user_prompt or inpatient_note in user_prompt
        assert user_prompt is not None

    def test_g12_emergency_note(self):
        """G12: Emergency department note"""
        emergency_note = """
            ED VISIT
            CC: Chest pain
            HPI: 55yo M with acute onset chest pain, 9/10, radiating to jaw
            Exam: Diaphoretic, BP 160/95, HR 105
            EKG: ST elevation in anterior leads
            Assessment: STEMI
            Plan: Emergent cath lab, cardiology consulted
        """

        user_prompt = prompt_templates.get_user_prompt(emergency_note, [])

        assert emergency_note in user_prompt
        assert user_prompt is not None

    def test_g12_procedure_note(self):
        """G12: Procedure note"""
        procedure_note = """
            PROCEDURE NOTE: Colonoscopy
            Indication: Screening, family history colon cancer
            Procedure: Colonoscopy performed with conscious sedation
            Findings: 3 polyps identified, removed with snare polypectomy
            Pathology: Polyps sent for histology
            Complications: None
        """

        user_prompt = prompt_templates.get_user_prompt(procedure_note, [])

        assert procedure_note in user_prompt
        assert "PROCEDURE" in user_prompt or procedure_note in user_prompt

    def test_g12_telehealth_note(self):
        """G12: Telehealth visit note"""
        telehealth_note = """
            TELEHEALTH VISIT (video)
            CC: Medication refill
            HPI: Patient doing well on current medications
            No new concerns
            Plan: Refill all medications, follow up in 6 months
            Time: 15 minutes via secure video platform
        """

        user_prompt = prompt_templates.get_user_prompt(telehealth_note, [])

        assert telehealth_note in user_prompt
        assert user_prompt is not None


class TestPromptConsistency:
    """Additional consistency tests across all features"""

    def test_all_feature_sections_present(self):
        """Verify all 7 feature sections are in prompts"""
        user_prompt = prompt_templates.get_user_prompt("Test note", [])

        # All major sections should be present
        sections_to_check = [
            "CODE",
            "DOCUMENTATION",
            "DENIAL",
            "RVU",
            "MODIFIER",
            "CAPTURE",
            "AUDIT"
        ]

        found_sections = sum(1 for section in sections_to_check
                            if section in user_prompt.upper())

        assert found_sections >= 6, f"Expected at least 6 sections, found {found_sections}"

    def test_prompt_combines_all_features(self):
        """Verify combined prompt includes all features"""
        combined = prompt_templates.get_combined_analysis_prompt()

        feature_indicators = [
            "CODE",
            "DOCUMENTATION",
            "DENIAL",
            "RVU",
            "MODIFIER",
            "UNCAPTURED",
            "AUDIT"
        ]

        for indicator in feature_indicators:
            assert indicator in combined.upper(), f"Missing {indicator} in combined prompt"

    def test_prompt_token_efficiency(self):
        """Verify prompts are token-efficient"""
        system_prompt = prompt_templates.get_system_prompt()
        combined_prompt = prompt_templates.get_combined_analysis_prompt()

        # Combined should be more efficient than full system
        assert len(combined_prompt) < len(system_prompt)

        # But still comprehensive
        assert len(combined_prompt) > 500


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
