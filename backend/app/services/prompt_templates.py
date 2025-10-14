"""
2-Prompt Approach for Medical Coding Analysis
Splits complex analysis into two focused prompts for reliability
"""

from typing import List, Dict


class PromptTemplates:
    """
    2-Prompt approach:
    1. Code Identification & Suggestions (Primary Coding)
    2. Quality & Compliance Analysis (Audit & Risk)
    """

    # ========================================================================
    # PROMPT 1: CODE IDENTIFICATION & SUGGESTIONS
    # ========================================================================

    @staticmethod
    def get_coding_system_prompt() -> str:
        """System prompt for Prompt 1: Code identification and suggestions"""
        return """You are an expert medical coding specialist with deep knowledge of CPT, ICD-10, and HCPCS codes.
Your role is to analyze de-identified clinical documentation and identify appropriate billing codes.

Core Guidelines:
1. **Extract Billed Codes**: Scan the entire clinical note for sections listing codes already billed (e.g., "Provider Billed Codes:", "Billing:", "Codes submitted:")
2. **Determine Encounter Type**: Identify visit type (well child, follow-up, new patient, urgent care, etc.)
3. **Determine E/M Service Level**: For office visits, determine appropriate E/M level (99202-99205 for new, 99211-99215 for established) based on:
   - Medical Decision Making (MDM) complexity
   - Total time spent (if documented)
4. **Use Provided Extracted Codes**: You'll receive pre-extracted ICD-10 and SNOMED-derived CPT suggestions as starting points
5. **Suggest Additional Codes**: Only suggest codes clearly supported by documentation
6. **Identify Uncaptured Services**: Find documented services not yet coded (screenings, counseling, procedures)
7. **Assign Confidence Scores** (0.0-1.0):
   - 0.9-1.0: Explicit documentation, clear medical necessity
   - 0.7-0.89: Good documentation, likely billable
   - 0.5-0.69: Moderate support, may need clarification
   - 0.3-0.49: Weak support, questionable necessity
   - 0.0-0.29: Insufficient documentation

E/M Level Guidelines (2021+):
- 99211: Minimal MDM (nurse visit)
- 99212: Straightforward MDM (1-2 diagnoses, low risk)
- 99213: Low complexity MDM (stable chronic conditions)
- 99214: Moderate complexity MDM (exacerbation, moderate risk)
- 99215: High complexity MDM (new uncertain problem, high risk)

Time-based alternative:
- 99212: 10-19 min | 99213: 20-29 min | 99214: 30-39 min | 99215: 40-54 min

Response Format (JSON):
Return your response as a JSON object with this structure:
{
  "billed_codes": [
    {
      "code": "99213",
      "code_type": "CPT",
      "description": "CPT 99213: Office visit, established patient, low complexity"
    }
  ],
  "suggested_codes": [
    {
      "code": "99214",
      "code_type": "CPT",
      "description": "CPT 99214: Office visit, established patient, moderate complexity",
      "justification": "Moderate MDM with 3 chronic conditions managed",
      "confidence": 0.85,
      "confidence_reason": "Clear documentation of MDM complexity",
      "supporting_text": ["3 diagnoses addressed", "Medication adjustments made"]
    }
  ],
  "additional_codes": [
    // Same structure - alternative codes NOT in billed_codes
  ],
  "uncaptured_services": [
    {
      "service": "Depression screening using PHQ-2",
      "location_in_note": "Assessment section",
      "suggested_codes": ["96127"],
      "priority": "High",
      "justification": "PHQ-2 documented but not coded; separately billable",
      "estimated_rvus": 0.18
    }
  ]
}"""

    @staticmethod
    def get_coding_user_prompt(
        clinical_note: str,
        billed_codes: List[Dict[str, str]],
        extracted_icd10_codes: List[Dict[str, any]] = None,
        snomed_to_cpt_suggestions: List[Dict[str, any]] = None,
        encounter_type: str = None
    ) -> str:
        """User prompt for Prompt 1: Code identification"""

        billed_codes_str = "\n".join(
            [f"- {code['code']} ({code.get('code_type', 'N/A')}): {code.get('description', 'N/A')}"
             for code in billed_codes]
        ) if billed_codes else "None provided"

        icd10_str = "\n".join(
            [f"- {code['code']}: {code.get('description', 'N/A')} (confidence: {code.get('score', 0):.2f})"
             for code in (extracted_icd10_codes or [])]
        ) or "None extracted"

        snomed_cpt_str = "\n".join(
            [f"- CPT {code['cpt_code']}: {code.get('cpt_description', 'N/A')} (confidence: {code.get('confidence', 0):.2f})"
             for code in (snomed_to_cpt_suggestions or [])]
        ) or "None suggested"

        encounter_info = f"Encounter Type: {encounter_type}" if encounter_type else "Encounter Type: Not determined"

        return f"""Analyze this clinical encounter and identify appropriate billing codes.

{encounter_info}

BILLED CODES (from claims data):
{billed_codes_str}

EXTRACTED ICD-10 CODES (from AWS Comprehend Medical):
{icd10_str}

SUGGESTED CPT CODES (from SNOMED crosswalk):
{snomed_cpt_str}

CLINICAL NOTE (de-identified, filtered for billing):
{clinical_note}

TASKS:
1. **Extract Billed Codes**: Scan the clinical note above for any billing sections. Extract ALL codes mentioned.
2. **Validate Billed Codes**: Review codes listed above and in the note. Are they appropriate for this encounter?
3. **Suggest Additional Codes**: Identify codes NOT in billed_codes but supported by documentation. Include:
   - E/M service level (if not billed)
   - Procedures performed
   - Screenings/assessments administered
   - ICD-10 diagnoses documented
4. **Identify Uncaptured Services**: Find documented services without associated codes (e.g., PHQ-9 screening, counseling, care coordination)

IMPORTANT:
- Format descriptions as "CODE_TYPE CODE: Description"
- Only suggest codes with clear documentation support
- Include confidence_reason for each suggestion
- Don't suggest codes already in billed_codes
- Focus on billable services with medical necessity"""

    # ========================================================================
    # PROMPT 2: QUALITY & COMPLIANCE ANALYSIS
    # ========================================================================

    @staticmethod
    def get_quality_system_prompt() -> str:
        """System prompt for Prompt 2: Quality and compliance analysis"""
        return """You are an expert medical coding auditor specializing in documentation quality, compliance, and denial risk assessment.

Your role is to analyze billing codes and assess:
1. **Documentation Quality**: What's missing to support higher-level codes?
2. **Denial Risks**: What payer objections could arise for each code?
3. **RVU Analysis**: Calculate revenue using 2024 Medicare values
4. **Modifier Recommendations**: When should modifiers be added?
5. **Audit Compliance**: Overall quality score and compliance flags

Denial Risk Levels:
- **Low**: Documentation clearly supports code, unlikely denial
- **Medium**: Some ambiguity, may require extra justification
- **High**: Insufficient documentation, likely denial

Common Denial Reasons:
- Medical necessity not established
- Insufficient documentation of complexity
- Missing time documentation (for time-based E/M)
- Bundling/unbundling violations
- Modifier misuse or missing
- Duplicate service within restricted timeframe
- Prior authorization missing

2024 Medicare Work RVU Reference:
- 99211: 0.18 | 99212: 0.48 | 99213: 1.3 | 99214: 1.92 | 99215: 2.8
- 99202-99205 (new): 0.93, 1.6, 2.6, 3.5
- 96127 (screening): 0.18 | 90834 (psychotherapy): 1.48
- 99291 (critical care): 4.5

Response Format (JSON):
Return your response as a JSON object with this structure:
{
  "missing_documentation": [
    {
      "section": "History of Present Illness",
      "issue": "Duration of symptoms not specified",
      "suggestion": "Document timeline: 'symptoms began 3 days ago'",
      "priority": "High"
    }
  ],
  "denial_risks": [
    {
      "code": "99214",
      "risk_level": "Low",
      "denial_reasons": ["Insufficient MDM complexity", "Time not documented"],
      "documentation_addresses_risks": true,
      "mitigation_notes": "MDM clearly shows 3 diagnoses with moderate complexity"
    }
  ],
  "rvu_analysis": {
    "billed_codes_rvus": 2.6,
    "suggested_codes_rvus": 3.8,
    "incremental_rvus": 1.2,
    "billed_code_details": [
      {"code": "99213", "rvus": 1.3, "description": "Office visit, low complexity"}
    ],
    "suggested_code_details": [
      {"code": "99214", "rvus": 1.92, "description": "Office visit, moderate complexity"}
    ]
  },
  "modifier_suggestions": [
    {
      "code": "99214",
      "modifier": "-25",
      "justification": "Significant, separately identifiable E/M on same day as procedure",
      "documentation_support": "Separate E/M note documented apart from procedure"
    }
  ],
  "audit_metadata": {
    "total_codes_identified": 5,
    "high_confidence_codes": 3,
    "documentation_quality_score": 0.82,
    "compliance_flags": [],
    "timestamp": "2025-10-12T10:00:00Z"
  }
}"""

    @staticmethod
    def get_quality_user_prompt(
        clinical_note: str,
        billed_codes: List[Dict[str, str]],
        suggested_codes: List[Dict[str, any]],
        additional_codes: List[Dict[str, any]],
        encounter_type: str = None
    ) -> str:
        """User prompt for Prompt 2: Quality and compliance analysis"""

        encounter_info = f"Encounter Type: {encounter_type}" if encounter_type else "Encounter Type: Not determined"

        billed_str = "\n".join(
            [f"- {c['code']} ({c.get('code_type', 'N/A')}): {c.get('description', 'N/A')}"
             for c in billed_codes]
        ) or "None"

        suggested_str = "\n".join(
            [f"- {c['code']} ({c.get('code_type', 'N/A')}): {c.get('description', 'N/A')} (confidence: {c.get('confidence', 0):.2f})"
             for c in suggested_codes]
        ) or "None"

        additional_str = "\n".join(
            [f"- {c['code']} ({c.get('code_type', 'N/A')}): {c.get('description', 'N/A')} (confidence: {c.get('confidence', 0):.2f})"
             for c in additional_codes]
        ) or "None"

        return f"""Analyze the quality and compliance of these billing codes.

{encounter_info}

BILLED CODES:
{billed_str}

SUGGESTED CODES (from coding analysis):
{suggested_str}

ADDITIONAL CODES (alternatives):
{additional_str}

CLINICAL NOTE (de-identified):
{clinical_note}

TASKS:
1. **Documentation Quality**: For each suggested code, identify missing documentation that could:
   - Justify the code level chosen
   - Prevent downcoding by payers
   - Support medical necessity
   Specify: section (HPI/ROS/Exam/MDM), issue, actionable suggestion, priority (High/Medium/Low)

2. **Denial Risk Assessment**: For each billed and suggested code:
   - Identify common payer denial reasons
   - Assess if documentation addresses these risks
   - Assign risk level (Low/Medium/High)
   - Provide mitigation recommendations

3. **RVU Analysis**: Calculate work RVUs using 2024 Medicare values:
   - Total RVUs for billed codes
   - Total RVUs for suggested codes
   - Incremental RVU opportunity
   - Provide code-level breakdown

4. **Modifier Recommendations**: Identify codes needing modifiers:
   - Common: -25 (separate E/M), -59 (distinct service), -76/-77 (repeat procedure), -95 (telemedicine)
   - Justify with documentation references

5. **Audit Metadata**: Provide summary statistics:
   - Total codes identified
   - High-confidence count (≥0.8)
   - Documentation quality score (0.0-1.0)
   - Compliance flags (if any)

Focus on practical, actionable guidance to improve coding accuracy and reduce denial risk."""


# Export singleton
prompt_templates = PromptTemplates()
