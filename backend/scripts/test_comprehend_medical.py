#!/usr/bin/env python3
"""
Test Amazon Comprehend Medical with Test Case 1

This script runs a clinical note through all Comprehend Medical APIs
to see what entities are extracted.
"""

import asyncio
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.comprehend_medical import comprehend_medical_service


# Test Case 1 from scripts/example_codes.txt
TEST_NOTE = """Patient presents for follow-up on hypertension. BP recorded as 150/95.
Assessment: Hypertension, uncontrolled.
Plan: Continue lisinopril, follow up in 6 months."""


async def main():
    """Run test case through all Comprehend Medical APIs"""

    print("=" * 80)
    print("TEST CASE 1: Missing Documentation → Downcoding")
    print("=" * 80)
    print("\nClinical Note:")
    print("-" * 80)
    print(TEST_NOTE)
    print("-" * 80)

    print("\nBilled Codes:")
    print("- 99214 (Level 4 established patient visit)")

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
            for entity in icd10_entities:
                print(f"\n  Code: {entity.code}")
                print(f"  Description: {entity.description}")
                print(f"  Text: '{entity.text}'")
                print(f"  Category: {entity.category}")
                print(f"  Type: {entity.type}")
                print(f"  Score: {entity.score:.3f}")

            print(f"\nTotal ICD-10 codes: {len(icd10_entities)}")
        else:
            print("No ICD-10 codes detected")

    except Exception as e:
        print(f"Error: {e}")

    # 3. Infer SNOMED CT
    print("\n\n3. INFER SNOMED CT (Procedure Codes)")
    print("-" * 80)
    try:
        snomed_entities = comprehend_medical_service.infer_snomed_ct(TEST_NOTE)

        if snomed_entities:
            for entity in snomed_entities:
                print(f"\n  Code: {entity.code}")
                print(f"  Description: {entity.description}")
                print(f"  Text: '{entity.text}'")
                print(f"  Category: {entity.category}")
                print(f"  Type: {entity.type}")
                print(f"  Score: {entity.score:.3f}")

            print(f"\nTotal SNOMED codes: {len(snomed_entities)}")

            # Apply filtering for crosswalk
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

    # Summary
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print("\nExpected Outputs:")
    print("- Feature Flag: Missing documentation elements")
    print("- Suggestion: Consider 99213 unless more HPI/ROS/exam elements documented")
    print("- Justification: Level 4 requires more detailed documentation")

    print("\n" + "=" * 80)
    print("KEY OBSERVATIONS")
    print("=" * 80)
    print("""
1. Comprehend Medical extracts CLINICAL entities (diagnoses, medications, vitals)
2. It does NOT extract billing/coding-related information like:
   - E/M visit levels (99214, 99213)
   - Documentation elements (HPI, ROS, exam)
   - Billing compliance issues

3. For this test case, we'd expect:
   - ICD-10: I10 (Hypertension) or I15.9 (Uncontrolled hypertension)
   - SNOMED: Procedure codes related to follow-up visits
   - Medical entities: Blood pressure measurement, medication (lisinopril)

4. The LLM is still needed for:
   - E/M level assessment (99214 vs 99213)
   - Documentation quality review
   - Billing compliance and risk assessment
   - Coding suggestions based on visit complexity
    """)


if __name__ == "__main__":
    asyncio.run(main())
