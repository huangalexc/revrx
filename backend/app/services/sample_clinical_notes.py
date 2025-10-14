"""
Sample de-identified clinical notes for prompt testing
"""

SAMPLE_NOTE_1_WELLNESS_VISIT = """
CHIEF COMPLAINT: Annual wellness visit

PATIENT: [REDACTED-1], 8-year-old established patient

DATE: [REDACTED-DATE]

HISTORY OF PRESENT ILLNESS:
Patient presents for annual wellness examination. Mother reports patient is doing well overall.
No acute concerns. Patient continues to do well in school.

REVIEW OF SYSTEMS:
Constitutional: No fever, weight loss, or fatigue
HEENT: No headaches, vision changes, or hearing problems
Respiratory: No cough, wheezing, or shortness of breath
Cardiovascular: No chest pain or palpitations
GI: No abdominal pain, nausea, vomiting, or diarrhea
GU: No dysuria or hematuria
Musculoskeletal: No joint pain or swelling
Neurological: No dizziness, syncope, or seizures
Psychiatric: No depression or anxiety

PAST MEDICAL HISTORY:
- Asthma (mild intermittent, well-controlled)

MEDICATIONS:
- Albuterol inhaler PRN (rarely uses)

ALLERGIES: NKDA

PHYSICAL EXAMINATION:
Vitals: BP 105/68, HR 82, RR 18, Temp 98.4°F, Wt 58 lbs (50th percentile), Ht 50 inches (60th percentile)
General: Well-appearing, in no acute distress
HEENT: Normocephalic, atraumatic. PERRLA. TMs clear bilaterally. Oropharynx clear.
Neck: Supple, no lymphadenopathy
Cardiovascular: Regular rate and rhythm, no murmurs
Lungs: Clear to auscultation bilaterally, no wheezes
Abdomen: Soft, non-tender, non-distended, normal bowel sounds
Extremities: No edema, normal strength and ROM
Neurological: Alert and oriented, appropriate affect

ASSESSMENT/PLAN:
1. Wellness visit - healthy 8-year-old
   - Discussed nutrition, exercise, safety
   - Reviewed developmental milestones - age appropriate
   - Discussed screen time limits
2. Asthma - well controlled, continue current management
   - Patient rarely needs rescue inhaler
   - No nighttime symptoms or activity limitations

Anticipatory guidance provided regarding safety, nutrition, and development. All questions answered.

Time: 20 minutes face-to-face with patient and mother

BILLING:
CPT: 99393 (Preventive medicine, established patient, age 5-11)
ICD-10: Z00.129 (Encounter for routine child health examination without abnormal findings)
"""

SAMPLE_NOTE_2_CHRONIC_DISEASE = """
CHIEF COMPLAINT: Follow-up diabetes, hypertension, hyperlipidemia

PATIENT: [REDACTED-2], 62-year-old established patient

DATE: [REDACTED-DATE]

HISTORY OF PRESENT ILLNESS:
Patient returns for routine follow-up of chronic conditions. Reports generally feeling well.
Blood sugars have been running 110-140 fasting per home glucose log. Compliant with medications.
Denies chest pain, shortness of breath, or edema. Some occasional headaches but no vision changes.
Diet compliance has been "pretty good" but admits to occasional dietary indiscretions.

REVIEW OF SYSTEMS:
Per HPI, otherwise negative in detail

PAST MEDICAL HISTORY:
- Type 2 Diabetes Mellitus (diagnosed 2018)
- Hypertension (diagnosed 2015)
- Hyperlipidemia (diagnosed 2016)
- Obesity

MEDICATIONS REVIEWED:
- Metformin 1000mg BID
- Lisinopril 20mg daily
- Atorvastatin 40mg daily
- Aspirin 81mg daily

ALLERGIES: Penicillin (rash)

PHYSICAL EXAMINATION:
Vitals: BP 138/84, HR 76, RR 16, Temp 98.6°F, Wt 215 lbs, BMI 32.4
General: Overweight, pleasant, in no distress
HEENT: Normocephalic, atraumatic. PERRLA. Oropharynx clear.
Neck: Supple, no JVD
Cardiovascular: RRR, normal S1/S2, no murmurs
Lungs: Clear to auscultation bilaterally
Abdomen: Obese, soft, non-tender, normal bowel sounds
Extremities: No edema, distal pulses intact bilaterally, monofilament sensation intact
Skin: No ulcerations

LABS REVIEWED (drawn last week):
HbA1c: 7.2% (improved from 7.8% three months ago)
Lipid panel: Total cholesterol 185, LDL 98, HDL 42, Triglycerides 210
Creatinine: 1.1 (eGFR >60)
Microalbumin: negative

ASSESSMENT/PLAN:
1. Type 2 Diabetes Mellitus - improved control
   - HbA1c improved, continue current regimen
   - Continue Metformin 1000mg BID
   - Reinforced importance of diet and exercise
   - Home glucose monitoring compliance good
   - Annual diabetic foot exam performed today - no neuropathy detected
   - Referral to ophthalmology for annual diabetic eye exam

2. Hypertension - adequately controlled
   - BP slightly elevated today but within acceptable range
   - Continue Lisinopril 20mg daily
   - Patient to monitor BP at home

3. Hyperlipidemia - on target
   - LDL at goal <100
   - Triglycerides elevated, discussed dietary modifications
   - Continue Atorvastatin 40mg daily

4. Obesity - counseling provided
   - BMI 32.4, discussed weight loss goals
   - Provided nutrition counseling (15 minutes)
   - Encouraged increased physical activity

Continue all current medications. Return to clinic in 3 months for recheck.

Total time: 35 minutes, >50% spent in counseling regarding diabetes management, nutrition, and lifestyle modifications.

PHQ-9 depression screening administered: Score 2 (minimal symptoms)

BILLING CODES:
E/M Level: 99214 (established patient, moderate complexity)
ICD-10: E11.9 (Type 2 diabetes without complications), I10 (Essential hypertension), E78.5 (Hyperlipidemia)
"""

SAMPLE_NOTE_3_UNDERCODED = """
CHIEF COMPLAINT: Sore throat, cough

PATIENT: [REDACTED-3], 42-year-old established patient

DATE: [REDACTED-DATE]

HISTORY OF PRESENT ILLNESS:
Patient presents with 3 days of sore throat, productive cough, and subjective fever.
Denies shortness of breath or chest pain. Has been taking OTC medications with minimal relief.
Wife had similar symptoms last week.

PAST MEDICAL HISTORY: None significant

MEDICATIONS: None

ALLERGIES: NKDA

PHYSICAL EXAMINATION:
Vitals: Temp 100.8°F, BP 128/78, HR 88, RR 16
General: Mildly ill-appearing but in no distress
HEENT: Pharyngeal erythema, no exudates. No cervical lymphadenopathy.
Lungs: Scattered rhonchi, no wheezes or rales
Heart: RRR, no murmurs

RAPID STREP TEST: Negative

ASSESSMENT/PLAN:
Acute viral pharyngitis with bronchitis
- Supportive care, fluids, rest
- Continue OTC analgesics
- Return if worsening or no improvement in 5-7 days

BILLING:
99213
"""

SAMPLE_BILLED_CODES = {
    "note_1": [
        {"code": "99393", "code_type": "CPT", "description": "Preventive medicine service, established patient, age 5-11"},
        {"code": "Z00.129", "code_type": "ICD-10", "description": "Routine child health exam without abnormal findings"}
    ],
    "note_2": [
        {"code": "99214", "code_type": "CPT", "description": "Office visit, established patient, moderate complexity"},
        {"code": "E11.9", "code_type": "ICD-10", "description": "Type 2 diabetes without complications"},
        {"code": "I10", "code_type": "ICD-10", "description": "Essential hypertension"},
        {"code": "E78.5", "code_type": "ICD-10", "description": "Hyperlipidemia"}
    ],
    "note_3": [
        {"code": "99213", "code_type": "CPT", "description": "Office visit, established patient, low complexity"}
    ]
}

# Expected analysis outcomes for testing
EXPECTED_OUTCOMES = {
    "note_1": {
        "should_suggest": ["J45.20"],  # Asthma ICD code missing
        "documentation_gaps": ["Asthma documented but not coded"],
        "denial_risk": "Low",
        "uncaptured_services": ["Asthma management documented"],
    },
    "note_2": {
        "should_suggest": ["96127", "G0438/G0439"],  # Depression screening, Annual wellness components
        "documentation_gaps": ["Could document MDM in more detail for 99215"],
        "modifier_needed": None,
        "uncaptured_services": ["PHQ-9 screening (96127)", "Diabetic foot exam", "Nutrition counseling"],
        "rvu_opportunity": "Moderate - missing 96127 and potentially diabetic foot exam codes"
    },
    "note_3": {
        "should_suggest": ["J02.9", "J20.9"],  # Pharyngitis and Bronchitis ICD codes
        "documentation_gaps": ["Consider documenting MDM complexity in more detail"],
        "potential_upgrade": "Could potentially be 99214 with more detailed documentation",
        "uncaptured_services": ["Rapid strep test (87880)"],
    }
}
