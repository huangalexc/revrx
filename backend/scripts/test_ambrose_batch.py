"""
Test FHIR pipeline on 10 encounters from Ambrose patient
"""
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.test_fhir_full_pipeline import run_full_coding_pipeline
from app.core.database import prisma

# 10 encounters from Ambrose patient (well child visits and check-ups)
TEST_ENCOUNTERS = [
    ("ae08bbe6-91da-5961-dd43-c06de5fb5775", "2015-08-04", "Well child visit (procedure)"),
    ("ae08bbe6-91da-5961-123b-fc2b2690f41e", "2016-08-09", "Well child visit (procedure)"),
    ("ae08bbe6-91da-5961-0dc5-0f0715749181", "2016-08-16", "Encounter for check up (procedure)"),
    ("ae08bbe6-91da-5961-f839-18622a5809cf", "2017-08-15", "Well child visit (procedure)"),
    ("ae08bbe6-91da-5961-3ccb-9b2bce852b2a", "2017-08-22", "Encounter for check up (procedure)"),
    ("ae08bbe6-91da-5961-8f14-522d5b4ab465", "2018-08-21", "Well child visit (procedure)"),
    ("ae08bbe6-91da-5961-fab5-228fe25f47b9", "2018-09-04", "Encounter for check up (procedure)"),
    ("ae08bbe6-91da-5961-2cfa-1ea3446842d1", "2019-08-27", "Well child visit (procedure)"),
    ("ae08bbe6-91da-5961-b595-5ec5d4a7d35e", "2020-09-01", "Well child visit (procedure)"),
    ("ae08bbe6-91da-5961-fdab-0565f162ad19", "2020-09-15", "Encounter for check up (procedure)"),
]

BUNDLE_PATH = "/Users/alexander/code/revrx/synthetic_data/synthea_fhir4_100/Ambrose149_Abshire638_ae08bbe6-91da-5961-f3fc-5e8360c29937.json"


async def test_ambrose_encounters():
    await prisma.connect()

    results = []

    try:
        for i, (enc_id, date, enc_type) in enumerate(TEST_ENCOUNTERS, 1):
            print(f"\n{'='*80}")
            print(f"TEST {i}/10: {enc_type} ({date})")
            print(f"ID: {enc_id}")
            print(f"{'='*80}\n")

            try:
                await run_full_coding_pipeline(enc_id, BUNDLE_PATH)
                results.append({
                    'success': True,
                    'encounter_id': enc_id,
                    'date': date,
                    'type': enc_type
                })
                print(f"\n✅ SUCCESS\n")
            except Exception as e:
                error_msg = str(e)[:200]  # Truncate long errors
                results.append({
                    'success': False,
                    'encounter_id': enc_id,
                    'date': date,
                    'type': enc_type,
                    'error': error_msg
                })
                print(f"\n❌ FAILED: {error_msg}\n")

        # Summary
        print(f"\n{'='*80}")
        print("BATCH TEST SUMMARY")
        print(f"{'='*80}")

        successful = sum(1 for r in results if r['success'])
        print(f"\nTotal: {successful}/10 successful\n")

        for i, result in enumerate(results, 1):
            status = "✅" if result['success'] else "❌"
            print(f"{i:2d}. {status} {result['date']} | {result['type']}")
            if not result['success']:
                print(f"     Error: {result['error']}")

    finally:
        await prisma.disconnect()


if __name__ == "__main__":
    asyncio.run(test_ambrose_encounters())
