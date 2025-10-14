"""
Reprocess a specific encounter with the updated AI extraction logic
"""

import asyncio
import sys
import json
from app.core.database import prisma
from app.services.openai_service import openai_service
from app.services.code_comparison import code_comparison_engine


async def reprocess_encounter(encounter_id: str):
    """Reprocess an encounter with updated AI extraction"""

    print(f"Reprocessing encounter: {encounter_id}")
    print("=" * 80)

    # Connect to database
    await prisma.connect()

    try:
        # Get encounter with phi mapping
        encounter = await prisma.encounter.find_unique(
            where={"id": encounter_id},
            include={
                "phiMapping": True,
                "report": True,
                "billingCodes": True
            }
        )

        if not encounter:
            print(f"❌ Encounter {encounter_id} not found")
            return

        if not encounter.phiMapping:
            print(f"❌ No PHI mapping found for encounter {encounter_id}")
            return

        clinical_note = encounter.phiMapping.deidentifiedText

        print(f"✓ Found encounter")
        print(f"  Status: {encounter.status}")
        print(f"  Clinical note length: {len(clinical_note)} chars")
        print()

        # Get billed codes from database
        billed_codes = [
            {
                "code": bc.code,
                "code_type": bc.codeType,
                "description": bc.description or ""
            }
            for bc in encounter.billingCodes
        ]

        print(f"📋 Billed codes from database: {len(billed_codes)}")
        for bc in billed_codes:
            print(f"  • {bc['code']} ({bc['code_type']}): {bc['description']}")
        print()

        # Run AI analysis
        print("Running AI analysis with updated extraction...")
        print("-" * 80)

        ai_result = await openai_service.analyze_clinical_note(
            clinical_note=clinical_note,
            billed_codes=billed_codes
        )

        print(f"\n✓ AI Analysis Complete")
        print(f"  Processing time: {ai_result.processing_time_ms}ms")
        print(f"  Cost: ${ai_result.cost_usd:.4f}")
        print()

        # Display extracted billed codes
        print(f"📋 BILLED CODES EXTRACTED: {len(ai_result.billed_codes)}")
        print("-" * 80)
        if ai_result.billed_codes:
            for code in ai_result.billed_codes:
                print(f"  ✓ {code.code} ({code.code_type})")
                print(f"    {code.description}")
        else:
            print("  (None found)")
        print()

        # Display suggested codes
        print(f"💡 SUGGESTED CODES: {len(ai_result.suggested_codes)}")
        print("-" * 80)
        for i, code in enumerate(ai_result.suggested_codes[:5], 1):  # Show first 5
            print(f"\n  {i}. {code.code} ({code.code_type})")
            print(f"     {code.description}")
            print(f"     Confidence: {code.confidence:.2f}")
            if code.confidence_reason:
                print(f"     Reason: {code.confidence_reason}")
        if len(ai_result.suggested_codes) > 5:
            print(f"\n  ... and {len(ai_result.suggested_codes) - 5} more")
        print()

        # Run code comparison
        print("Running code comparison...")
        print("-" * 80)

        comparison_result = code_comparison_engine.compare_codes(
            billed_codes=[c.to_dict() for c in ai_result.billed_codes],
            ai_result=ai_result
        )

        print(f"✓ Code Comparison Complete")
        print(f"  New codes: {comparison_result.new_codes_count}")
        print(f"  Upgrades: {comparison_result.upgrade_opportunities_count}")
        print(f"  Incremental Revenue: ${comparison_result.incremental_revenue:.2f}")
        print()

        # Update report in database
        print("Updating report in database...")
        print("-" * 80)

        # Calculate average confidence
        avg_confidence = (
            sum(c.confidence for c in ai_result.additional_codes) / len(ai_result.additional_codes)
            if ai_result.additional_codes
            else 0.0
        )

        report_data = {
            "billedCodes": json.dumps([c.to_dict() for c in ai_result.billed_codes]),
            "suggestedCodes": json.dumps([c.to_dict() for c in ai_result.additional_codes]),
            "incrementalRevenue": comparison_result.incremental_revenue,
            "aiModel": ai_result.model_used,
            "confidenceScore": avg_confidence,
        }

        if encounter.report:
            # Update existing report
            await prisma.report.update(
                where={"id": encounter.report.id},
                data=report_data
            )
            print("✓ Report updated")
        else:
            # Create new report
            await prisma.report.create(
                data={
                    "encounterId": encounter_id,
                    **report_data
                }
            )
            print("✓ Report created")

        print()
        print("=" * 80)
        print("✅ REPROCESSING COMPLETE")
        print("=" * 80)
        print(f"\nView report at: http://localhost:3000/reports/{encounter_id}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await prisma.disconnect()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python reprocess_encounter.py <encounter_id>")
        print("\nExample:")
        print("  python reprocess_encounter.py a0334e57-1dc5-4fe0-b662-465d64989f71")
        sys.exit(1)

    encounter_id = sys.argv[1]
    asyncio.run(reprocess_encounter(encounter_id))
