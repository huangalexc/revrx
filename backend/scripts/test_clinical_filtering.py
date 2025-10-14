#!/usr/bin/env python3
"""
Test Clinical Relevance Filtering

Shows how GPT-4o-mini filters out non-billing content from clinical notes.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.openai_service import openai_service


# Test clinical note with both relevant and irrelevant content
TEST_NOTE = """Chief Complaint: Follow-up visit for hypertension and diabetes management.

Vital Signs:
- BP: 138/88 mmHg
- HR: 78 bpm
- Temp: 98.6°F
- Weight: 185 lbs
- BMI: 28.3

Screening Tools:
PHQ-9 Depression Score: 3 (minimal depression)
GAD-7 Anxiety Score: 2 (minimal anxiety)

History of Present Illness:
Patient is a 55-year-old male with history of hypertension and type 2 diabetes mellitus. Reports good medication compliance. Blood pressure has been running high at home (150s/90s). Denies chest pain, shortness of breath, or palpitations. Blood sugar readings have been in 120-140 range fasting.

Review of Systems:
Constitutional: Denies fever, chills, weight loss
Cardiovascular: Denies chest pain, palpitations
Respiratory: Denies shortness of breath, cough
GI: Denies nausea, vomiting, diarrhea
Neuro: Denies headaches, dizziness

Physical Examination:
General: Alert, oriented, in no acute distress
Cardiovascular: Regular rate and rhythm, no murmurs
Respiratory: Clear to auscultation bilaterally
Extremities: No edema, pulses 2+ throughout

Labs Reviewed:
HbA1c: 7.8% (elevated)
Creatinine: 1.1 mg/dL (normal)
eGFR: 68 mL/min (mildly decreased)

Assessment and Plan:
1. Hypertension, uncontrolled
   - Increase lisinopril from 10mg to 20mg daily
   - Continue HCTZ 25mg daily
   - Recheck BP in 2 weeks

2. Type 2 Diabetes Mellitus with mild complications
   - Continue metformin 1000mg BID
   - Add glipizide 5mg daily
   - Diabetic education reinforced
   - HbA1c goal <7%

3. Chronic Kidney Disease, Stage 2
   - Related to diabetes and hypertension
   - Recheck kidney function in 3 months
   - Nephrology referral if progression

Patient Education:
- DASH diet handout provided
- Home blood pressure monitoring log given
- Discussed foot care for diabetes
- Medication compliance counseling

Follow-up: 1 month for diabetes/hypertension recheck

Growth Chart (for pediatric template - not applicable):
Height: N/A
Weight percentile: N/A
Head circumference: N/A

Billing Notes:
Level 4 established patient visit
Time: 25 minutes
"""


async def main():
    """Test clinical relevance filtering"""

    print("=" * 80)
    print("CLINICAL RELEVANCE FILTERING TEST")
    print("=" * 80)

    print("\nOriginal Clinical Note:")
    print("-" * 80)
    print(TEST_NOTE)
    print("-" * 80)
    print(f"\nOriginal Length: {len(TEST_NOTE)} characters")

    print("\n" + "=" * 80)
    print("FILTERING WITH GPT-4o-mini")
    print("=" * 80)

    # Call filtering service
    result = await openai_service.filter_clinical_relevance(
        deidentified_text=TEST_NOTE
    )

    print(f"\nFiltered Text:")
    print("-" * 80)
    print(result["filtered_text"])
    print("-" * 80)

    print("\n" + "=" * 80)
    print("FILTERING STATISTICS")
    print("=" * 80)

    print(f"\nOriginal Length: {result['original_length']:,} characters")
    print(f"Filtered Length: {result['filtered_length']:,} characters")
    print(f"Reduction: {result['reduction_pct']}%")
    print(f"\nTokens Used: {result['tokens_used']:,}")
    print(f"Cost: ${result['cost_usd']:.6f}")
    print(f"Processing Time: {result['processing_time_ms']} ms")
    print(f"Model: {result['model_used']}")

    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    print("\nExpected to be REMOVED:")
    print("✓ Vital signs (unless abnormal)")
    print("✓ PHQ-9/GAD-7 screening scores")
    print("✓ Growth chart (pediatric template)")
    print("✓ Patient education handouts")
    print("✓ Billing notes (already captured)")
    print("✓ Normal lab values")

    print("\nExpected to be KEPT:")
    print("✓ Chief complaint")
    print("✓ History of Present Illness")
    print("✓ Review of Systems findings")
    print("✓ Physical exam findings")
    print("✓ Assessment and diagnosis")
    print("✓ Treatment plan")
    print("✓ Abnormal lab values (HbA1c)")
    print("✓ Medical decision making")

    print("\n" + "=" * 80)
    print("COST ANALYSIS")
    print("=" * 80)

    # Calculate cost savings from filtering
    estimated_comprehend_cost_per_100_chars = 0.00001  # Approximate
    original_comprehend_cost = (result['original_length'] / 100) * estimated_comprehend_cost_per_100_chars
    filtered_comprehend_cost = (result['filtered_length'] / 100) * estimated_comprehend_cost_per_100_chars
    comprehend_savings = original_comprehend_cost - filtered_comprehend_cost

    net_cost = result['cost_usd'] - comprehend_savings

    print(f"\nFiltering Cost (GPT-4o-mini): ${result['cost_usd']:.6f}")
    print(f"Est. Comprehend Cost Saved: ${comprehend_savings:.6f}")
    print(f"Net Additional Cost: ${net_cost:.6f}")
    print(f"\nNote: Actual benefit is improved extraction accuracy, not just cost savings")


if __name__ == "__main__":
    asyncio.run(main())
