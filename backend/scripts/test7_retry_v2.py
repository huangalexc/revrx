"""
Test 7 retry with 2-prompt approach
"""
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.test_fhir_full_pipeline import run_full_coding_pipeline
from app.core.database import prisma

# Test 7 details
ENCOUNTER_ID = "a965e34b-a96f-bf08-730f-9a218e667fbc"
DATE = "2018-11-01"
TYPE = "General examination"
BUNDLE_PATH = "/Users/alexander/code/revrx/synthetic_data/synthea_fhir4_100/Ahmed109_Bosco882_a965e34b-a96f-bf08-366d-3e4b4ec4c8c0.json"


async def test7_retry():
    """Re-run Test 7 with 2-prompt approach"""
    await prisma.connect()

    try:
        print(f"{'='*80}")
        print(f"TEST 7 RETRY (2-Prompt Approach): {TYPE} ({DATE})")
        print(f"ID: {ENCOUNTER_ID}")
        print(f"{'='*80}\n")

        await run_full_coding_pipeline(ENCOUNTER_ID, BUNDLE_PATH)

        print(f"\n{'='*80}")
        print("✅ TEST 7 SUCCESSFUL WITH 2-PROMPT APPROACH")
        print(f"{'='*80}")

    except Exception as e:
        print(f"\n{'='*80}")
        print(f"❌ TEST 7 FAILED: {str(e)}")
        print(f"{'='*80}")
        raise

    finally:
        await prisma.disconnect()


if __name__ == "__main__":
    asyncio.run(test7_retry())
