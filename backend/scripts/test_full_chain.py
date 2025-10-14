#!/usr/bin/env python3
"""
Test Full Processing Chain

Runs the complete processing pipeline:
1. Clinical Relevance Filtering (GPT-4o-mini)
2. DetectEntitiesV2
3. InferICD10CM
4. ICD-10 Filtering (fuzzy matching)
5. InferSNOMEDCT
6. SNOMED Filtering (fuzzy matching)
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.openai_service import openai_service
from app.services.comprehend_medical import comprehend_medical_service
from app.utils.icd10_filtering import (
    get_diagnosis_entities,
    filter_icd10_codes,
    deduplicate_icd10_codes,
    get_procedure_entities,
    filter_snomed_codes
)


async def main():
    """Test full processing chain"""

    # Read example chart
    script_dir = Path(__file__).parent
    chart_file = script_dir.parent.parent / "scripts" / "example_charts.txt"

    with open(chart_file, "r") as f:
        original_text = f.read()

    print("=" * 80)
    print("FULL PROCESSING CHAIN TEST")
    print("=" * 80)

    print(f"\nOriginal Text Length: {len(original_text):,} characters")

    # Step 1: Clinical Relevance Filtering
    print("\n" + "=" * 80)
    print("STEP 1: CLINICAL RELEVANCE FILTERING (GPT-4o-mini)")
    print("=" * 80)

    filtering_result = await openai_service.filter_clinical_relevance(
        deidentified_text=original_text
    )

    clinical_text = filtering_result["filtered_text"]

    print(f"\nOriginal Length: {filtering_result['original_length']:,} chars")
    print(f"Filtered Length: {filtering_result['filtered_length']:,} chars")
    print(f"Reduction: {filtering_result['reduction_pct']}%")
    print(f"Encounter Type: {filtering_result.get('encounter_type', 'N/A')}")
    print(f"Cost: ${filtering_result['cost_usd']:.6f}")
    print(f"Processing Time: {filtering_result['processing_time_ms']} ms")

    print("\nFiltered Text (Billing-Relevant Only):")
    print("-" * 80)
    print(clinical_text)
    print("-" * 80)

    # Step 2: DetectEntitiesV2
    print("\n" + "=" * 80)
    print("STEP 2: DETECT ENTITIES V2")
    print("=" * 80)

    medical_entities = comprehend_medical_service.detect_entities_v2(clinical_text)

    # Group by category
    by_category = {}
    for entity in medical_entities:
        if entity.category not in by_category:
            by_category[entity.category] = []
        by_category[entity.category].append(entity)

    print(f"\nTotal Entities: {len(medical_entities)}")

    for category in sorted(by_category.keys()):
        print(f"\n{category} ({len(by_category[category])}):")
        for entity in by_category[category][:5]:  # Show first 5
            traits_str = ""
            if entity.traits:
                trait_names = [t.get('Name', '') for t in entity.traits]
                traits_str = f" [{', '.join(trait_names)}]"
            print(f"  - {entity.text}{traits_str} (score: {entity.score:.3f})")
        if len(by_category[category]) > 5:
            print(f"  ... and {len(by_category[category]) - 5} more")

    # Step 3: Extract Diagnosis/Symptom Entities
    print("\n" + "=" * 80)
    print("STEP 3: EXTRACT DIAGNOSIS/SYMPTOM ENTITIES")
    print("Criteria: MEDICAL_CONDITION with DIAGNOSIS or SYMPTOM (exclude NEGATION)")
    print("=" * 80)

    diagnosis_entities = get_diagnosis_entities(medical_entities)

    print(f"\nDiagnosis/Symptom Entities: {len(diagnosis_entities)}")
    for entity in diagnosis_entities:
        traits_str = ""
        if entity.traits:
            trait_names = [t.get('Name', '') for t in entity.traits]
            traits_str = f" [{', '.join(trait_names)}]"
        print(f"  ✓ {entity.text}{traits_str} (score: {entity.score:.3f})")

    # Step 4: InferICD10CM
    print("\n" + "=" * 80)
    print("STEP 4: INFER ICD-10-CM (All Codes)")
    print("=" * 80)

    icd10_entities = comprehend_medical_service.infer_icd10_cm(clinical_text)

    print(f"\nTotal ICD-10 Codes: {len(icd10_entities)}")
    for entity in icd10_entities:
        print(f"\n  - {entity.code}: {entity.description}")
        print(f"    Text: '{entity.text}' (score: {entity.score:.3f})")

    # Step 5: Filter ICD-10 Codes
    print("\n" + "=" * 80)
    print("STEP 5: FILTER ICD-10 CODES (Fuzzy Text Matching)")
    print("Match ICD-10 codes to diagnosis/symptom entities (threshold 0.6)")
    print("=" * 80)

    if icd10_entities and diagnosis_entities:
        filtered_icd10, icd10_stats = filter_icd10_codes(
            icd10_entities=icd10_entities,
            diagnosis_entities=diagnosis_entities,
            min_match_score=0.6
        )

        deduplicated_icd10 = deduplicate_icd10_codes(filtered_icd10)

        print(f"\nFilter Statistics:")
        print(f"  Total ICD-10 codes: {icd10_stats['total_icd10']}")
        print(f"  Diagnosis/symptom entities: {icd10_stats['diagnosis_entities']}")
        print(f"  Filtered ICD-10 codes: {icd10_stats['filtered_icd10']}")
        print(f"  Filtered out: {icd10_stats['filtered_out']}")

        print(f"\nFiltered ICD-10 Codes (Deduplicated): {len(deduplicated_icd10)}")
        for entity in deduplicated_icd10:
            print(f"  ✅ {entity.code}: {entity.description}")
            print(f"     Text: '{entity.text}' (score: {entity.score:.3f})")
    else:
        print("\n⚠️  No ICD-10 codes or diagnosis entities to filter")
        deduplicated_icd10 = []

    # Step 6: Extract Procedure Entities
    print("\n" + "=" * 80)
    print("STEP 6: EXTRACT PROCEDURE ENTITIES (DetectEntitiesV2)")
    print("Criteria: TEST_TREATMENT_PROCEDURE with score > 0.5")
    print("=" * 80)

    procedure_entities = get_procedure_entities(
        medical_entities,
        min_score=0.5
    )

    print(f"\nProcedure Entities: {len(procedure_entities)}")
    for entity in procedure_entities:
        print(f"  ✓ {entity.text} (score: {entity.score:.3f})")

    # Step 7: InferSNOMEDCT
    print("\n" + "=" * 80)
    print("STEP 7: INFER SNOMED CT (All Codes)")
    print("=" * 80)

    snomed_entities = comprehend_medical_service.infer_snomed_ct(clinical_text)

    print(f"\nTotal SNOMED Codes: {len(snomed_entities)}")
    for entity in snomed_entities[:10]:  # Show first 10
        print(f"\n  - Code: {entity.code}")
        print(f"    Description: {entity.description}")
        print(f"    Text: '{entity.text}'")
        print(f"    Category: {entity.category}")
        print(f"    Score: {entity.score:.3f}")
    if len(snomed_entities) > 10:
        print(f"\n  ... and {len(snomed_entities) - 10} more")

    # Step 8: Filter SNOMED Codes
    print("\n" + "=" * 80)
    print("STEP 8: FILTER SNOMED CODES (Fuzzy Text Matching)")
    print("Match SNOMED codes to procedure entities (threshold 0.5)")
    print("=" * 80)

    if snomed_entities and procedure_entities:
        filtered_snomed, snomed_stats = filter_snomed_codes(
            snomed_entities=snomed_entities,
            procedure_entities=procedure_entities,
            min_match_score=0.5
        )

        print(f"\nFilter Statistics:")
        print(f"  Total SNOMED codes: {snomed_stats['total_snomed']}")
        print(f"  Procedure entities: {snomed_stats['procedure_entities']}")
        print(f"  Filtered SNOMED codes: {snomed_stats['filtered_snomed']}")
        print(f"  Filtered out: {snomed_stats['filtered_out']}")

        if filtered_snomed:
            print(f"\nFiltered SNOMED Codes: {len(filtered_snomed)}")
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
    print("SUMMARY - DATA FOR LLM CODING")
    print("=" * 80)

    print(f"\n📄 Clinical Text:")
    print(f"   Original: {filtering_result['original_length']:,} chars")
    print(f"   Filtered: {filtering_result['filtered_length']:,} chars ({filtering_result['reduction_pct']}% reduction)")

    print(f"\n📊 Entities Extracted:")
    print(f"   Total medical entities: {len(medical_entities)}")
    print(f"   Diagnosis/symptom entities: {len(diagnosis_entities)}")
    print(f"   Procedure entities: {len(procedure_entities)}")

    print(f"\n📋 ICD-10 Codes (Diagnoses):")
    print(f"   Total extracted: {len(icd10_entities)}")
    print(f"   After filtering: {len(deduplicated_icd10)}")
    for entity in deduplicated_icd10:
        print(f"   - {entity.code}: {entity.description}")

    print(f"\n🔧 SNOMED Procedure Codes:")
    print(f"   Total extracted: {len(snomed_entities)}")
    print(f"   After filtering: {len(filtered_snomed)}")
    for entity in filtered_snomed:
        print(f"   - {entity.code}: {entity.description}")

    print("\n" + "=" * 80)
    print("EXPECTED BILLING CODES")
    print("=" * 80)

    print("\nFrom document:")
    print("  CPT: 99393 (Established Children ages 5-11 well child visit)")
    print("  ICD-10: Z00.129 (Well Child Visit Without Abnormal Findings)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
