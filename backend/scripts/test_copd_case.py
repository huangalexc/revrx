#!/usr/bin/env python3
"""
Test Amazon Comprehend Medical with COPD Exacerbation Case

This script tests if Comprehend Medical correctly extracts J44.1 (COPD with exacerbation)
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.comprehend_medical import comprehend_medical_service


# COPD Exacerbation Test Case
TEST_NOTE = """52-year-old male presents with worsening shortness of breath over 2 days.
Past medical history significant for chronic obstructive pulmonary disease (COPD) and hypertension.
On exam: diffuse wheezing, decreased air movement. No fever.
Impression: COPD exacerbation.
Plan: Nebulized bronchodilators, oral prednisone. Continue lisinopril for blood pressure."""


async def main():
    """Run COPD test case through Comprehend Medical"""

    print("=" * 80)
    print("TEST CASE: COPD Exacerbation")
    print("=" * 80)
    print("\nClinical Note:")
    print("-" * 80)
    print(TEST_NOTE)
    print("-" * 80)

    print("\nExpected ICD-10:")
    print("- J44.1 (COPD with acute exacerbation)")
    print("- I10 (Hypertension)")

    print("\n" + "=" * 80)
    print("COMPREHEND MEDICAL RESULTS")
    print("=" * 80)

    # 1. Detect Entities V2
    print("\n1. DETECT ENTITIES V2 (General Medical Entities)")
    print("-" * 80)
    try:
        entities = comprehend_medical_service.detect_entities_v2(TEST_NOTE)

        if entities:
            # Group by category
            by_category = {}
            for entity in entities:
                if entity.category not in by_category:
                    by_category[entity.category] = []
                by_category[entity.category].append(entity)

            for category, ents in sorted(by_category.items()):
                print(f"\n{category}:")
                for e in ents:
                    print(f"  - {e.text}")
                    print(f"    Type: {e.type}")
                    print(f"    Score: {e.score:.3f}")
                    if e.traits:
                        traits_str = ", ".join([t.get('Name', '') for t in e.traits])
                        print(f"    Traits: {traits_str}")

            print(f"\nTotal entities: {len(entities)}")
        else:
            print("No entities detected")

    except Exception as e:
        print(f"Error: {e}")

    # 2. Infer ICD-10-CM
    print("\n\n2. INFER ICD-10-CM (Diagnosis Codes)")
    print("-" * 80)
    try:
        icd10_entities = comprehend_medical_service.infer_icd10_cm(TEST_NOTE)

        if icd10_entities:
            print(f"\nTotal ICD-10 codes extracted: {len(icd10_entities)}\n")

            # Check if J44.1 was found
            found_j44_1 = False
            found_i10 = False

            for entity in icd10_entities:
                marker = ""
                if entity.code == "J44.1":
                    marker = "  ✅ CORRECT - COPD with exacerbation detected!"
                    found_j44_1 = True
                elif entity.code == "I10":
                    marker = "  ✅ Also correct - Hypertension detected"
                    found_i10 = True

                print(f"Code: {entity.code}{marker}")
                print(f"  Description: {entity.description}")
                print(f"  Text: '{entity.text}'")
                print(f"  Category: {entity.category}")
                print(f"  Type: {entity.type}")
                print(f"  Score: {entity.score:.3f}")
                print()

            # Summary
            print("=" * 80)
            print("ICD-10 EXTRACTION SUMMARY")
            print("=" * 80)
            if found_j44_1:
                print("✅ J44.1 (COPD with exacerbation): FOUND")
            else:
                print("❌ J44.1 (COPD with exacerbation): NOT FOUND")

            if found_i10:
                print("✅ I10 (Hypertension): FOUND")
            else:
                print("⚠️  I10 (Hypertension): NOT FOUND")

            print("=" * 80)
        else:
            print("❌ No ICD-10 codes detected")

    except Exception as e:
        print(f"Error: {e}")

    # 3. Infer SNOMED CT
    print("\n\n3. INFER SNOMED CT (Procedure Codes)")
    print("-" * 80)
    try:
        snomed_entities = comprehend_medical_service.infer_snomed_ct(TEST_NOTE)

        if snomed_entities:
            for entity in snomed_entities:
                print(f"\nCode: {entity.code}")
                print(f"  Description: {entity.description}")
                print(f"  Text: '{entity.text}'")
                print(f"  Category: {entity.category}")
                print(f"  Type: {entity.type}")
                print(f"  Score: {entity.score:.3f}")

            print(f"\nTotal SNOMED codes: {len(snomed_entities)}")

            # Apply filtering
            filtered_snomed = [
                e for e in snomed_entities
                if e.category == "TEST_TREATMENT_PROCEDURE" and e.score > 0.2
            ]

            print(f"\n" + "=" * 80)
            print("FILTERED SNOMED CODES (for crosswalk)")
            print("Criteria: category == 'TEST_TREATMENT_PROCEDURE' AND score > 0.2")
            print("=" * 80)

            if filtered_snomed:
                for entity in filtered_snomed:
                    print(f"\n  ✓ Code: {entity.code}")
                    print(f"    Description: {entity.description}")
                    print(f"    Text: '{entity.text}'")
                    print(f"    Score: {entity.score:.3f}")
                print(f"\nFiltered codes: {len(filtered_snomed)} (passed)")
                print(f"Filtered out: {len(snomed_entities) - len(filtered_snomed)} (rejected)")
            else:
                print("\n  No SNOMED codes passed filtering criteria")
                print(f"  All {len(snomed_entities)} codes were filtered out")

                # Show why they were filtered
                print("\n  Rejection reasons:")
                for entity in snomed_entities:
                    reasons = []
                    if entity.category != "TEST_TREATMENT_PROCEDURE":
                        reasons.append(f"category={entity.category}")
                    if entity.score <= 0.2:
                        reasons.append(f"score={entity.score:.3f}≤0.2")
                    print(f"    - {entity.code}: {', '.join(reasons)}")

        else:
            print("No SNOMED codes detected")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
