# SNOMED Filtering Implementation

## Overview

The SNOMED filtering system uses **fuzzy text matching** with DetectEntitiesV2 procedure entities to filter SNOMED CT codes from InferSNOMEDCT, addressing the issue where InferSNOMEDCT can give very low confidence scores even for valid procedures.

## Problem Solved

**Original Issue**: InferSNOMEDCT sometimes gives very low confidence scores (e.g., 4.8%) for valid procedures, even when DetectEntitiesV2 identifies them with high confidence (e.g., 66%).

**Example - Otitis Media Case**:
- DetectEntitiesV2: "Ear lavage" detected with 66% confidence as TEST_TREATMENT_PROCEDURE
- InferSNOMEDCT: Same "Ear lavage" mapped to SNOMED code 468975002 with only 4.8% confidence
- Previous score-based filtering (>0.2) would have filtered this out ❌

## Solution: Two-Stage Filtering

### Stage 1: Extract High-Confidence Procedure Entities
```python
from app.utils.icd10_filtering import get_procedure_entities

procedure_entities = get_procedure_entities(
    medical_entities,  # From DetectEntitiesV2
    min_score=0.5      # 50% confidence threshold
)
```

**Criteria**:
- Category: `TEST_TREATMENT_PROCEDURE`
- Score: ≥ 0.5 (50%)

### Stage 2: Fuzzy Text Match to SNOMED Codes
```python
from app.utils.icd10_filtering import filter_snomed_codes

filtered_snomed, stats = filter_snomed_codes(
    snomed_entities=snomed_entities,      # From InferSNOMEDCT
    procedure_entities=procedure_entities, # From Stage 1
    min_match_score=0.5                   # 50% similarity threshold
)
```

**Criteria**:
- SNOMED code category: `TEST_TREATMENT_PROCEDURE`
- Fuzzy match score: ≥ 0.5 (50% text similarity to procedure entity)

## Fuzzy Matching Algorithm

Uses `difflib.SequenceMatcher` for text similarity:

1. **Exact match**: Score = 1.0
   - Example: "Ear lavage" ↔ "Ear lavage"

2. **Containment match**: Score = 0.9
   - Example: "Ear" in "Ear lavage"

3. **Sequence similarity**: Score = ratio(text1, text2)
   - Example: "ear lavage" ↔ "ear canal lavage" → ~0.8

## Results - Otitis Media Test Case

**Input Note**:
> "Patient presents with otitis media. Ear lavage performed. Prescribed amoxicillin."

**Stage 1 - Procedure Entities (DetectEntitiesV2)**:
- ✅ "Ear lavage" (score: 0.660)

**Stage 2 - SNOMED Filtering**:

| SNOMED Code | Description | Category | AWS Score | Match Score | Result |
|-------------|-------------|----------|-----------|-------------|--------|
| 65363002 | Otitis media (disorder) | MEDICAL_CONDITION | 0.763 | - | ❌ Excluded (wrong category) |
| 117590005 | Ear structure | ANATOMY | 0.076 | - | ❌ Excluded (wrong category) |
| **468975002** | **Ear canal lavage system** | **TEST_TREATMENT_PROCEDURE** | **0.048** | **1.0** | **✅ Included** |

**Final Output to LLM**:
- ICD-10: H66.90 (Otitis media, unspecified)
- SNOMED: 468975002 (Ear canal lavage system)
  - Will be mapped to CPT 69210 via crosswalk

## Implementation Files

### Core Filtering Logic
- **`app/utils/icd10_filtering.py`**:
  - `get_procedure_entities()` - Extract high-confidence procedure entities
  - `filter_snomed_codes()` - Fuzzy match SNOMED codes to procedures
  - `fuzzy_match_score()` - Text similarity calculation

### PHI Processing Integration
- **`app/tasks/phi_processing.py`** (lines 238-314):
  ```python
  # Get procedure entities from DetectEntitiesV2 (score > 0.5)
  procedure_entities = get_procedure_entities(
      medical_entities,
      min_score=0.5
  )

  # Filter SNOMED codes using fuzzy text matching
  filtered_snomed_entities, snomed_filter_stats = filter_snomed_codes(
      snomed_entities=snomed_entities,
      procedure_entities=procedure_entities,
      min_match_score=0.5
  )
  ```

### Test Scripts
- **`backend/scripts/test_otitis_media.py`** - Demonstrates SNOMED filtering with otitis media case

## Comparison: ICD-10 vs SNOMED Filtering

Both use the same two-stage fuzzy matching approach:

| Aspect | ICD-10 Filtering | SNOMED Filtering |
|--------|------------------|------------------|
| **Stage 1 Source** | DetectEntitiesV2 | DetectEntitiesV2 |
| **Stage 1 Category** | MEDICAL_CONDITION | TEST_TREATMENT_PROCEDURE |
| **Stage 1 Traits** | DIAGNOSIS or SYMPTOM (exclude NEGATION) | N/A (no traits) |
| **Stage 1 Score** | Any score | ≥ 0.5 |
| **Stage 2 Source** | InferICD10CM | InferSNOMEDCT |
| **Stage 2 Category Filter** | None | TEST_TREATMENT_PROCEDURE |
| **Match Threshold** | 0.6 (for filtering in tests) | 0.5 |
| **Match Threshold in Pipeline** | 0.6 | 0.5 |

## Benefits

1. **Increased Recall**: Captures valid procedures even when InferSNOMEDCT gives low confidence
2. **Maintains Precision**: Still requires TEST_TREATMENT_PROCEDURE category and text similarity
3. **Consistent Approach**: Same fuzzy matching pattern as ICD-10 filtering
4. **Robust to API Variations**: Less dependent on InferSNOMEDCT confidence scores

## Monitoring

Structured logging tracks filtering performance:

```python
logger.info(
    "snomed_filtering_complete",
    total_snomed=3,
    filtered_snomed=1,
    filtered_out=2,
    procedure_entities=1,
    match_threshold=0.5
)
```

## Future Enhancements

1. **Adaptive Thresholds**: Adjust match score threshold based on procedure complexity
2. **Synonym Expansion**: Include medical synonyms in fuzzy matching
3. **Context-Aware Matching**: Consider anatomical context (e.g., "ear" + "lavage")
4. **Machine Learning**: Train classifier on successful matches vs. false positives
