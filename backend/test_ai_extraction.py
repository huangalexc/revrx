"""
Test AI Code Extraction
Run this script to test the OpenAI service with sample clinical notes
"""

import asyncio
import json
import sys
from test_clinical_notes import TEST_NOTES
from app.services.openai_service import openai_service


async def test_extraction(note_name: str):
    """Test AI extraction on a specific clinical note"""

    if note_name not in TEST_NOTES:
        print(f"Error: Note '{note_name}' not found")
        print(f"Available notes: {', '.join(TEST_NOTES.keys())}")
        return

    clinical_note = TEST_NOTES[note_name]

    print("=" * 80)
    print(f"TESTING: {note_name}")
    print("=" * 80)
    print(f"\nClinical Note Preview (first 500 chars):")
    print(clinical_note[:500])
    print("...\n")

    print("Analyzing with OpenAI...")
    print("-" * 80)

    try:
        result = await openai_service.analyze_clinical_note(
            clinical_note=clinical_note,
            billed_codes=[]  # No pre-existing billed codes
        )

        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)

        # Billed Codes (extracted from note)
        print(f"\n📋 BILLED CODES EXTRACTED FROM NOTE: {len(result.billed_codes)}")
        print("-" * 80)
        if result.billed_codes:
            for code in result.billed_codes:
                print(f"\n✓ {code.code} ({code.code_type})")
                print(f"  Description: {code.description}")
        else:
            print("  (None found)")

        # Suggested Codes
        print(f"\n\n💡 SUGGESTED CODES: {len(result.suggested_codes)}")
        print("-" * 80)
        for i, code in enumerate(result.suggested_codes, 1):
            print(f"\n{i}. {code.code} ({code.code_type})")
            print(f"   Description: {code.description}")
            print(f"   Confidence: {code.confidence:.2f}")
            if code.confidence_reason:
                print(f"   Reason: {code.confidence_reason}")
            print(f"   Justification: {code.justification}")
            if code.supporting_text:
                print(f"   Supporting Text:")
                for text in code.supporting_text[:2]:  # Limit to 2 quotes
                    print(f"     - \"{text}\"")

        # Additional Codes
        print(f"\n\n🆕 ADDITIONAL CODES (not in billed): {len(result.additional_codes)}")
        print("-" * 80)
        for i, code in enumerate(result.additional_codes, 1):
            print(f"\n{i}. {code.code} ({code.code_type})")
            print(f"   Description: {code.description}")
            print(f"   Confidence: {code.confidence:.2f}")
            if code.confidence_reason:
                print(f"   Reason: {code.confidence_reason}")

        # Missing Documentation
        if result.missing_documentation:
            print(f"\n\n📝 DOCUMENTATION SUGGESTIONS:")
            print("-" * 80)
            for suggestion in result.missing_documentation:
                print(f"  • {suggestion}")

        # Metadata
        print(f"\n\n📊 METADATA:")
        print("-" * 80)
        print(f"  Model: {result.model_used}")
        print(f"  Processing Time: {result.processing_time_ms}ms")
        print(f"  Tokens Used: {result.tokens_used}")
        print(f"  Cost: ${result.cost_usd:.4f}")

        print("\n" + "=" * 80)

        return result

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_all_notes():
    """Test all clinical notes"""
    print("\n" + "=" * 80)
    print("TESTING ALL CLINICAL NOTES")
    print("=" * 80)

    results = {}
    for note_name in TEST_NOTES.keys():
        result = await test_extraction(note_name)
        results[note_name] = result
        print("\n\n")
        await asyncio.sleep(1)  # Brief pause between tests

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for note_name, result in results.items():
        if result:
            print(f"\n{note_name}:")
            print(f"  Billed codes extracted: {len(result.billed_codes)}")
            print(f"  Suggested codes: {len(result.suggested_codes)}")
            print(f"  Additional codes: {len(result.additional_codes)}")
        else:
            print(f"\n{note_name}: FAILED")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        note_name = sys.argv[1]
        asyncio.run(test_extraction(note_name))
    else:
        print("Usage: python test_ai_extraction.py [note_name]")
        print("\nAvailable test notes:")
        for i, name in enumerate(TEST_NOTES.keys(), 1):
            print(f"  {i}. {name}")
        print("\nOr run with 'all' to test all notes:")
        print("  python test_ai_extraction.py all")
        print("\nExample:")
        print("  python test_ai_extraction.py well_child_explicit_billing")
