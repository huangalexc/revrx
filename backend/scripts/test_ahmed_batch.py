"""
Test FHIR pipeline on 10 encounters from Ahmed patient
"""
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.test_fhir_full_pipeline import run_full_coding_pipeline
from app.core.database import prisma

# 10 encounters from Ahmed patient (diverse types)
TEST_ENCOUNTERS = [
    ("a965e34b-a96f-bf08-5c12-581e32f35ba7", "2015-09-26", "Encounter for problem"),
    ("a965e34b-a96f-bf08-be9e-fa07de35cd5f", "2015-10-15", "General examination"),
    ("a965e34b-a96f-bf08-2abe-e068e53774e9", "2016-10-20", "General examination"),
    ("a965e34b-a96f-bf08-7aaa-1d10e19b391e", "2016-10-27", "Encounter for problem"),
    ("a965e34b-a96f-bf08-3f2d-2849fdc12eda", "2017-10-26", "General examination"),
    ("a965e34b-a96f-bf08-5776-212a43696475", "2017-11-09", "Check-up"),
    ("a965e34b-a96f-bf08-730f-9a218e667fbc", "2018-11-01", "General examination"),
    ("a965e34b-a96f-bf08-4c45-ca878b573059", "2019-11-07", "General examination"),
    ("a965e34b-a96f-bf08-f7af-60b394e3fd9f", "2020-11-12", "General examination"),
    ("a965e34b-a96f-bf08-b8e8-b1b21fc2fab4", "2021-11-18", "General examination"),
]

BUNDLE_PATH = "/Users/alexander/code/revrx/synthetic_data/synthea_fhir4_100/Ahmed109_Bosco882_a965e34b-a96f-bf08-366d-3e4b4ec4c8c0.json"


async def test_ahmed_encounters():
    """Test pipeline on Ahmed patient encounters"""
    
    try:
        await prisma.connect()
        
        results = []
        
        for i, (enc_id, date, enc_type) in enumerate(TEST_ENCOUNTERS, 1):
            print(f"\n{'='*80}")
            print(f"TEST {i}/10: {enc_type} ({date})")
            print(f"ID: {enc_id}")
            print(f"{'='*80}")
            
            try:
                await run_full_coding_pipeline(enc_id, BUNDLE_PATH)
                
                results.append({
                    "id": enc_id,
                    "date": date,
                    "type": enc_type,
                    "success": True
                })
                
                print(f"\n✅ SUCCESS")
                
            except Exception as e:
                print(f"\n❌ FAILED: {str(e)[:100]}")
                results.append({
                    "id": enc_id,
                    "date": date,
                    "type": enc_type,
                    "success": False,
                    "error": str(e)[:200]
                })
        
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
    asyncio.run(test_ahmed_encounters())
