"""
Retry the two encounters that failed with JSON parsing errors
"""
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.test_fhir_full_pipeline import run_full_coding_pipeline
from app.core.database import prisma

# Two encounters that failed with JSON parsing errors
RETRY_ENCOUNTERS = [
    ("a965e34b-a96f-bf08-3f2d-2849fdc12eda", "2017-10-26", "General examination"),
    ("a965e34b-a96f-bf08-730f-9a218e667fbc", "2018-11-01", "General examination"),
]

BUNDLE_PATH = "/Users/alexander/code/revrx/synthetic_data/synthea_fhir4_100/Ahmed109_Bosco882_a965e34b-a96f-bf08-366d-3e4b4ec4c8c0.json"


async def retry_failed_encounters():
    await prisma.connect()

    results = []

    try:
        for i, (enc_id, date, enc_type) in enumerate(RETRY_ENCOUNTERS, 1):
            print(f"\n{'='*80}")
            print(f"RETRY TEST {i}/2: {enc_type} ({date})")
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
        print("RETRY TEST SUMMARY")
        print(f"{'='*80}")

        successful = sum(1 for r in results if r['success'])
        print(f"\nTotal: {successful}/2 successful\n")

        for i, result in enumerate(results, 1):
            status = "✅" if result['success'] else "❌"
            print(f"{i}. {status} {result['date']} | {result['type']}")
            if not result['success']:
                print(f"   Error: {result['error']}")

    finally:
        await prisma.disconnect()


if __name__ == "__main__":
    asyncio.run(retry_failed_encounters())
