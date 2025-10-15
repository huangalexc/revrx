"""
Test Complete FHIR Coding Pipeline with Documentation
Runs the full coding suggestion workflow and documents inputs/outputs for each step
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import prisma
from app.services.phi_handler import phi_handler
from app.services.openai_service import openai_service
from app.services.comprehend_medical import comprehend_medical_service
from app.services.snomed_crosswalk import get_crosswalk_service
import structlog

# Import LocalFhirClient from test script
from test_fhir_local import LocalFhirClient, generate_synthetic_note

logger = structlog.get_logger(__name__)


def print_section(title: str, content: Any = None):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)
    if content:
        print(content)


def print_subsection(title: str):
    """Print a formatted subsection header"""
    print(f"\n--- {title} ---")


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text for display"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + f"... [truncated, total length: {len(text)}]"


async def run_full_coding_pipeline(encounter_id: str, bundle_path: str):
    """
    Run the complete coding suggestion pipeline with detailed documentation
    """
    print_section("FHIR CODING INTELLIGENCE PIPELINE TEST")
    print(f"Encounter ID: {encounter_id}")
    print(f"Bundle Path: {bundle_path}")

    # ===========================================================================
    # STEP 1: LOAD AND EXTRACT FHIR DATA
    # ===========================================================================
    print_section("STEP 1: FHIR DATA EXTRACTION")

    async with LocalFhirClient(bundle_path) as client:
        from app.services.fhir.encounter_service import FhirEncounterService
        from app.services.fhir.note_service import FhirNoteService

        encounter_service = FhirEncounterService(client)
        note_service = FhirNoteService(client)

        # Extract encounter metadata
        print_subsection("1.1 Fetching Encounter Metadata")
        encounter = await encounter_service.fetch_encounter_by_id(encounter_id)
        metadata = encounter_service.extract_encounter_metadata(encounter)

        print(f"INPUT: Encounter ID = {encounter_id}")
        print(f"\nOUTPUT:")
        print(f"  Patient ID: {metadata['fhir_patient_id']}")
        print(f"  Provider ID: {metadata['fhir_provider_id']}")
        print(f"  Date of Service: {metadata['date_of_service']}")
        print(f"  Encounter Type: {metadata['encounter_type']}")
        print(f"  Encounter Class: {metadata['encounter_class']}")

        # Fetch conditions
        print_subsection("1.2 Fetching Conditions")
        conditions = await client.search_resources(
            "Condition",
            {"encounter": f"Encounter/{encounter_id}"},
        )
        print(f"INPUT: Search Condition resources where encounter = {encounter_id}")
        print(f"OUTPUT: Found {len(conditions)} condition(s)")
        for i, condition in enumerate(conditions, 1):
            code = condition.get("code", {}).get("coding", [{}])[0]
            print(f"  {i}. SNOMED: {code.get('code')} - {code.get('display')}")

        # Fetch procedures
        print_subsection("1.3 Fetching Procedures")
        procedures = await client.search_resources(
            "Procedure",
            {"encounter": f"Encounter/{encounter_id}"},
        )
        print(f"INPUT: Search Procedure resources where encounter = {encounter_id}")
        print(f"OUTPUT: Found {len(procedures)} procedure(s)")
        for i, procedure in enumerate(procedures, 1):
            code = procedure.get("code", {}).get("coding", [{}])[0]
            print(f"  {i}. SNOMED: {code.get('code')} - {code.get('display')}")

        # Fetch actual clinical note from DocumentReference
        print_subsection("1.4 Fetching Clinical Note from DocumentReference")
        doc_refs = await client.search_resources(
            "DocumentReference",
            {"encounter": f"Encounter/{encounter_id}"}
        )

        clinical_text = None
        encounter_type = metadata.get("encounter_type", "Unknown")

        if doc_refs:
            print(f"INPUT: Search DocumentReference for encounter {encounter_id}")
            print(f"OUTPUT: Found {len(doc_refs)} DocumentReference(s)")

            # Use the first DocumentReference
            doc_ref = doc_refs[0]
            content = doc_ref.get("content", [{}])[0]
            attachment = content.get("attachment", {})

            if "data" in attachment:
                # Decode base64 clinical note
                import base64
                clinical_text = base64.b64decode(attachment["data"]).decode("utf-8")
                print(f"  Successfully extracted clinical note ({len(clinical_text)} characters)")
            else:
                print(f"  No embedded data in DocumentReference")

        # Fallback to synthetic note if no DocumentReference found
        if not clinical_text:
            print(f"\n  No DocumentReference found - generating synthetic note from structured data")
            print_subsection("1.4b Generating Synthetic Clinical Note (Fallback)")
            clinical_data = {"conditions": conditions, "procedures": procedures}
            clinical_text = generate_synthetic_note(metadata, clinical_data)
            print(f"INPUT: Metadata + Conditions + Procedures")
            print(f"OUTPUT: Synthetic clinical note ({len(clinical_text)} characters)")

        print(f"\nClinical Note Preview:\n{'-' * 60}")
        print(truncate_text(clinical_text, 800))
        print('-' * 60)

    # ===========================================================================
    # STEP 2: PHI DETECTION AND DE-IDENTIFICATION
    # ===========================================================================
    print_section("STEP 2: PHI DETECTION AND DE-IDENTIFICATION")
    print_subsection("2.1 Amazon Comprehend Medical - DetectPHI")

    print(f"INPUT:")
    print(f"  Text Length: {len(clinical_text)} characters")
    print(f"  Text Preview: {truncate_text(clinical_text, 200)}")

    phi_result = phi_handler.detect_and_deidentify(clinical_text)

    print(f"\nOUTPUT:")
    print(f"  PHI Detected: {phi_result.phi_detected}")
    print(f"  PHI Entity Count: {len(phi_result.phi_entities)}")
    print(f"  De-identified Text Length: {len(phi_result.deidentified_text)} characters")

    if phi_result.phi_entities:
        print(f"\n  PHI Entities Found:")
        for i, entity in enumerate(phi_result.phi_entities[:10], 1):
            print(f"    {i}. Type: {entity.type:12s} | Text: '{entity.text}' | Score: {entity.score:.3f}")

    print(f"\n  De-identified Text Preview:")
    print(f"  {truncate_text(phi_result.deidentified_text, 300)}")

    deidentified_text = phi_result.deidentified_text

    # ===========================================================================
    # STEP 3: CLINICAL RELEVANCE FILTERING (LLM)
    # ===========================================================================
    print_section("STEP 3: CLINICAL RELEVANCE FILTERING (LLM)")
    print_subsection("3.1 GPT-4o-mini - Filter Clinical Relevance")

    print(f"INPUT:")
    print(f"  Model: gpt-4o-mini")
    print(f"  Temperature: 0.3")
    print(f"  De-identified Text Length: {len(deidentified_text)} characters")
    print(f"  Text Preview: {truncate_text(deidentified_text, 200)}")

    filtering_result = await openai_service.filter_clinical_relevance(
        deidentified_text=deidentified_text
    )

    print(f"\nOUTPUT:")
    print(f"  Original Length: {filtering_result['original_length']} characters")
    print(f"  Filtered Length: {filtering_result['filtered_length']} characters")
    print(f"  Reduction: {filtering_result['reduction_pct']:.1f}%")
    print(f"  Tokens Used: {filtering_result['tokens_used']}")
    print(f"  Cost: ${filtering_result['cost_usd']:.4f}")
    print(f"  Provider Placeholder: {filtering_result.get('provider_placeholder')}")
    print(f"  Service Date Placeholder: {filtering_result.get('service_date_placeholder')}")

    print(f"\n  Filtered Text:")
    print(f"  {truncate_text(filtering_result['filtered_text'], 400)}")

    clinical_text_for_coding = filtering_result["filtered_text"]

    # ===========================================================================
    # STEP 4: ICD-10 CODE INFERENCE
    # ===========================================================================
    print_section("STEP 4: ICD-10 CODE INFERENCE")
    print_subsection("4.1 Amazon Comprehend Medical - InferICD10CM")

    print(f"INPUT:")
    print(f"  Text Length: {len(clinical_text_for_coding)} characters")
    print(f"  Text Preview: {truncate_text(clinical_text_for_coding, 200)}")

    icd10_entities = comprehend_medical_service.infer_icd10_cm(clinical_text_for_coding)

    print(f"\nOUTPUT:")
    print(f"  Total ICD-10 Codes Found: {len(icd10_entities)}")

    if icd10_entities:
        print(f"\n  ICD-10 Codes (Top 10):")
        for i, entity in enumerate(icd10_entities[:10], 1):
            print(f"    {i}. {entity.code:8s} | {entity.description:50s} | Score: {entity.score:.3f} | Type: {entity.type}")

    # Filter ICD-10 codes (remove duplicates, skip diagnosis matching for now)
    from app.utils.icd10_filtering import deduplicate_icd10_codes

    print_subsection("4.2 Filtering ICD-10 Codes")
    print(f"INPUT: {len(icd10_entities)} raw ICD-10 codes")

    # Filter by confidence score
    filtered_icd10 = [e for e in icd10_entities if e.score >= 0.3]
    deduped_icd10 = deduplicate_icd10_codes(filtered_icd10)

    print(f"OUTPUT:")
    print(f"  After filtering (score >= 0.3): {len(filtered_icd10)} codes")
    print(f"  After deduplication: {len(deduped_icd10)} codes")

    if deduped_icd10:
        print(f"\n  Filtered ICD-10 Codes:")
        for i, entity in enumerate(deduped_icd10[:10], 1):
            print(f"    {i}. {entity.code:8s} | {entity.description:50s} | Score: {entity.score:.3f}")

    # ===========================================================================
    # STEP 5: SNOMED CODE INFERENCE
    # ===========================================================================
    print_section("STEP 5: SNOMED CODE INFERENCE")
    print_subsection("5.1 Amazon Comprehend Medical - InferSNOMEDCT")

    print(f"INPUT:")
    print(f"  Text Length: {len(clinical_text_for_coding)} characters")
    print(f"  Text Preview: {truncate_text(clinical_text_for_coding, 200)}")

    snomed_entities = comprehend_medical_service.infer_snomed_ct(clinical_text_for_coding)

    print(f"\nOUTPUT:")
    print(f"  Total SNOMED Codes Found: {len(snomed_entities)}")

    if snomed_entities:
        print(f"\n  SNOMED Codes (Top 15):")
        for i, entity in enumerate(snomed_entities[:15], 1):
            print(f"    {i}. {entity.code:12s} | {entity.description:50s} | Score: {entity.score:.3f} | Category: {entity.category}")

    # Filter for procedures
    procedure_snomed = [
        e for e in snomed_entities
        if e.category in ("TEST_TREATMENT_PROCEDURE", "MEDICAL_CONDITION")
        and e.score >= 0.05
    ]

    print(f"\n  Filtered for Procedures/Conditions:")
    print(f"  {len(procedure_snomed)} SNOMED codes (score >= 0.05, relevant categories)")

    # ===========================================================================
    # STEP 6: EXTRACT BILLED CODES FROM FHIR CLAIMS
    # ===========================================================================
    print_section("STEP 6: EXTRACT BILLED CODES FROM FHIR CLAIMS")
    print_subsection("6.1 Fetch Claims for Encounter")

    # Search for Claims related to this encounter
    claims = await client.search_resources("Claim", {
        "encounter": f"Encounter/{encounter_id}"
    })

    print(f"INPUT: Search Claim resources for encounter {encounter_id}")
    print(f"OUTPUT: Found {len(claims)} claim(s)")

    billed_codes = []
    total_billed_amount = 0.0
    claim_level_totals = []

    for claim in claims:
        # Get claim-level total (more accurate than summing items)
        claim_total = claim.get("total", {})
        claim_amount = claim_total.get("value", 0.0)
        claim_currency = claim_total.get("currency", "USD")

        if claim_amount > 0:
            claim_level_totals.append({
                "amount": claim_amount,
                "currency": claim_currency,
                "claim_id": claim.get("id")
            })
            total_billed_amount += claim_amount

        # Extract individual line items for code analysis
        claim_items = claim.get("item", [])
        for item in claim_items:
            # Extract procedure code from productOrService
            product_or_service = item.get("productOrService", {})
            codings = product_or_service.get("coding", [])

            for coding in codings:
                code = coding.get("code")
                display = coding.get("display", "Unknown")
                system = coding.get("system", "")

                # Extract line item amount (for reference only)
                net_amount = item.get("net", {})
                amount_value = net_amount.get("value", 0.0)
                currency = net_amount.get("currency", "USD")

                if code:
                    billed_codes.append({
                        "code": code,
                        "description": display,
                        "system": system,
                        "amount": amount_value,
                        "currency": currency
                    })

    # Deduplicate billed codes (keep first occurrence with highest amount)
    seen_codes = {}
    for bc in billed_codes:
        code = bc["code"]
        if code not in seen_codes or bc["amount"] > seen_codes[code]["amount"]:
            seen_codes[code] = bc

    billed_codes_deduped = list(seen_codes.values())

    print(f"\n  Billed Codes Extracted:")
    print(f"    Raw: {len(billed_codes)} codes")
    print(f"    After deduplication: {len(billed_codes_deduped)} unique codes")

    if billed_codes_deduped:
        for i, billed in enumerate(billed_codes_deduped[:20], 1):  # Show first 20
            print(f"    {i}. {billed['code']}: {billed['description'][:60]}")
            if billed['amount'] > 0:
                print(f"       Line Item: ${billed['amount']:.2f} {billed['currency']}")
        if len(billed_codes_deduped) > 20:
            print(f"    ... and {len(billed_codes_deduped) - 20} more codes")
    else:
        print(f"    (No billed codes found in claims)")

    print(f"\n  Claim-Level Totals:")
    for i, claim_total in enumerate(claim_level_totals, 1):
        print(f"    Claim {i} ({claim_total['claim_id'][:20]}...): ${claim_total['amount']:.2f} {claim_total['currency']}")

    print(f"\n  Total Billed Amount (from claim totals): ${total_billed_amount:.2f}")

    # ===========================================================================
    # STEP 7: LLM CODING SUGGESTIONS
    # ===========================================================================
    print_section("STEP 7: LLM CODING SUGGESTIONS")
    print_subsection("7.1 GPT-4o-mini - Generate Coding Suggestions")

    # Prepare billed codes in the format expected by OpenAI service (USE DEDUPLICATED LIST)
    billed_codes_for_llm = [
        {
            "code": bc["code"],
            "code_type": "CPT" if "CPT" in bc.get("system", "") or bc["code"].startswith("D") else "ICD-10",
            "description": bc["description"],
        }
        for bc in billed_codes_deduped  # Use deduplicated list
    ]

    # Filter out already-billed codes from ICD-10 and SNOMED suggestions
    billed_code_set = {bc["code"] for bc in billed_codes_deduped}

    # Filter ICD-10 codes to only unbilled ones
    unbilled_icd10 = [
        {"code": e.code, "description": e.description, "score": e.score}
        for e in deduped_icd10
        if e.code not in billed_code_set
    ]

    # Filter SNOMED procedure codes to only unbilled ones
    unbilled_snomed = [
        {"code": e.code, "description": e.description, "score": e.score, "category": e.category}
        for e in procedure_snomed
        if e.code not in billed_code_set
    ]

    print(f"INPUT:")
    print(f"  Model: gpt-4o-mini")
    print(f"  Clinical Text Length: {len(clinical_text_for_coding)} characters")
    print(f"  Billed Codes (deduplicated): {len(billed_codes_for_llm)} codes")
    print(f"  Unbilled ICD-10 Codes: {len(unbilled_icd10)} codes (filtered from {len(deduped_icd10)} total)")
    print(f"  Unbilled SNOMED Codes: {len(unbilled_snomed)} codes (filtered from {len(procedure_snomed)} total)")

    if billed_codes_for_llm:
        print(f"\n  Billed Codes from Claims (first 10):")
        for i, code in enumerate(billed_codes_for_llm[:10], 1):
            print(f"    {i}. {code['code']}: {code['description'][:60]}")
        if len(billed_codes_for_llm) > 10:
            print(f"    ... and {len(billed_codes_for_llm) - 10} more")

    if unbilled_icd10:
        print(f"\n  Unbilled ICD-10 Codes to Consider:")
        for i, code in enumerate(unbilled_icd10, 1):
            print(f"    {i}. {code['code']}: {code['description']}")

    if unbilled_snomed:
        print(f"\n  Unbilled SNOMED Procedure Codes to Consider:")
        for i, code in enumerate(unbilled_snomed[:10], 1):
            print(f"    {i}. SNOMED {code['code']}: {code['description'][:60]} (score: {code['score']:.2f})")
        if len(unbilled_snomed) > 10:
            print(f"    ... and {len(unbilled_snomed) - 10} more")
        print(f"\n  Note: These unbilled SNOMED codes are documented in clinical text")
        print(f"        and may represent additional billable procedures.")

    # Use analyze_clinical_note (2-prompt approach) for better reliability
    # This approach splits the analysis into:
    # - Prompt 1: Code identification and suggestions
    # - Prompt 2: Quality and compliance analysis
    # Note: snomed_to_cpt_suggestions requires crosswalk data, so we pass empty list
    # The LLM will still see unbilled procedures in the clinical text
    analysis_result = await openai_service.analyze_clinical_note(
        clinical_note=clinical_text_for_coding,
        billed_codes=billed_codes_for_llm,
        extracted_icd10_codes=unbilled_icd10,  # Only send unbilled ICD-10 codes
        snomed_to_cpt_suggestions=[],  # No crosswalk data available
        encounter_type=encounter_type,
    )

    print(f"\nOUTPUT:")
    print(f"  Analysis Complete")
    print(f"  Suggested Codes: {len(analysis_result.suggested_codes)}")
    print(f"  Additional Codes: {len(analysis_result.additional_codes)}")
    print(f"  Denial Risks: {len(analysis_result.denial_risks)}")
    print(f"  Missing Documentation: {len(analysis_result.missing_documentation)}")
    print(f"  Modifier Suggestions: {len(analysis_result.modifier_suggestions)}")
    print(f"  Uncaptured Services: {len(analysis_result.uncaptured_services)}")
    print(f"  Tokens Used: {analysis_result.tokens_used}")
    print(f"  Cost: ${analysis_result.cost_usd:.4f}")
    print(f"  Incremental RVUs: {analysis_result.rvu_analysis.get('incremental_rvus', 0):.2f}")

    if analysis_result.suggested_codes:
        print(f"\n  Suggested Codes:")
        for i, code in enumerate(analysis_result.suggested_codes, 1):
            print(f"    {i}. {code.code_type}: {code.code} - {code.description[:60]}")
            print(f"       Confidence: {code.confidence:.2f}")
            print(f"       Justification: {truncate_text(code.justification, 150)}")
            if code.incremental_revenue:
                print(f"       Incremental Revenue: ${code.incremental_revenue:.2f}")

    if analysis_result.denial_risks:
        print(f"\n  Denial Risks Identified:")
        for i, risk in enumerate(analysis_result.denial_risks[:3], 1):
            print(f"    {i}. {risk.get('code')}: {risk.get('risk')} (Severity: {risk.get('severity')})")

    if analysis_result.uncaptured_services:
        print(f"\n  Uncaptured Services:")
        for i, service in enumerate(analysis_result.uncaptured_services[:3], 1):
            print(f"    {i}. {service.get('service')}: {truncate_text(service.get('description', ''), 100)}")

    # ===========================================================================
    # REVENUE ANALYSIS
    # ===========================================================================
    print_section("STEP 8: REVENUE ANALYSIS")
    print_subsection("8.1 Compare Billed vs Suggested Codes")

    # Calculate potential additional revenue from suggestions
    suggested_cpt_codes = [s for s in analysis_result.suggested_codes if s.code_type == "CPT"]
    billed_cpt_codes_set = {bc["code"] for bc in billed_codes if bc["code"].startswith("D")}
    suggested_codes_set = {s.code for s in suggested_cpt_codes}

    # Find new codes (suggested but not billed)
    new_codes = suggested_codes_set - billed_cpt_codes_set
    # Find matching codes (suggested and billed)
    matching_codes = suggested_codes_set & billed_cpt_codes_set

    print(f"\nActual Billed Codes: {len(billed_cpt_codes_set)} CPT codes")
    for code in billed_cpt_codes_set:
        billed_info = next((b for b in billed_codes if b["code"] == code), None)
        if billed_info:
            print(f"  • {code}: {billed_info['description'][:50]} (${billed_info['amount']:.2f})")

    print(f"\nAI Suggested Codes: {len(suggested_cpt_codes)} CPT codes")
    for suggestion in suggested_cpt_codes:
        status = "✓ Already Billed" if suggestion.code in matching_codes else "★ NEW OPPORTUNITY"
        revenue = f"${suggestion.incremental_revenue:.2f}" if suggestion.incremental_revenue else "N/A"
        print(f"  • {suggestion.code}: {suggestion.description[:50]}")
        print(f"    Status: {status} | Confidence: {suggestion.confidence:.2f} | Revenue: {revenue}")

    print(f"\nRevenue Opportunity Summary:")
    print(f"  • Codes Already Billed: {len(matching_codes)}")
    print(f"  • New Code Opportunities: {len(new_codes)}")
    print(f"  • Total Billed Amount: ${total_billed_amount:.2f}")

    # Calculate potential additional revenue
    potential_additional_revenue = sum(
        s.incremental_revenue for s in suggested_cpt_codes
        if s.code in new_codes and s.incremental_revenue
    )
    print(f"  • Potential Additional Revenue: ${potential_additional_revenue:.2f}")
    print(f"  • Total Potential Revenue: ${total_billed_amount + potential_additional_revenue:.2f}")

    if total_billed_amount > 0:
        revenue_increase_pct = (potential_additional_revenue / total_billed_amount) * 100
        print(f"  • Revenue Increase: {revenue_increase_pct:.1f}%")

    # ===========================================================================
    # SUMMARY
    # ===========================================================================
    print_section("PIPELINE SUMMARY")

    print(f"Input:")
    print(f"  • Encounter ID: {encounter_id}")
    print(f"  • Patient: {metadata['fhir_patient_id']}")
    print(f"  • Date of Service: {metadata['date_of_service']}")
    print(f"  • Original Text: {len(clinical_text)} characters")

    print(f"\nProcessing:")
    print(f"  • PHI Entities Detected: {len(phi_result.phi_entities)}")
    print(f"  • Text Reduction (filtering): {filtering_result['reduction_pct']:.1f}%")
    print(f"  • ICD-10 Codes Found: {len(deduped_icd10)}")
    print(f"  • SNOMED Codes Found: {len(snomed_entities)}")
    print(f"  • Billed Codes from Claims: {len(billed_codes)}")

    print(f"\nOutput:")
    print(f"  • Coding Suggestions: {len(analysis_result.suggested_codes)}")
    print(f"  • Additional Codes: {len(analysis_result.additional_codes)}")
    print(f"  • Denial Risks: {len(analysis_result.denial_risks)}")
    print(f"  • Total Cost: ${filtering_result['cost_usd'] + analysis_result.cost_usd:.4f}")

    print(f"\nRevenue Impact:")
    print(f"  • Billed Amount: ${total_billed_amount:.2f}")
    print(f"  • Potential Additional: ${potential_additional_revenue:.2f}")
    print(f"  • Total Potential: ${total_billed_amount + potential_additional_revenue:.2f}")

    print_section("PIPELINE TEST COMPLETE")


async def main():
    """Main test runner"""
    # Configuration
    BUNDLE_PATH = "/Users/alexander/code/revrx/synthetic_data/synthea_fhir4_100/Adam631_Gusikowski974_296e9f96-4897-f44b-39d3-1127e65f9e80.json"
    ENCOUNTER_ID = "296e9f96-4897-f44b-908d-5661e2eef92b"  # Hospital admission for isolation (COVID-19)

    try:
        # Connect to database
        await prisma.connect()

        # Run full pipeline
        await run_full_coding_pipeline(ENCOUNTER_ID, BUNDLE_PATH)

    except Exception as e:
        logger.error("Pipeline test failed", error=str(e), exc_info=True)
        raise
    finally:
        # Cleanup
        await prisma.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
