#!/usr/bin/env python3
"""
Test ICD-10 and SNOMED Filtering with Otitis Media Case

Shows both filtered ICD-10 codes and filtered SNOMED procedure codes.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.comprehend_medical import comprehend_medical_service
from app.utils.icd10_filtering import (
    get_diagnosis_entities,
    filter_icd10_codes,
    deduplicate_icd10_codes,
    get_procedure_entities,
    filter_snomed_codes
)


# Otitis Media Test Case
TEST_NOTE = """Patient presents with otitis media. Ear lavage performed.
Prescribed amoxicillin."""


async def main():
    """Test ICD-10 and SNOMED filtering for otitis media"""

    print("=" * 80)
    print("OTITIS MEDIA - ICD-10 & SNOMED FILTERING TEST")
    print("=" * 80)
    print("\nClinical Note:")
    print("-" * 80)
    print(TEST_NOTE)
    print("-" * 80)

    print("\nProvider Billed Codes:")
    print("- 99213 (office visit)")
    print("- 69210 (ear lavage)")

    # Step 1: Extract medical entities
    print("\n" + "=" * 80)
    print("STEP 1: DETECT ENTITIES V2")
    print("=" * 80)

    medical_entities = comprehend_medical_service.detect_entities_v2(TEST_NOTE)

    # Show all entities by category
    by_category = {}
    for entity in medical_entities:
        if entity.category not in by_category:
            by_category[entity.category] = []
        by_category[entity.category].append(entity)

    for category in sorted(by_category.keys()):
        print(f"\n{category}:")
        for entity in by_category[category]:
            traits_str = ""
            if entity.traits:
                trait_names = [t.get('Name', '') for t in entity.traits]
                traits_str = f" [{', '.join(trait_names)}]"
            print(f"  - {entity.text}{traits_str} (score: {entity.score:.3f})")

    # Step 2: Extract diagnosis/symptom entities
    print("\n" + "=" * 80)
    print("STEP 2: FILTER TO DIAGNOSIS/SYMPTOM ENTITIES")
    print("Criteria: DIAGNOSIS or SYMPTOM, exclude NEGATION")
    print("=" * 80)

    diagnosis_entities = get_diagnosis_entities(medical_entities)

    print(f"\nDiagnosis/Symptom entities: {len(diagnosis_entities)}")
    for entity in diagnosis_entities:
        traits_str = ""
        if entity.traits:
            trait_names = [t.get('Name', '') for t in entity.traits]
            traits_str = f" [{', '.join(trait_names)}]"
        print(f"  ✓ {entity.text}{traits_str} (score: {entity.score:.3f})")

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
    print("STEP 4: FILTER ICD-10 CODES (threshold 0.6)")
    print("=" * 80)

    if icd10_entities and diagnosis_entities:
        filtered_icd10, filter_stats = filter_icd10_codes(
            icd10_entities=icd10_entities,
            diagnosis_entities=diagnosis_entities,
            min_match_score=0.6
        )

        deduplicated_icd10 = deduplicate_icd10_codes(filtered_icd10)

        print(f"\nFiltered ICD-10 codes: {len(deduplicated_icd10)}")
        for entity in deduplicated_icd10:
            print(f"  ✅ {entity.code}: {entity.description}")
            print(f"     Text: '{entity.text}' (score: {entity.score:.3f})")
    else:
        print("\n⚠️  No ICD-10 codes or diagnosis entities to filter")
        deduplicated_icd10 = []

    # Step 5: Extract SNOMED codes
    print("\n" + "=" * 80)
    print("STEP 5: INFER SNOMED CT (All Codes)")
    print("=" * 80)

    snomed_entities = comprehend_medical_service.infer_snomed_ct(TEST_NOTE)

    print(f"\nTotal SNOMED codes extracted: {len(snomed_entities)}")
    for entity in snomed_entities:
        print(f"\n  - Code: {entity.code}")
        print(f"    Description: {entity.description}")
        print(f"    Text: '{entity.text}'")
        print(f"    Category: {entity.category}")
        print(f"    Type: {entity.type}")
        print(f"    Score: {entity.score:.3f}")

    # Step 6: Extract procedure entities from DetectEntitiesV2
    print("\n" + "=" * 80)
    print("STEP 6: EXTRACT PROCEDURE ENTITIES (DetectEntitiesV2)")
    print("Criteria: category = TEST_TREATMENT_PROCEDURE AND score > 0.5")
    print("=" * 80)

    procedure_entities = get_procedure_entities(
        medical_entities,
        min_score=0.5
    )

    print(f"\nProcedure entities: {len(procedure_entities)}")
    for entity in procedure_entities:
        print(f"  ✓ {entity.text} (score: {entity.score:.3f})")

    # Step 7: Filter SNOMED codes with fuzzy text matching
    print("\n" + "=" * 80)
    print("STEP 7: FILTER SNOMED CODES (Fuzzy Text Matching)")
    print("Match SNOMED codes to procedure entities (threshold 0.5)")
    print("=" * 80)

    if snomed_entities and procedure_entities:
        filtered_snomed, snomed_filter_stats = filter_snomed_codes(
            snomed_entities=snomed_entities,
            procedure_entities=procedure_entities,
            min_match_score=0.5
        )

        print(f"\nFilter statistics:")
        print(f"  Total SNOMED codes: {snomed_filter_stats['total_snomed']}")
        print(f"  Procedure entities: {snomed_filter_stats['procedure_entities']}")
        print(f"  Filtered SNOMED codes: {snomed_filter_stats['filtered_snomed']}")
        print(f"  Filtered out: {snomed_filter_stats['filtered_out']}")

        if filtered_snomed:
            print(f"\nFiltered SNOMED procedure codes: {len(filtered_snomed)}")
            for entity in filtered_snomed:
                print(f"\n  ✅ Code: {entity.code}")
                print(f"     Description: {entity.description}")
                print(f"     Text: '{entity.text}'")
                print(f"     Score: {entity.score:.3f}")
        else:
            print(f"\n⚠️  No SNOMED codes matched procedure entities")
    else:
        print(f"\n⚠️  Missing data for SNOMED filtering")
        print(f"   SNOMED entities: {len(snomed_entities)}")
        print(f"   Procedure entities: {len(procedure_entities)}")
        filtered_snomed = []

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY - DATA FOR LLM")
    print("=" * 80)

    print(f"\n📋 ICD-10 Codes (Diagnoses): {len(deduplicated_icd10)}")
    for entity in deduplicated_icd10:
        print(f"   - {entity.code}: {entity.description}")

    print(f"\n🔧 SNOMED Procedure Codes: {len(filtered_snomed)}")
    for entity in filtered_snomed:
        print(f"   - {entity.code}: {entity.description}")

    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    print("\nExpected extractions:")
    print("- ICD-10: H66.x (Otitis media code)")
    print("- SNOMED: Ear lavage/irrigation procedure code")
    print("- Medication: Amoxicillin")

    print("\nNote: E/M level (99213) and specific CPT (69210) require:")
    print("- LLM for E/M visit complexity assessment")
    print("- SNOMED → CPT crosswalk for procedure code mapping")


if __name__ == "__main__":
    asyncio.run(main())
