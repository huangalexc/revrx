"""
Test FHIR pipeline on multiple encounter types
"""
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.test_fhir_full_pipeline import run_full_coding_pipeline
from app.core.database import prisma

# Test encounters from the synthetic data
TEST_ENCOUNTERS = [
    {
        "id": "296e9f96-4897-f44b-9b53-217d8a8df81e",
        "type": "Well child visit",
        "date": "1964-03-04",
        "description": "Routine pediatric well-child visit"
    },
    {
        "id": "296e9f96-4897-f44b-851e-f3731baf64d8", 
        "type": "Dental check-up",
        "date": "2025-07-09",
        "description": "Routine dental encounter"
    },
    {
        "id": "296e9f96-4897-f44b-2508-e8322dd2fbe0",
        "type": "Urgent care",
        "date": "2012-08-01",
        "description": "Urgent care clinic visit"
    },
    {
        "id": "296e9f96-4897-f44b-908d-5661e2eef92b",
        "type": "Vaccination",
        "date": "2021-03-17",
        "description": "COVID-19 vaccination"
    },
]

BUNDLE_PATH = "/Users/alexander/code/revrx/synthetic_data/synthea_fhir4_100/Adam631_Gusikowski974_296e9f96-4897-f44b-39d3-1127e65f9e80.json"


async def test_multiple_encounters():
    """Test pipeline on multiple encounter types"""
    
    try:
        await prisma.connect()
        
        results = []
        
        for i, encounter in enumerate(TEST_ENCOUNTERS, 1):
            print("\n" + "=" * 100)
            print(f"TEST {i}/{len(TEST_ENCOUNTERS)}: {encounter['type']} ({encounter['date']})")
            print(f"Encounter ID: {encounter['id']}")
            print(f"Description: {encounter['description']}")
            print("=" * 100)
            
            try:
                # Run pipeline
                result = await run_full_coding_pipeline(encounter['id'], BUNDLE_PATH)
                
                # Store summary
                results.append({
                    "encounter": encounter,
                    "success": True,
                    "result": result
                })
                
                print(f"\n✅ SUCCESS: {encounter['type']} completed")
                
            except Exception as e:
                print(f"\n❌ ERROR: {encounter['type']} failed")
                print(f"   Error: {str(e)}")
                results.append({
                    "encounter": encounter,
                    "success": False,
                    "error": str(e)
                })
        
        # Print summary
        print("\n" + "=" * 100)
        print("FINAL SUMMARY")
        print("=" * 100)
        
        for i, result in enumerate(results, 1):
            enc = result['encounter']
            status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
            print(f"{i}. {enc['type']:20} ({enc['date']}) - {status}")
        
        successful = sum(1 for r in results if r['success'])
        print(f"\nTotal: {successful}/{len(results)} successful")
        
    finally:
        await prisma.disconnect()


if __name__ == "__main__":
    asyncio.run(test_multiple_encounters())
