#!/usr/bin/env python3
"""
Test Final Coding Suggestion Prompt

Tests the complete pipeline with revised prompt including:
- Filtered clinical text (reduced by ~85%)
- Extracted ICD-10 codes
- SNOMED to CPT crosswalk suggestions
- Encounter type
- E/M level determination
"""

import asyncio
import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.openai_service import openai_service
from app.services.comprehend_medical import comprehend_medical_service
from app.services.phi_handler import phi_handler
from app.utils.icd10_filtering import (
    get_diagnosis_entities,
    filter_icd10_codes,
    deduplicate_icd10_codes,
    get_procedure_entities,
    filter_snomed_codes
)


async def main():
    """Test final coding prompt with all inputs"""

    # Read example chart
    script_dir = Path(__file__).parent
    chart_file = script_dir.parent.parent / "scripts" / "example_charts.txt"

    with open(chart_file, "r") as f:
        clinical_text = f.read()

    print("=" * 80)
    print("FINAL CODING SUGGESTION PROMPT TEST")
    print("=" * 80)

    # Step 1: Deidentify
    print("\n" + "=" * 80)
    print("STEP 1: PHI DETECTION & DEIDENTIFICATION")
    print("=" * 80)

    deid_result = phi_handler.detect_and_deidentify(clinical_text)
    print(f"PHI entities detected: {len(deid_result.phi_entities)}")
    print(f"Deidentified text length: {len(deid_result.deidentified_text):,} chars")

    # Step 2: Clinical relevance filtering
    print("\n" + "=" * 80)
    print("STEP 2: CLINICAL RELEVANCE FILTERING (GPT-4o-mini)")
    print("=" * 80)

    filtering_result = await openai_service.filter_clinical_relevance(
        deidentified_text=deid_result.deidentified_text
    )

    clinical_text_for_coding = filtering_result["filtered_text"]
    encounter_type = filtering_result.get("encounter_type")

    print(f"Original: {filtering_result['original_length']:,} chars")
    print(f"Filtered: {filtering_result['filtered_length']:,} chars ({filtering_result['reduction_pct']}% reduction)")
    print(f"Encounter Type: {encounter_type}")

    # Step 3: Extract medical entities
    print("\n" + "=" * 80)
    print("STEP 3: EXTRACT MEDICAL ENTITIES (DetectEntitiesV2)")
    print("=" * 80)

    medical_entities = comprehend_medical_service.detect_entities_v2(clinical_text_for_coding)
    print(f"Total entities: {len(medical_entities)}")

    # Step 4: Extract and filter ICD-10 codes
    print("\n" + "=" * 80)
    print("STEP 4: EXTRACT & FILTER ICD-10 CODES")
    print("=" * 80)

    icd10_entities = comprehend_medical_service.infer_icd10_cm(clinical_text_for_coding)
    print(f"Total ICD-10 codes: {len(icd10_entities)}")

    diagnosis_entities = get_diagnosis_entities(medical_entities)
    print(f"Diagnosis/symptom entities: {len(diagnosis_entities)}")

    if icd10_entities and diagnosis_entities:
        filtered_icd10, _ = filter_icd10_codes(
            icd10_entities=icd10_entities,
            diagnosis_entities=diagnosis_entities,
            min_match_score=0.6
        )
        deduplicated_icd10 = deduplicate_icd10_codes(filtered_icd10)
    else:
        deduplicated_icd10 = []

    print(f"Filtered ICD-10 codes: {len(deduplicated_icd10)}")
    for entity in deduplicated_icd10:
        print(f"  - {entity.code}: {entity.description} (score: {entity.score:.2f})")

    # Step 5: Extract and filter SNOMED codes
    print("\n" + "=" * 80)
    print("STEP 5: EXTRACT & FILTER SNOMED CODES")
    print("=" * 80)

    snomed_entities = comprehend_medical_service.infer_snomed_ct(clinical_text_for_coding)
    print(f"Total SNOMED codes: {len(snomed_entities)}")

    procedure_entities = get_procedure_entities(medical_entities, min_score=0.5)
    print(f"Procedure entities: {len(procedure_entities)}")

    if snomed_entities and procedure_entities:
        filtered_snomed, _ = filter_snomed_codes(
            snomed_entities=snomed_entities,
            procedure_entities=procedure_entities,
            min_match_score=0.5
        )
    else:
        filtered_snomed = []

    print(f"Filtered SNOMED codes: {len(filtered_snomed)}")

    # Mock SNOMED to CPT crosswalk (in real system, would query database)
    snomed_to_cpt = []
    for snomed in filtered_snomed[:5]:  # Take first 5
        # Mock CPT mapping
        cpt_code = "99393" if "well child" in snomed.description.lower() else "99XXX"
        snomed_to_cpt.append({
            "snomed_code": snomed.code,
            "snomed_description": snomed.description,
            "cpt_code": cpt_code,
            "cpt_description": f"CPT {cpt_code}: Mapped from SNOMED",
            "confidence": 0.85
        })

    print(f"SNOMED to CPT suggestions: {len(snomed_to_cpt)}")
    for mapping in snomed_to_cpt:
        print(f"  - CPT {mapping['cpt_code']}: {mapping['cpt_description']} (confidence: {mapping['confidence']:.2f})")

    # Step 6: Call final coding suggestion LLM
    print("\n" + "=" * 80)
    print("STEP 6: FINAL CODING SUGGESTIONS (GPT-4)")
    print("=" * 80)

    # Prepare inputs
    extracted_icd10_for_llm = [
        {
            "code": e.code,
            "description": e.description,
            "score": e.score
        }
        for e in deduplicated_icd10
    ]

    billed_codes = []  # No billed codes in this example

    print("\nCalling GPT-4 with:")
    print(f"  - Encounter Type: {encounter_type}")
    print(f"  - Clinical Text: {len(clinical_text_for_coding):,} chars")
    print(f"  - ICD-10 Codes: {len(extracted_icd10_for_llm)}")
    print(f"  - SNOMED→CPT Suggestions: {len(snomed_to_cpt)}")

    coding_result = await openai_service.analyze_clinical_note(
        clinical_note=clinical_text_for_coding,
        billed_codes=billed_codes,
        extracted_icd10_codes=extracted_icd10_for_llm,
        snomed_to_cpt_suggestions=snomed_to_cpt,
        encounter_type=encounter_type
    )

    # Display results
    print("\n" + "=" * 80)
    print("CODING SUGGESTIONS RESULT")
    print("=" * 80)

    print(f"\n📋 BILLED CODES (extracted from note): {len(coding_result.billed_codes)}")
    for code in coding_result.billed_codes:
        print(f"  - {code.code} ({code.code_type}): {code.description}")

    print(f"\n💡 SUGGESTED CODES: {len(coding_result.suggested_codes)}")
    for code in coding_result.suggested_codes:
        print(f"\n  - {code.code} ({code.code_type}): {code.description}")
        print(f"    Justification: {code.justification}")
        print(f"    Confidence: {code.confidence:.2f} - {code.confidence_reason}")

    print(f"\n➕ ADDITIONAL CODES: {len(coding_result.additional_codes)}")
    for code in coding_result.additional_codes:
        print(f"\n  - {code.code} ({code.code_type}): {code.description}")
        print(f"    Justification: {code.justification}")
        print(f"    Confidence: {code.confidence:.2f}")

    # Validation
    print("\n" + "=" * 80)
    print("VALIDATION - EXPECTED CODES")
    print("=" * 80)

    print("\nFrom document:")
    print("  CPT: 99393 (Established Children ages 5-11 well child visit)")
    print("  ICD-10: Z00.129 (Well Child Visit Without Abnormal Findings)")

    print("\nKey Questions:")
    print("  ✓ Did it identify the encounter as a well child visit?")
    print(f"    → {encounter_type}")
    print("  ✓ Did it determine the correct E/M level or preventive code?")

    # Check if 99393 is in any of the codes
    all_codes = (
        [c.code for c in coding_result.billed_codes] +
        [c.code for c in coding_result.suggested_codes] +
        [c.code for c in coding_result.additional_codes]
    )
    if "99393" in all_codes:
        print(f"    → YES! Found 99393 ✅")
    else:
        print(f"    → Suggested codes: {all_codes[:5]}")

    print("  ✓ Did it use the extracted ICD-10 code Z00.129?")
    if "Z00.129" in [c.code for c in coding_result.billed_codes]:
        print(f"    → YES! Found in billed codes ✅")
    elif "Z00.129" in all_codes:
        print(f"    → YES! Found in suggested codes ✅")
    else:
        print(f"    → Provided as input: {extracted_icd10_for_llm}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
