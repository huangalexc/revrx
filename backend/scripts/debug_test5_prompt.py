"""
Debug script to show the exact prompt sent to OpenAI for Test 5
"""
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.test_fhir_local import LocalFhirClient
from app.services.prompt_templates import prompt_templates

# Test 5 details
ENCOUNTER_ID = "a965e34b-a96f-bf08-3f2d-2849fdc12eda"
BUNDLE_PATH = "/Users/alexander/code/revrx/synthetic_data/synthea_fhir4_100/Ahmed109_Bosco882_a965e34b-a96f-bf08-366d-3e4b4ec4c8c0.json"


async def show_test5_prompt():
    """Extract the exact prompt that would be sent to OpenAI for Test 5"""

    # From the batch test output, we know:
    clinical_text = """Chief Complaint: No complaints.

History of Present Illness: Ahmed109 is a 20 year-old nonhispanic white male. Patient has a history of medication review due (situation), unemployed (finding), full-time employment (finding), stress (finding).

Social History: Patient is married. Patient has never smoked. Patient identifies as heterosexual. Patient comes from a middle socioeconomic background.

Assessment and Plan: Patient screened for intimate partner abuse using HARK questionnaire. Patient also screened for depression and anxiety. Patient is a victim of intimate partner abuse and should be connected with local domestic violence resources. Patient's medication was reviewed and is current."""

    billed_codes = [
        {"code": "206905", "code_type": "RxNorm", "description": "Ibuprofen 400 MG Oral Tablet [Ibu]"},
        {"code": "162673000", "code_type": "SNOMED", "description": "General examination of patient (procedure)"},
        {"code": "140", "code_type": "CVX", "description": "Influenza, seasonal, injectable, preservative free"},
        {"code": "43", "code_type": "CVX", "description": "Hep B, adult"},
        {"code": "314529007", "code_type": "SNOMED", "description": "Medication review due (situation)"},
        {"code": "337388004", "code_type": "SNOMED", "description": "Blood glucose testing strips (physical object)"},
        {"code": "51990-0", "code_type": "LOINC", "description": "Basic metabolic panel - Blood"},
        {"code": "710824005", "code_type": "SNOMED", "description": "Assessment of health and social care needs (procedure)"},
        {"code": "706893006", "code_type": "SNOMED", "description": "Victim of intimate partner abuse (finding)"},
        {"code": "710841007", "code_type": "SNOMED", "description": "Assessment of anxiety (procedure)"},
        {"code": "69737-5", "code_type": "LOINC", "description": "Generalized anxiety disorder 7 item (GAD-7)"},
        {"code": "866148006", "code_type": "SNOMED", "description": "Screening for domestic abuse (procedure)"},
        {"code": "76499-3", "code_type": "LOINC", "description": "Humiliation, Afraid, Rape, and Kick questionnaire [HARK]"},
        {"code": "171207006", "code_type": "SNOMED", "description": "Depression screening (procedure)"},
        {"code": "55757-9", "code_type": "LOINC", "description": "Patient Health Questionnaire 2 item (PHQ-2) [Reported]"},
        {"code": "103697008", "code_type": "SNOMED", "description": "Patient referral for dental care (procedure)"},
    ]

    extracted_icd10_codes = [
        {"code": "Z91.414", "description": "Personal history of adult intimate partner abuse", "score": 0.99}
    ]

    snomed_to_cpt_suggestions = [
        {"cpt_code": "SNOMED 182836005", "cpt_description": "Review of medication (procedure)", "snomed_code": "182836005", "confidence": 0.30},
        {"cpt_code": "SNOMED 182836005", "cpt_description": "Review of medication (procedure)", "snomed_code": "182836005", "confidence": 0.21},
        {"cpt_code": "SNOMED 6142004", "cpt_description": "Influenza (disorder)", "snomed_code": "6142004", "confidence": 0.27},
        {"cpt_code": "SNOMED 740685003", "cpt_description": "Inject (administration method)", "snomed_code": "740685003", "confidence": 0.05},
        {"cpt_code": "SNOMED 27566006", "cpt_description": "Drug preservative (product)", "snomed_code": "27566006", "confidence": 0.05},
        {"cpt_code": "SNOMED 416608005", "cpt_description": "Drug therapy (procedure)", "snomed_code": "416608005", "confidence": 0.14},
    ]

    encounter_type = "General examination of patient (procedure)"

    # Generate prompts
    system_prompt = prompt_templates.get_system_prompt()
    user_prompt = prompt_templates.get_user_prompt(
        clinical_text,
        billed_codes,
        extracted_icd10_codes,
        snomed_to_cpt_suggestions,
        encounter_type
    )

    print("="*80)
    print("SYSTEM PROMPT")
    print("="*80)
    print(f"Length: {len(system_prompt)} characters")
    print(f"Tokens (estimate): ~{len(system_prompt) // 4}")
    print()
    print(system_prompt)
    print()

    print("="*80)
    print("USER PROMPT")
    print("="*80)
    print(f"Length: {len(user_prompt)} characters")
    print(f"Tokens (estimate): ~{len(user_prompt) // 4}")
    print()
    print(user_prompt)
    print()

    print("="*80)
    print("TOTAL PROMPT STATS")
    print("="*80)
    total_chars = len(system_prompt) + len(user_prompt)
    total_tokens_est = total_chars // 4
    print(f"Total characters: {total_chars:,}")
    print(f"Estimated tokens: ~{total_tokens_est:,}")
    print(f"OpenAI max context: 128,000 tokens")
    print(f"Max completion tokens: 2,000 (configured)")
    print()

    if total_tokens_est > 10000:
        print("⚠️  WARNING: Prompt is very large (>10K tokens)")
        print("    This may cause:")
        print("    - Longer response times")
        print("    - Higher cost")
        print("    - Potential timeouts")
        print("    - JSON parsing issues due to truncated responses")


if __name__ == "__main__":
    asyncio.run(show_test5_prompt())
