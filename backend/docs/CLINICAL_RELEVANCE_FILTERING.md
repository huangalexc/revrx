# Clinical Relevance Filtering

## Overview

The clinical relevance filtering system uses **GPT-4o-mini** (OpenAI's cheapest model) to pre-process de-identified clinical notes before sending them to AWS Comprehend Medical. This step removes non-billing content (vitals, screeners, patient education, etc.) to improve extraction accuracy and reduce downstream processing costs.

## Problem Solved

**Challenge**: Clinical notes often contain large amounts of content that is not relevant for medical billing and coding:
- Vital signs (unless abnormal and clinically significant)
- Screening tool scores (PHQ-9, GAD-7, etc.)
- Growth charts and percentiles
- Patient education materials
- Template boilerplate text
- Administrative notes

**Impact**: This irrelevant content can:
- Reduce extraction accuracy (noise in entity detection)
- Increase AWS Comprehend Medical costs
- Add cognitive load for LLM coding analysis
- Slow down processing

## Solution: Pre-Processing with GPT-4o-mini

### Pipeline Position

```
Original Text
    ↓
PHI Detection & Stripping (AWS Comprehend Medical)
    ↓
De-identified Text
    ↓
📍 Clinical Relevance Filtering (GPT-4o-mini) ← NEW STEP
    ↓
Filtered Text (billing-relevant only)
    ↓
Entity Extraction (DetectEntitiesV2, InferICD10CM, InferSNOMEDCT)
    ↓
Code Suggestions (GPT-4)
```

### What Gets Removed

- **Vital Signs**: Blood pressure, heart rate, temperature, weight, BMI (unless abnormal and clinically significant)
- **Screening Tools**: PHQ-9, GAD-7, AUDIT-C, and other standardized questionnaires
- **Growth Charts**: Height/weight percentiles, head circumference (pediatric templates)
- **Patient Education**: Handouts, educational materials, home monitoring logs
- **Administrative Notes**: Billing reminders, scheduling notes, template instructions
- **Normal Lab Values**: Labs within normal range (keeps abnormal values)
- **Vaccine Records**: Immunization history (unless part of today's visit)

### What Gets Kept

- **Chief Complaint**: Reason for visit
- **History of Present Illness (HPI)**: Clinical narrative
- **Review of Systems (ROS)**: Pertinent findings
- **Physical Examination**: Clinical findings
- **Assessment and Diagnosis**: Clinical impressions
- **Treatment Plan**: Procedures, medications, orders
- **Medical Decision Making**: Complexity factors
- **Abnormal Lab Values**: Clinically significant results
- **Follow-up Plans**: Return visit instructions

## Implementation

### Service Method

**Location**: `app/services/openai_service.py`

```python
async def filter_clinical_relevance(
    self,
    deidentified_text: str,
) -> Dict[str, Any]:
    """
    Filter clinical text to keep only billing-relevant content.

    Uses GPT-4o-mini (cheapest model) to extract clinically relevant assessment
    and billing context, dropping vitals, screeners, growth charts, patient education, etc.

    Args:
        deidentified_text: De-identified clinical text (after PHI stripping)

    Returns:
        Dict with:
            - filtered_text: Clinically relevant text for coding
            - original_length: Original character count
            - filtered_length: Filtered character count
            - reduction_pct: Percentage reduction
            - tokens_used: Token count
            - cost_usd: API cost
            - processing_time_ms: Processing time
            - model_used: Model name

    Raises:
        OpenAIError: If API call fails after retries
    """
```

### Pipeline Integration

**Location**: `app/tasks/phi_processing.py` (lines 140-173)

```python
# Step 6.1: Filter for clinical relevance using GPT-4o-mini
logger.info("Filtering text for clinical relevance", encounter_id=encounter_id)

deidentified_text = result.deidentified_text
filtering_result = None

try:
    from app.services.openai_service import openai_service

    filtering_result = await openai_service.filter_clinical_relevance(
        deidentified_text=deidentified_text
    )

    # Use filtered text for subsequent processing
    clinical_text_for_coding = filtering_result["filtered_text"]

    logger.info(
        "Clinical relevance filtering completed",
        encounter_id=encounter_id,
        original_length=filtering_result["original_length"],
        filtered_length=filtering_result["filtered_length"],
        reduction_pct=filtering_result["reduction_pct"],
        tokens_used=filtering_result["tokens_used"],
        cost_usd=filtering_result["cost_usd"],
    )

except Exception as e:
    logger.warning(
        "Clinical relevance filtering failed, using full deidentified text",
        encounter_id=encounter_id,
        error=str(e)
    )
    # Fallback: use full deidentified text if filtering fails
    clinical_text_for_coding = deidentified_text
```

### Subsequent Processing

All downstream AWS Comprehend Medical calls use the filtered text:

```python
# DetectEntitiesV2
medical_entities = comprehend_medical_service.detect_entities_v2(clinical_text_for_coding)

# InferICD10CM
icd10_entities = comprehend_medical_service.infer_icd10_cm(clinical_text_for_coding)

# InferSNOMEDCT
snomed_entities = comprehend_medical_service.infer_snomed_ct(clinical_text_for_coding)

# Final coding analysis
coding_result = await openai_service.analyze_clinical_note(
    clinical_note=clinical_text_for_coding,
    billed_codes=billed_codes
)
```

## Test Results

### Example: Hypertension/Diabetes Follow-up

**Input Note**: 2,040 characters
- Chief complaint
- Vital signs (BP, HR, temp, weight, BMI)
- PHQ-9/GAD-7 screening scores
- History of Present Illness
- Review of Systems
- Physical Examination
- Labs (HbA1c, creatinine, eGFR)
- Assessment and Plan
- Patient education handouts
- Growth chart template (not applicable)
- Billing notes

**Filtered Output**: 1,432 characters (29.8% reduction)
- Chief complaint ✓
- History of Present Illness ✓
- Review of Systems ✓
- Physical Examination ✓
- Abnormal labs (HbA1c 7.8%, eGFR 68) ✓
- Assessment and Plan ✓
- Follow-up plan ✓

**Removed**:
- Vital signs ✗
- PHQ-9/GAD-7 scores ✗
- Normal lab (creatinine) ✗
- Patient education ✗
- Growth chart ✗
- Billing notes ✗

**Performance**:
- Reduction: 29.8%
- Cost: $0.000343
- Processing time: 9.1 seconds
- Tokens used: 1,154

## Cost Analysis

### GPT-4o-mini Pricing (2025)
- Input: $0.15 per 1M tokens
- Output: $0.60 per 1M tokens

### Example Cost Breakdown

For a 2,040 character clinical note:
- **Filtering cost**: $0.000343
- **Estimated Comprehend savings**: $0.000061 (from 30% reduction)
- **Net additional cost**: $0.000282

**Key Insight**: The primary benefit is **improved extraction accuracy**, not just cost savings. Cleaner input text leads to:
- More accurate entity detection
- Better ICD-10/SNOMED code extraction
- Higher quality coding suggestions
- Reduced false positives

## Monitoring

### Structured Logging

```python
logger.info(
    "Clinical relevance filtering completed",
    original_length=2040,
    filtered_length=1432,
    reduction_pct=29.8,
    tokens_used=1154,
    cost_usd=0.000343,
    processing_time_ms=9132
)
```

### Audit Log Metadata

Filtering metadata is stored in the report generation audit log:

```python
{
    "clinical_filtering": {
        "enabled": True,
        "original_length": 2040,
        "filtered_length": 1432,
        "reduction_pct": 29.8,
        "cost_usd": 0.000343
    }
}
```

## Error Handling

### Graceful Fallback

If filtering fails (API error, timeout, etc.), the system automatically falls back to using the full de-identified text:

```python
except Exception as e:
    logger.warning(
        "Clinical relevance filtering failed, using full deidentified text",
        encounter_id=encounter_id,
        error=str(e)
    )
    clinical_text_for_coding = deidentified_text
```

This ensures:
- No processing interruption
- Graceful degradation
- Full audit trail of failures

## Testing

### Test Script

**Location**: `backend/scripts/test_clinical_filtering.py`

```bash
# Run filtering test
python scripts/test_clinical_filtering.py
```

**Output**:
- Original vs. filtered text comparison
- Character count reduction
- Token usage and cost
- Processing time
- Analysis of what was removed/kept

## Benefits

1. **Improved Accuracy**: Cleaner input reduces noise in entity detection
2. **Cost Efficiency**: Reduces downstream AWS Comprehend Medical processing
3. **Better Coding**: LLM receives focused, billing-relevant content
4. **Faster Processing**: Less text to analyze at each step
5. **Consistency**: Standardized filtering rules across all notes

## Future Enhancements

1. **Adaptive Filtering**: Adjust filtering based on note type (inpatient vs. outpatient, specialty)
2. **Custom Rules**: User-configurable filtering criteria
3. **Learning System**: Track which filtered content led to missed codes and adjust
4. **Batch Optimization**: Cache filtering model for faster repeated calls
5. **Multi-Model Support**: Option to use other lightweight models (Claude Haiku, etc.)
