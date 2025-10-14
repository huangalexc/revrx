"""
Test Clinical Notes for AI Extraction
Various formats of clinical notes with different billing patterns
"""

TEST_NOTES = {
    "well_child_explicit_billing": """
PATIENT: John Doe, Age 8
DATE: 2024-10-03

CHIEF COMPLAINT: Well child check and sports physical

HISTORY: Patient presents for annual well child examination. No current concerns.
Parent reports child is doing well in school. Active in sports. No significant
medical history.

PHYSICAL EXAM:
- General: Well-appearing, no acute distress
- HEENT: Normal
- Cardiovascular: RRR, no murmurs
- Respiratory: Clear bilaterally
- Abdomen: Soft, non-tender
- Extremities: Full ROM, no deformities

ASSESSMENT:
Healthy 8-year-old male. Annual preventive visit completed.
Sports clearance provided.

PLAN:
- Continue routine health maintenance
- Return in 1 year or PRN
- Sports physical form completed

TIME: 30 minutes face-to-face

BILLING:
CPT: 99393 - Periodic comprehensive preventive medicine, established patient, age 5-11
ICD-10: Z00.129 - Encounter for routine child health examination without abnormal findings
""",

    "office_visit_with_codes": """
OFFICE VISIT NOTE

Patient: Jane Smith, DOB: 05/15/1985
Date of Service: 10/03/2024

CC: Follow-up diabetes management, hypertension check

HPI: Patient presents for routine diabetes and HTN management. Blood sugars
have been well controlled on current regimen (morning 105-120, evening 110-130).
Blood pressure at home averaging 128/82. Taking all medications as prescribed.
Denies chest pain, SOB, edema, or other concerns.

MEDICATIONS:
- Metformin 1000mg BID
- Lisinopril 10mg daily
- Atorvastatin 20mg daily

PHYSICAL EXAM:
Vitals: BP 126/80, HR 72, Temp 98.6F
General: Well-appearing
CV: RRR, no murmurs
Lungs: Clear
Feet: No ulcers, pulses intact

LABS REVIEWED:
HbA1c: 6.8% (excellent control)
LDL: 95 mg/dL (at goal)
Creatinine: 0.9 (stable)

ASSESSMENT & PLAN:
1. Type 2 Diabetes - well controlled, continue current therapy
2. Essential Hypertension - at goal, continue lisinopril
3. Hyperlipidemia - at goal, continue statin

Follow-up in 3 months with repeat labs

Time spent: 25 minutes, >50% counseling on diet/exercise

CODES BILLED:
CPT 99214 - Office visit, established patient, moderate complexity
ICD-10 E11.9 - Type 2 diabetes mellitus without complications
ICD-10 I10 - Essential hypertension
ICD-10 E78.5 - Hyperlipidemia, unspecified
""",

    "ed_visit_informal_billing": """
EMERGENCY DEPARTMENT NOTE

Patient: Robert Johnson
Age: 45
Date: 10/03/2024

CHIEF COMPLAINT: Ankle pain after fall

HPI: Patient twisted ankle while playing basketball 2 hours ago. Immediate
pain and swelling. Able to bear some weight but with significant discomfort.
No previous ankle injuries. Denies loss of consciousness or other injuries.

EXAM:
Vitals: BP 138/86, HR 88, RR 16, SpO2 98% RA
Right ankle: Swelling and ecchymosis over lateral malleolus
Tenderness to palpation over ATFL
Range of motion limited by pain
Neurovascularly intact

X-RAY: Right ankle 3 views
No fracture identified. Soft tissue swelling noted.

ASSESSMENT: Right ankle sprain (ATFL), no fracture

TREATMENT:
- Ice pack applied
- Ace wrap applied
- Ibuprofen 800mg PO given
- Crutches provided
- Work excuse for 3 days

DISPOSITION: Discharge home with crutches and ankle brace

FOLLOW-UP: Orthopedics in 1 week if not improving

Billed as: ED visit level 3 (99283) with ankle sprain diagnosis (S93.491A)
""",

    "procedure_note_no_billing": """
COLONOSCOPY PROCEDURE NOTE

Patient: Mary Williams, DOB: 03/22/1960
Date: 10/03/2024
Indication: Screening colonoscopy (family history of colon cancer)

PROCEDURE: Colonoscopy with biopsy

FINDINGS:
- Prep quality: Excellent (Boston 9)
- Cecum reached and photographed (cecal intubation time: 8 min)
- Withdrawal time: 12 minutes
- Two small polyps identified in sigmoid colon (5mm and 7mm)
- Both polyps removed with cold snare technique
- Specimens sent to pathology

IMPRESSION:
1. Two sigmoid polyps removed (likely tubular adenomas pending path)
2. Otherwise normal colonoscopy to cecum

RECOMMENDATIONS:
- Await pathology results
- Recommend repeat colonoscopy in 3-5 years depending on pathology
- Continue high-fiber diet

Patient tolerated procedure well. Discharged to recovery in stable condition.

Note: This visit included screening colonoscopy (45378) with polyp removal (45385).
Diagnosis code for screening with family history (Z12.11).
""",

    "no_billing_mentioned": """
PHYSICAL THERAPY EVALUATION

Patient: David Chen
Age: 52
Date: 10/03/2024
Referral: Low back pain

SUBJECTIVE:
Patient reports chronic low back pain x 6 months. Pain is 6/10 at rest, 8/10
with bending. Denies radiation to legs. No numbness/tingling. Has tried
NSAIDs with minimal relief.

OBJECTIVE:
Posture: Forward head posture, increased lumbar lordosis
ROM: Lumbar flexion 60° (limited), extension 15° (limited)
Strength: Hip flexors 4/5 bilaterally, core 3+/5
Palpation: Tenderness over L4-L5, muscle spasm in paraspinals
Special tests: Negative SLR bilaterally

ASSESSMENT:
Chronic mechanical low back pain likely due to poor posture and weak core.
Good candidate for physical therapy.

PLAN:
- PT 2x/week x 6 weeks
- Focus on core strengthening, posture training, manual therapy
- Home exercise program provided
- Re-evaluate in 2 weeks

Goals: Reduce pain to 3/10, improve lumbar ROM by 25%, return to golf
"""
}


def get_test_note(note_name: str) -> str:
    """Get a test clinical note by name"""
    return TEST_NOTES.get(note_name, "")


def list_test_notes() -> list:
    """List all available test note names"""
    return list(TEST_NOTES.keys())


if __name__ == "__main__":
    print("Available test notes:")
    for i, name in enumerate(list_test_notes(), 1):
        print(f"{i}. {name}")
        print(f"   Length: {len(TEST_NOTES[name])} chars")
        print()
