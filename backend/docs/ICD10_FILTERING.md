# ICD-10 Code Filtering System

## Overview

This document describes the intelligent filtering system that reduces ICD-10 codes extracted by AWS Comprehend Medical by filtering out non-billable signs and negated findings, while keeping diagnoses and symptoms for the LLM to evaluate.

## Problem Statement

AWS Comprehend Medical's `InferICD10CM` API extracts **all possible ICD-10 codes** from clinical text, including:
- ✅ **Diagnoses**: Conditions being treated (e.g., J44.1 - COPD exacerbation)
- ❌ **Symptoms**: Patient complaints (e.g., R06.02 - Shortness of breath)
- ❌ **Signs**: Physical exam findings (e.g., R06.2 - Wheezing)
- ❌ **Negated findings**: Things ruled out (e.g., R50.9 - Fever [when "No fever"])

**Result**: A COPD exacerbation note produces **9 ICD-10 codes**, but only **3 are actual diagnoses**.

## Solution: Two-Step Filtering

### Step 1: Extract Diagnosis & Symptom Entities

Use `DetectEntitiesV2` to identify entities with:
- ✅ Category: `MEDICAL_CONDITION`
- ✅ Trait: `DIAGNOSIS` or `SYMPTOM` (includes billable symptoms like headache, neck pain)
- ❌ Exclude trait: `NEGATION` (filters out "No fever", "denies pain", etc.)

This filters out non-billable SIGN entities and NEGATION entities, while keeping diagnoses and symptoms for the LLM to evaluate.

### Step 2: Fuzzy Text Matching

Match ICD-10 codes to diagnosis entities using fuzzy text matching:
- Compare ICD-10 `text` field to diagnosis entity `text`
- Use similarity scoring (SequenceMatcher)
- Keep only codes that strongly match a diagnosis (threshold: 0.6)

## Example: COPD Exacerbation

### Input Clinical Note
```
52-year-old male presents with worsening shortness of breath over 2 days.
Past medical history significant for chronic obstructive pulmonary disease (COPD)
and hypertension.
On exam: diffuse wheezing, decreased air movement. No fever.
Impression: COPD exacerbation.
Plan: Nebulized bronchodilators, oral prednisone. Continue lisinopril for blood pressure.
```

### Step 1: Detect Entities V2 Results

**MEDICAL_CONDITION Entities (9 total):**

| Text | Trait | Include? |
|------|-------|----------|
| shortness of breath | SYMPTOM | ❌ Not DIAGNOSIS |
| chronic obstructive pulmonary disease | DIAGNOSIS | ✅ Yes |
| COPD | DIAGNOSIS | ✅ Yes |
| hypertension | DIAGNOSIS | ✅ Yes |
| wheezing | SIGN | ❌ Not DIAGNOSIS |
| decreased air movement | SIGN | ❌ Not DIAGNOSIS |
| fever | NEGATION, SYMPTOM | ❌ Has NEGATION |
| COPD exacerbation | DIAGNOSIS | ✅ Yes |
| blood pressure | SIGN | ❌ Not DIAGNOSIS |

**Diagnosis Entities (4):**
1. chronic obstructive pulmonary disease
2. COPD
3. hypertension
4. COPD exacerbation

### Step 2: Infer ICD-10-CM Results

**All ICD-10 Codes (9 total):**

| Code | Description | Text | Match Score | Keep? |
|------|-------------|------|-------------|-------|
| R06.02 | Shortness of breath | shortness of breath | 0.387 | ❌ < 0.6 |
| J44.9 | COPD, unspecified | chronic obstructive pulmonary disease | 1.0 | ✅ Exact |
| J44.9 | COPD, unspecified | COPD | 1.0 | ✅ Exact |
| I10 | Essential hypertension | hypertension | 1.0 | ✅ Exact |
| R06.2 | Wheezing | wheezing | 0.5 | ❌ < 0.6 |
| R06.89 | Other breathing abnormalities | decreased air movement | 0.359 | ❌ < 0.6 |
| R50.9 | Fever, unspecified | fever | 0.273 | ❌ < 0.6 |
| J44.1 | COPD with exacerbation | COPD exacerbation | 1.0 | ✅ Exact |
| I10 | Essential hypertension | blood pressure | 0.275 | ❌ < 0.6 |

**Filtered Codes (4):**
- J44.9 (COPD, unspecified) - from "chronic obstructive pulmonary disease"
- J44.9 (COPD, unspecified) - from "COPD" ← duplicate
- I10 (Essential hypertension) - from "hypertension"
- J44.1 (COPD with exacerbation) - from "COPD exacerbation"

### Step 3: Deduplication

**Final Codes for LLM (3):**
1. ✅ **J44.9** - COPD, unspecified
2. ✅ **J44.1** - COPD with (acute) exacerbation
3. ✅ **I10** - Essential (primary) hypertension

**Result: 9 → 3 codes (67% reduction)**

## Implementation

### Code Location

- **Filtering utilities**: `app/utils/icd10_filtering.py`
- **Integration point**: `app/tasks/phi_processing.py` (lines 344-389)
- **Test script**: `scripts/test_icd10_filtering.py`

### Key Functions

#### `get_diagnosis_entities(medical_entities)`

Extracts diagnosis entities from DetectEntitiesV2 results.

```python
diagnosis_entities = get_diagnosis_entities(medical_entities)
# Returns only entities with DIAGNOSIS trait, excluding NEGATION
```

#### `filter_icd10_codes(icd10_entities, diagnosis_entities, min_match_score=0.6)`

Filters ICD-10 codes using fuzzy text matching.

```python
filtered, stats = filter_icd10_codes(
    icd10_entities=icd10_entities,
    diagnosis_entities=diagnosis_entities,
    min_match_score=0.6  # Require 60% similarity
)
```

Returns:
- `filtered`: List of ICD10Entity objects that matched
- `stats`: Dictionary with filtering statistics

#### `deduplicate_icd10_codes(icd10_entities)`

Removes duplicate codes, keeping highest confidence instance.

```python
deduplicated = deduplicate_icd10_codes(filtered)
# Keeps one instance per ICD-10 code
```

### Integration in PHI Processing

```python
# Extract medical entities
medical_entities = comprehend_medical_service.detect_entities_v2(text)

# Extract ICD-10 codes
icd10_entities = comprehend_medical_service.infer_icd10_cm(text)

# Filter to diagnosis codes only
diagnosis_entities = get_diagnosis_entities(medical_entities)
filtered_icd10, stats = filter_icd10_codes(
    icd10_entities,
    diagnosis_entities,
    min_match_score=0.6
)

# Deduplicate
final_icd10 = deduplicate_icd10_codes(filtered_icd10)

# Use final_icd10 for LLM prompt
```

## Fuzzy Matching Logic

### Similarity Scoring

Uses Python's `difflib.SequenceMatcher` with these rules:

| Match Type | Score | Example |
|------------|-------|---------|
| **Exact match** | 1.0 | "COPD" == "COPD" |
| **Contains** | 0.9 | "COPD" in "COPD exacerbation" |
| **Sequence similarity** | 0.0-1.0 | "wheezing" vs "hypertension" = 0.5 |

### Threshold Selection

| Threshold | Behavior | Use Case |
|-----------|----------|----------|
| **0.5** | Permissive | Keeps some weak matches (e.g., wheezing → hypertension) |
| **0.6** | Balanced | **Current setting** - Good precision |
| **0.7** | Strict | May filter valid variations |
| **0.8** | Very strict | May miss legitimate matches |

**Current threshold: 0.6** (60% similarity required)

## Benefits

### 1. Reduced LLM Token Usage
- **Before**: 9 ICD-10 codes sent to LLM
- **After**: 3 ICD-10 codes sent to LLM
- **Savings**: 67% fewer codes = smaller prompts

### 2. Improved LLM Focus
- LLM receives only diagnosis codes
- Eliminates noise from symptoms/signs
- Better context for validation/refinement

### 3. Higher Quality Suggestions
- Symptom codes (R-codes) filtered out
- Negated findings excluded
- Duplicate codes removed

### 4. Better Audit Trail
- All extracted codes still stored in database
- Filtering only affects LLM input
- Can track filter hit/miss rates

## Monitoring

### Structured Logging

Every filtering operation logs:

```json
{
  "event": "icd10_filtering_complete",
  "total_icd10": 9,
  "filtered_icd10": 4,
  "filtered_out": 5,
  "diagnosis_entities": 4,
  "match_threshold": 0.6
}
```

### Metrics to Track

1. **Filter rate**: `filtered_out / total_icd10`
   - Expected: 30-70% (filtering is working)
   - Alert if: < 10% (too permissive) or > 90% (too strict)

2. **Diagnosis entity count**: Number of DIAGNOSIS entities found
   - Expected: 1-5 per note
   - Alert if: 0 (may indicate extraction failure)

3. **Deduplication rate**: `duplicates_removed / original_count`
   - Expected: 10-30% (some duplicates are normal)

## Edge Cases

### No Diagnosis Entities
If no DIAGNOSIS entities are found, all ICD-10 codes are filtered out:

```python
# Returns empty list and logs warning
filtered, stats = filter_icd10_codes(icd10_entities, [], min_match_score=0.6)
# stats['filtered_icd10'] == 0
```

### No ICD-10 Codes
If no ICD-10 codes extracted, filtering is skipped:

```python
# Returns empty list immediately
filtered, stats = filter_icd10_codes([], diagnosis_entities, min_match_score=0.6)
```

### Filtering Failure
If filtering throws an exception, all codes are kept:

```python
try:
    filtered = filter_icd10_codes(...)
except Exception:
    filtered = icd10_entities  # Fallback to all codes
```

## Testing

Run the test script to see filtering in action:

```bash
cd backend
source venv/bin/activate
python scripts/test_icd10_filtering.py
```

Expected output:
- 9 codes extracted → 4 after filtering → 3 after deduplication
- J44.9, J44.1, I10 kept (diagnosis codes)
- R06.02, R06.2, R06.89, R50.9 filtered out (symptoms/signs)

## Configuration

### Adjusting Match Threshold

In `app/tasks/phi_processing.py`:

```python
filtered_icd10_entities, filter_stats = filter_icd10_codes(
    icd10_entities=icd10_entities,
    diagnosis_entities=diagnosis_entities,
    min_match_score=0.6  # Adjust this value
)
```

### Recommendations

- **0.5**: For permissive filtering (more codes)
- **0.6**: Current balanced setting (recommended)
- **0.7**: For strict filtering (fewer codes)

## Future Enhancements

1. **Machine Learning**
   - Train classifier on ICD-10 codes that should be kept
   - Learn patterns from LLM feedback

2. **Medical Ontology**
   - Use ICD-10 hierarchy (R-codes vs disease codes)
   - Automatically exclude symptom code ranges

3. **Context Awareness**
   - Consider entity proximity in text
   - Weight recent mentions higher

4. **Feedback Loop**
   - Track which filtered codes LLM requests
   - Adjust thresholds based on LLM usage

## Related Documentation

- [SNOMED Filtering Criteria](SNOMED_FILTERING_CRITERIA.md)
- [Comprehend Medical Test Analysis](COMPREHEND_MEDICAL_TEST_ANALYSIS.md)
- [PHI Processing Integration](PHI_PROCESSING_INTEGRATION.md)
