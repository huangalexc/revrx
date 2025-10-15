#!/usr/bin/env python3
"""
Test ICD-10 Filtering with COPD Case

Demonstrates how diagnosis entity filtering reduces ICD-10 codes from 9 to 3.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.comprehend_medical import comprehend_medical_service
from app.utils.icd10_filtering import get_diagnosis_entities, filter_icd10_codes, deduplicate_icd10_codes


# COPD Exacerbation Test Case
TEST_NOTE = """52-year-old male presents with worsening shortness of breath over 2 days.
Past medical history significant for chronic obstructive pulmonary disease (COPD) and hypertension.
On exam: diffuse wheezing, decreased air movement. No fever.
Impression: COPD exacerbation.
Plan: Nebulized bronchodilators, oral prednisone. Continue lisinopril for blood pressure."""


async def main():
    """Test ICD-10 filtering"""

    print("=" * 80)
    print("ICD-10 FILTERING DEMONSTRATION")
    print("=" * 80)
    print("\nClinical Note:")
    print("-" * 80)
    print(TEST_NOTE)
    print("-" * 80)

    # Step 1: Extract medical entities
    print("\n" + "=" * 80)
    print("STEP 1: DETECT ENTITIES")
    print("=" * 80)

    medical_entities = comprehend_medical_service.detect_entities(TEST_NOTE)

    # Find MEDICAL_CONDITION entities
    medical_conditions = [e for e in medical_entities if e.category == "MEDICAL_CONDITION"]

    print(f"\nTotal MEDICAL_CONDITION entities: {len(medical_conditions)}")
    for entity in medical_conditions:
        traits_str = ""
        if entity.traits:
            trait_names = [t.get('Name', '') for t in entity.traits]
            traits_str = f" [{', '.join(trait_names)}]"

        print(f"  - {entity.text}{traits_str} (score: {entity.score:.3f})")

    # Step 2: Extract diagnosis entities
    print("\n" + "=" * 80)
    print("STEP 2: FILTER TO DIAGNOSIS ENTITIES")
    print("Criteria: Trait=DIAGNOSIS, Exclude=NEGATION")
    print("=" * 80)

    diagnosis_entities = get_diagnosis_entities(medical_entities)

    print(f"\nDiagnosis entities: {len(diagnosis_entities)}")
    for entity in diagnosis_entities:
        print(f"  ✓ {entity.text} (score: {entity.score:.3f})")

    # Step 3: Extract ICD-10 codes
    print("\n" + "=" * 80)
    print("STEP 3: INFER ICD-10-CM (All Codes)")
    print("=" * 80)

    icd10_entities = comprehend_medical_service.infer_icd10_cm(TEST_NOTE)

    print(f"\nTotal ICD-10 codes extracted: {len(icd10_entities)}")
    for entity in icd10_entities:
        print(f"  - {entity.code}: {entity.description}")
        print(f"    Text: '{entity.text}' (score: {entity.score:.3f})")

    # Step 4: Filter ICD-10 codes
    print("\n" + "=" * 80)
    print("STEP 4: FILTER ICD-10 CODES USING DIAGNOSIS ENTITIES")
    print("=" * 80)

    filtered_icd10, filter_stats = filter_icd10_codes(
        icd10_entities=icd10_entities,
        diagnosis_entities=diagnosis_entities,
        min_match_score=0.5
    )

    print(f"\nFiltering stats:")
    print(f"  Total ICD-10 codes: {filter_stats['total_icd10']}")
    print(f"  Diagnosis entities: {filter_stats['diagnosis_entities']}")
    print(f"  Match threshold: {filter_stats['match_threshold']}")
    print(f"  Filtered (kept): {filter_stats['filtered_icd10']}")
    print(f"  Filtered out: {filter_stats['filtered_out']}")

    print(f"\n✅ Kept (matched to diagnoses):")
    for entity in filtered_icd10:
        print(f"  - {entity.code}: {entity.description}")
        print(f"    Text: '{entity.text}' (score: {entity.score:.3f})")

    # Step 5: Deduplicate
    print("\n" + "=" * 80)
    print("STEP 5: DEDUPLICATE ICD-10 CODES")
    print("=" * 80)

    deduplicated_icd10 = deduplicate_icd10_codes(filtered_icd10)

    print(f"\nDeduplicated codes: {len(deduplicated_icd10)}")
    for entity in deduplicated_icd10:
        print(f"  - {entity.code}: {entity.description}")
        print(f"    Text: '{entity.text}' (score: {entity.score:.3f})")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nOriginal ICD-10 codes: {len(icd10_entities)}")
    print(f"After filtering: {len(filtered_icd10)}")
    print(f"After deduplication: {len(deduplicated_icd10)}")
    print(f"\nReduction: {len(icd10_entities)} → {len(deduplicated_icd10)} codes")
    print(f"Filtered out: {len(icd10_entities) - len(deduplicated_icd10)} codes")

    print("\n" + "=" * 80)
    print("FINAL ICD-10 CODES FOR LLM")
    print("=" * 80)

    expected_codes = {"J44.9", "J44.1", "I10"}
    actual_codes = {e.code for e in deduplicated_icd10}

    for code in sorted(actual_codes):
        entity = next(e for e in deduplicated_icd10 if e.code == code)
        marker = "✅" if code in expected_codes else "⚠️"
        print(f"{marker} {code}: {entity.description}")

    print("\n" + "=" * 80)
    print("EXPECTED vs ACTUAL")
    print("=" * 80)
    print(f"\nExpected codes: {sorted(expected_codes)}")
    print(f"Actual codes:   {sorted(actual_codes)}")

    if actual_codes == expected_codes:
        print("\n✅ SUCCESS: Filtering produced expected result!")
    else:
        missing = expected_codes - actual_codes
        extra = actual_codes - expected_codes
        if missing:
            print(f"\n⚠️  Missing codes: {missing}")
        if extra:
            print(f"\n⚠️  Extra codes: {extra}")


if __name__ == "__main__":
    asyncio.run(main())
