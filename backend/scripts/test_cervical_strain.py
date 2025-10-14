#!/usr/bin/env python3
"""
Test ICD-10 Filtering with Cervical Strain Case

Goal: Extract S16.1XXA (cervical strain) and R51.9 (headache)
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.comprehend_medical import comprehend_medical_service
from app.utils.icd10_filtering import get_diagnosis_entities, filter_icd10_codes, deduplicate_icd10_codes


# Cervical Strain Test Case
TEST_NOTE = """Patient seen for follow-up after motor vehicle collision one week ago.
Reports persistent neck pain and mild headache.
Exam: paraspinal tenderness, limited range of motion, no neurological deficit.
Diagnoses: cervical strain.
Plan: NSAIDs, physical therapy referral."""


async def main():
    """Test ICD-10 filtering for cervical strain"""

    print("=" * 80)
    print("CERVICAL STRAIN - ICD-10 FILTERING TEST")
    print("=" * 80)
    print("\nClinical Note:")
    print("-" * 80)
    print(TEST_NOTE)
    print("-" * 80)

    print("\nExpected ICD-10:")
    print("- S16.1XXA (Strain of muscle, fascia and tendon at neck level, initial encounter)")
    print("- R51.9 (Headache, unspecified)")

    # Step 1: Extract medical entities
    print("\n" + "=" * 80)
    print("STEP 1: DETECT ENTITIES V2")
    print("=" * 80)

    medical_entities = comprehend_medical_service.detect_entities_v2(TEST_NOTE)

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
        marker = ""
        if entity.code == "S16.1XXA":
            marker = "  ← TARGET CODE"
        elif entity.code == "R51.9" or entity.code.startswith("R51"):
            marker = "  ← HEADACHE CODE"

        print(f"  - {entity.code}: {entity.description}{marker}")
        print(f"    Text: '{entity.text}' (score: {entity.score:.3f})")

    # Step 4: Filter ICD-10 codes
    print("\n" + "=" * 80)
    print("STEP 4: FILTER ICD-10 CODES (threshold 0.6)")
    print("=" * 80)

    filtered_icd10, filter_stats = filter_icd10_codes(
        icd10_entities=icd10_entities,
        diagnosis_entities=diagnosis_entities,
        min_match_score=0.6
    )

    print(f"\nFiltering stats:")
    print(f"  Total ICD-10 codes: {filter_stats['total_icd10']}")
    print(f"  Diagnosis entities: {filter_stats['diagnosis_entities']}")
    print(f"  Filtered (kept): {filter_stats['filtered_icd10']}")
    print(f"  Filtered out: {filter_stats['filtered_out']}")

    if filtered_icd10:
        print(f"\n✅ Kept (matched to diagnoses):")
        for entity in filtered_icd10:
            marker = ""
            if entity.code == "S16.1XXA":
                marker = "  ✅ TARGET CODE"
            elif entity.code == "R51.9" or entity.code.startswith("R51"):
                marker = "  ✅ HEADACHE CODE"

            print(f"  - {entity.code}: {entity.description}{marker}")
            print(f"    Text: '{entity.text}' (score: {entity.score:.3f})")
    else:
        print("\n❌ No codes passed filtering")

    # Step 5: Deduplicate
    print("\n" + "=" * 80)
    print("STEP 5: DEDUPLICATE")
    print("=" * 80)

    deduplicated_icd10 = deduplicate_icd10_codes(filtered_icd10)

    print(f"\nFinal codes: {len(deduplicated_icd10)}")
    for entity in deduplicated_icd10:
        marker = ""
        if entity.code == "S16.1XXA":
            marker = "  ✅ CORRECT"
        elif entity.code == "R51.9" or entity.code.startswith("R51"):
            marker = "  ✅ CORRECT"

        print(f"  - {entity.code}: {entity.description}{marker}")
        print(f"    Text: '{entity.text}' (score: {entity.score:.3f})")

    # Summary
    print("\n" + "=" * 80)
    print("RESULT ANALYSIS")
    print("=" * 80)

    expected_codes = {"S16.1XXA", "R51.9"}
    actual_codes = {e.code for e in deduplicated_icd10}

    # Check for R51 variants
    has_headache_code = any(code.startswith("R51") for code in actual_codes)

    print(f"\nExpected codes: {sorted(expected_codes)}")
    print(f"Actual codes:   {sorted(actual_codes)}")

    # Check S16.1XXA
    if "S16.1XXA" in actual_codes:
        print("\n✅ SUCCESS: S16.1XXA (cervical strain) found!")
    else:
        print("\n❌ MISSING: S16.1XXA (cervical strain) not found")

    # Check for headache
    if "R51.9" in actual_codes or has_headache_code:
        if "R51.9" in actual_codes:
            print("✅ SUCCESS: R51.9 (headache) found!")
        else:
            headache_code = next(code for code in actual_codes if code.startswith("R51"))
            print(f"⚠️  PARTIAL: {headache_code} (headache) found instead of R51.9")
    else:
        print("❌ MISSING: Headache code not found")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
