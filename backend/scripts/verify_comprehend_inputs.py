"""
Verify what text is actually sent to AWS Comprehend Medical methods
"""
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.test_fhir_local import LocalFhirClient
from app.services.phi_handler import phi_handler
from app.services.comprehend_medical import comprehend_medical_service

# Use the COVID-19 encounter
BUNDLE_PATH = "/Users/alexander/code/revrx/synthetic_data/synthea_fhir4_100/Adam631_Gusikowski974_296e9f96-4897-f44b-39d3-1127e65f9e80.json"
ENCOUNTER_ID = "296e9f96-4897-f44b-e8b4-d9ef5f7d8f0a"


async def verify_comprehend_inputs():
    """Verify inputs to Comprehend Medical methods"""
    
    # Load FHIR data
    client = LocalFhirClient(BUNDLE_PATH)
    await client.load_bundle()
    
    # Get DocumentReference
    doc_refs = await client.search_resources(
        "DocumentReference",
        {"encounter": f"Encounter/{ENCOUNTER_ID}"}
    )
    
    if not doc_refs:
        print("ERROR: No DocumentReference found!")
        return
    
    # Extract clinical note
    import base64
    doc_ref = doc_refs[0]
    content = doc_ref.get("content", [{}])[0]
    attachment = content.get("attachment", {})
    clinical_text = base64.b64decode(attachment["data"]).decode("utf-8")
    
    print("=" * 80)
    print("STEP 1: ORIGINAL CLINICAL NOTE FROM DocumentReference")
    print("=" * 80)
    print(f"Length: {len(clinical_text)} characters")
    print(f"\nFirst 1000 characters:")
    print("-" * 80)
    print(clinical_text[:1000])
    print("-" * 80)
    print(f"\n... (remaining {len(clinical_text) - 1000} characters omitted)")
    
    # STEP 2: DetectPHI
    print("\n" + "=" * 80)
    print("STEP 2: INPUT TO DetectPHI")
    print("=" * 80)
    print(f"Text sent to DetectPHI: {len(clinical_text)} characters")
    print(f"\nFirst 500 characters of input:")
    print("-" * 80)
    print(clinical_text[:500])
    print("-" * 80)
    
    phi_result = phi_handler.detect_and_deidentify(clinical_text)
    
    print(f"\nOUTPUT FROM DetectPHI:")
    print(f"  PHI Entities Found: {len(phi_result.phi_entities)}")
    for i, entity in enumerate(phi_result.phi_entities, 1):
        print(f"    {i}. {entity.type}: '{entity.text}' (score: {entity.score:.3f})")
    
    print(f"\n  De-identified text length: {len(phi_result.deidentified_text)} characters")
    print(f"  First 500 characters of de-identified text:")
    print("-" * 80)
    print(phi_result.deidentified_text[:500])
    print("-" * 80)
    
    # STEP 3: Clinical Relevance Filtering
    # NOTE: In the actual pipeline, this uses OpenAI to filter for billing relevance
    # For this verification, we'll skip to show what would be sent to Comprehend
    
    # For demo purposes, let's use the de-identified text directly
    # (In real pipeline, this would be the filtered text from OpenAI)
    text_for_comprehend = phi_result.deidentified_text
    
    print("\n" + "=" * 80)
    print("STEP 3: INPUT TO InferICD10CM")
    print("=" * 80)
    print(f"Text length: {len(text_for_comprehend)} characters")
    print(f"\nFirst 500 characters:")
    print("-" * 80)
    print(text_for_comprehend[:500])
    print("-" * 80)
    
    # Call InferICD10CM
    icd10_entities = comprehend_medical_service.infer_icd10_cm(text_for_comprehend)
    
    print(f"\nOUTPUT FROM InferICD10CM:")
    print(f"  ICD-10 Codes Found: {len(icd10_entities)}")
    for i, entity in enumerate(icd10_entities[:10], 1):
        print(f"    {i}. {entity.code}: {entity.description[:60]} (score: {entity.score:.3f})")
    if len(icd10_entities) > 10:
        print(f"    ... and {len(icd10_entities) - 10} more")
    
    # STEP 4: InferSNOMEDCT
    print("\n" + "=" * 80)
    print("STEP 4: INPUT TO InferSNOMEDCT")
    print("=" * 80)
    print(f"Text length: {len(text_for_comprehend)} characters")
    print(f"(Same text as sent to InferICD10CM)")
    print(f"\nFirst 500 characters:")
    print("-" * 80)
    print(text_for_comprehend[:500])
    print("-" * 80)
    
    # Call InferSNOMEDCT
    snomed_entities = comprehend_medical_service.infer_snomed_ct(text_for_comprehend)
    
    print(f"\nOUTPUT FROM InferSNOMEDCT:")
    print(f"  SNOMED Codes Found: {len(snomed_entities)}")
    for i, entity in enumerate(snomed_entities[:10], 1):
        print(f"    {i}. {entity.code}: {entity.description[:60]} (score: {entity.score:.3f})")
    if len(snomed_entities) > 10:
        print(f"    ... and {len(snomed_entities) - 10} more")
    
    # SUMMARY
    print("\n" + "=" * 80)
    print("SUMMARY OF INPUTS TO COMPREHEND MEDICAL")
    print("=" * 80)
    print(f"1. DetectPHI Input:      {len(clinical_text)} characters (original DocumentReference)")
    print(f"2. InferICD10CM Input:   {len(text_for_comprehend)} characters (de-identified)")
    print(f"3. InferSNOMEDCT Input:  {len(text_for_comprehend)} characters (de-identified)")
    print(f"\nNote: In the full pipeline, the text is further filtered by GPT-4o-mini")
    print(f"      for billing relevance before being sent to ICD-10/SNOMED inference.")


if __name__ == "__main__":
    asyncio.run(verify_comprehend_inputs())
