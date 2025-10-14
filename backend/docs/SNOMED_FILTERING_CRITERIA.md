# SNOMED Code Filtering Criteria

## Overview

To improve the quality of SNOMED→CPT crosswalk suggestions, we filter SNOMED codes before passing them to the crosswalk service and LLM. This document explains the filtering criteria and rationale.

## Filtering Rules

### Current Implementation

SNOMED codes are filtered with the following criteria:

```python
filtered_snomed = [
    entity for entity in snomed_entities
    if entity.category == "TEST_TREATMENT_PROCEDURE"
    and entity.score > 0.2
]
```

### Criteria Details

| Criterion | Value | Rationale |
|-----------|-------|-----------|
| **Category** | `TEST_TREATMENT_PROCEDURE` | Only procedure codes are billable via CPT. Diagnoses (MEDICAL_CONDITION) have their own ICD-10 codes. |
| **Score** | `> 0.2` | AWS confidence threshold. Filters out very low-confidence extractions (like 0.002) that are likely noise. |

## Why Filter?

### 1. Reduce Noise in Crosswalk
- **Problem**: Low-confidence SNOMED codes (< 0.2) are unreliable
- **Example**: Test Case 1 extracted "BP" with confidence 0.002
- **Solution**: Filter reduces false positives in CPT suggestions

### 2. Focus on Billable Procedures
- **Problem**: SNOMED extracts both diagnoses and procedures
- **Example**: "Hypertension" (diagnosis) has SNOMED code but not billable via CPT
- **Solution**: Only use `TEST_TREATMENT_PROCEDURE` category

### 3. Improve Crosswalk Hit Rate
- **Problem**: Low-quality codes unlikely to have crosswalk mappings
- **Solution**: Higher hit rate on filtered codes = better cache utilization

### 4. Reduce LLM Token Usage
- **Problem**: Including all SNOMED codes increases prompt size
- **Solution**: Filtered list is smaller, more relevant

## Test Case Example

### Test Case 1: Hypertension Follow-Up

**SNOMED Codes Extracted (All 3):**

| Code | Description | Category | Score | Filtered? |
|------|-------------|----------|-------|-----------|
| 38341003 | Hypertensive disorder | MEDICAL_CONDITION | 0.627 | ❌ Wrong category |
| 75367002 | Blood pressure | TEST_TREATMENT_PROCEDURE | 0.002 | ❌ Score too low |
| 38341003 | Hypertensive disorder | MEDICAL_CONDITION | 0.280 | ❌ Wrong category |

**Result**: All 3 filtered out (0 passed)

**Why This is Correct:**
- Hypertension is a diagnosis, not a procedure → Use ICD-10 instead
- Blood pressure has 0.2% confidence → Unreliable
- No billable procedures in this simple follow-up visit

## Category Definitions

### TEST_TREATMENT_PROCEDURE
Includes:
- Diagnostic procedures (colonoscopy, MRI, x-ray)
- Therapeutic procedures (surgery, injections, therapy)
- Tests and measurements (lab tests, vitals when procedural)

**Billable via**: CPT codes

### MEDICAL_CONDITION
Includes:
- Diagnoses (hypertension, diabetes, infections)
- Symptoms (pain, fever, nausea)
- Clinical findings

**Billable via**: ICD-10 codes (not CPT)

### Other Categories
- `MEDICATION`: Prescriptions, drugs
- `ANATOMY`: Body parts, organs
- `PROTECTED_HEALTH_INFORMATION`: PHI entities

These are **not used for crosswalk** as they don't map to CPT codes.

## Confidence Score Threshold

### Why 0.2?

| Score Range | Interpretation | Action |
|-------------|----------------|--------|
| **0.8 - 1.0** | High confidence | ✅ Use for crosswalk |
| **0.5 - 0.79** | Medium confidence | ✅ Use for crosswalk |
| **0.21 - 0.49** | Low-medium confidence | ✅ Use for crosswalk (marginal) |
| **0.0 - 0.2** | Very low confidence | ❌ Filter out (likely noise) |

### Rationale for 0.2
- AWS Comprehend Medical scores < 0.2 are typically extraction errors
- Example: "BP" → 0.002 (0.2% confidence) is clearly noise
- Threshold of 0.2 (20%) is conservative but filters obvious false positives

### Future Tuning
The threshold can be adjusted based on:
- Crosswalk hit/miss rates
- LLM feedback on suggestion quality
- Manual review of filtered codes

## Impact on Processing

### Storage
- ✅ **All SNOMED codes** (including filtered) are stored in database
- ✅ Database records include category and score for future analysis
- ✅ Audit trail maintains complete extraction history

### Crosswalk
- ✅ **Only filtered codes** are sent to crosswalk service
- ✅ Reduces unnecessary database lookups
- ✅ Improves cache hit rates

### LLM Input
- ✅ **Filtered codes** passed to LLM in structured format
- ✅ Smaller, more relevant code lists
- ✅ Reduces token usage and improves focus

### Logging
```json
{
  "event": "SNOMED codes filtered for crosswalk",
  "total_snomed_codes": 3,
  "filtered_procedure_codes": 0,
  "filtered_out": 3
}
```

## Configuration

### Current Settings
- **Location**: `app/tasks/phi_processing.py` (line 245-248)
- **Category**: `TEST_TREATMENT_PROCEDURE`
- **Score threshold**: `0.2`
- **Applied to**: Crosswalk only (database stores all)

### Changing Thresholds

To adjust filtering criteria:

```python
# Option 1: More permissive (include low confidence)
filtered_snomed = [
    e for e in snomed_entities
    if e.category == "TEST_TREATMENT_PROCEDURE" and e.score > 0.1
]

# Option 2: More restrictive (high confidence only)
filtered_snomed = [
    e for e in snomed_entities
    if e.category == "TEST_TREATMENT_PROCEDURE" and e.score > 0.5
]

# Option 3: Include multiple categories
filtered_snomed = [
    e for e in snomed_entities
    if e.category in ["TEST_TREATMENT_PROCEDURE", "ANATOMY"]
    and e.score > 0.2
]
```

## Monitoring Recommendations

### Metrics to Track
1. **Filter rate**: `filtered_out / total_snomed_codes`
2. **Crosswalk hit rate**: CPT mappings found for filtered codes
3. **LLM suggestion accuracy**: Are filtered codes producing good CPT suggestions?

### Alert Conditions
- ⚠️ If filter rate > 90%: May be too restrictive
- ⚠️ If filter rate < 10%: May need stricter criteria
- ⚠️ If crosswalk hit rate < 20%: Threshold may be too low

## Examples of Filtered vs Passed Codes

### Passed (Score > 0.2, Category = Procedure)

| Code | Description | Category | Score | Crosswalk? |
|------|-------------|----------|-------|------------|
| 73761001 | Colonoscopy | TEST_TREATMENT_PROCEDURE | 0.95 | ✅ Yes |
| 80146002 | Appendectomy | TEST_TREATMENT_PROCEDURE | 0.92 | ✅ Yes |
| 82078001 | MRI of brain | TEST_TREATMENT_PROCEDURE | 0.88 | ✅ Yes |

### Filtered Out (Wrong Category)

| Code | Description | Category | Score | Reason |
|------|-------------|----------|-------|--------|
| 38341003 | Hypertension | MEDICAL_CONDITION | 0.85 | Diagnosis, not procedure |
| 73211009 | Diabetes | MEDICAL_CONDITION | 0.92 | Diagnosis, not procedure |

### Filtered Out (Low Score)

| Code | Description | Category | Score | Reason |
|------|-------------|----------|-------|--------|
| 75367002 | Blood pressure | TEST_TREATMENT_PROCEDURE | 0.002 | 0.2% confidence (noise) |
| 12345678 | Unknown test | TEST_TREATMENT_PROCEDURE | 0.15 | 15% confidence (unreliable) |

## Testing

Run the test script to see filtering in action:

```bash
cd backend
source venv/bin/activate
python scripts/test_comprehend_medical.py
```

Output shows:
- All extracted SNOMED codes
- Filtering criteria applied
- Which codes passed/failed
- Rejection reasons for filtered codes

## Related Documentation

- [SNOMED CPT Crosswalk Overview](SNOMED_CPT_CROSSWALK.md)
- [PHI Processing Integration](PHI_PROCESSING_INTEGRATION.md)
- [Comprehend Medical Test Analysis](COMPREHEND_MEDICAL_TEST_ANALYSIS.md)
