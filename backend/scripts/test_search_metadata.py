#!/usr/bin/env python3
"""
Test Search Metadata Extraction

Tests extraction of:
1. Filename hash (SHA-256)
2. Provider initials (from PHI detection)
3. Date of service (from PHI detection)
4. Encounter type (from clinical filtering)
"""

import asyncio
import sys
from pathlib import Path
import hashlib

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.openai_service import openai_service
from app.services.comprehend_medical import comprehend_medical_service


# Test clinical note with provider name and dates
TEST_NOTE = """CLINIC, PLLC
ADDRESS
Tel: PHONE_1 Email: EMAIL
Chart
NAME_1
Patient Number: 4
Date of Birth: 01/15/2014
Cary, NC
Tel: PHONE_2
10/05/2025 Added by: John Smith, MD -
History

HPI
NAME_1 presents for his 11-year well child check. He reports feeling well and has no concerns at this time.

Assessment
NAME_1 is an 11-year-old male presenting for his well child check. Physical exam is within normal limits.
NAME_1 is growing and developing appropriately.

Plan
Well Child Check
• Sports physical form completed and signed.
• Follow up in one year for next well child check.

John Smith, MD
10/05/2025 at 11:55am
"""

FILENAME = "John_Smith_MD_Patient_NAME1_20251005.txt"


async def main():
    """Test search metadata extraction"""

    print("=" * 80)
    print("SEARCH METADATA EXTRACTION TEST")
    print("=" * 80)

    # 1. Calculate filename hash
    print("\n" + "=" * 80)
    print("1. FILENAME HASH")
    print("=" * 80)

    filename_hash = hashlib.sha256(FILENAME.encode()).hexdigest()
    print(f"\nFilename: {FILENAME}")
    print(f"SHA-256 Hash: {filename_hash}")
    print(f"Hash Preview: {filename_hash[:32]}...")

    # 2. Detect PHI and extract provider/date
    print("\n" + "=" * 80)
    print("2. PHI DETECTION - EXTRACT PROVIDER & DATE")
    print("=" * 80)

    phi_entities = comprehend_medical_service.detect_phi(TEST_NOTE)

    print(f"\nPHI Entities Detected: {len(phi_entities)}")

    # Extract provider initials and date
    provider_initials = None
    date_of_service = None

    for entity in phi_entities:
        print(f"\n  - Type: {entity.type}")
        print(f"    Text: {entity.text}")
        print(f"    Score: {entity.score:.3f}")

        # Extract provider name
        if entity.type == "NAME" and not provider_initials:
            name_parts = entity.text.split()
            if len(name_parts) >= 2:
                initials = ''.join([part[0].upper() for part in name_parts[:2] if part])
                if initials and len(initials) >= 2:
                    provider_initials = initials
                    print(f"    → Provider Initials: {provider_initials}")

        # Extract date
        if entity.type == "DATE" and not date_of_service:
            from dateutil import parser as date_parser
            try:
                parsed_date = date_parser.parse(entity.text)
                date_of_service = parsed_date
                print(f"    → Date of Service: {date_of_service.isoformat()}")
            except:
                pass

    print("\n" + "-" * 80)
    print(f"✅ Provider Initials: {provider_initials or 'Not found'}")
    print(f"✅ Date of Service: {date_of_service.isoformat() if date_of_service else 'Not found'}")

    # 3. Clinical relevance filtering - extract encounter type
    print("\n" + "=" * 80)
    print("3. CLINICAL FILTERING - EXTRACT ENCOUNTER TYPE")
    print("=" * 80)

    # Use original text for filtering (in real system it would be deidentified)
    deidentified_text = TEST_NOTE

    filtering_result = await openai_service.filter_clinical_relevance(
        deidentified_text=deidentified_text
    )

    encounter_type = filtering_result.get("encounter_type")

    print(f"\nFiltered Text Length: {filtering_result['filtered_length']:,} chars")
    print(f"Reduction: {filtering_result['reduction_pct']}%")
    print(f"✅ Encounter Type: {encounter_type or 'Not found'}")

    # 4. Summary
    print("\n" + "=" * 80)
    print("SUMMARY - ENCOUNTER SEARCH METADATA")
    print("=" * 80)

    print(f"\n📄 File Identification:")
    print(f"   Filename: {FILENAME}")
    print(f"   Hash: {filename_hash[:32]}...")

    print(f"\n👨‍⚕️ Provider Information:")
    print(f"   Initials: {provider_initials or 'N/A'}")

    print(f"\n📅 Date Information:")
    print(f"   Date of Service: {date_of_service.strftime('%Y-%m-%d') if date_of_service else 'N/A'}")

    print(f"\n🏥 Encounter Information:")
    print(f"   Type: {encounter_type or 'N/A'}")

    print("\n" + "=" * 80)
    print("USE CASES")
    print("=" * 80)

    print("\nThese fields enable:")
    print("  1. Search encounters by provider initials (e.g., 'JS' for John Smith)")
    print("  2. Search encounters by date of service")
    print("  3. Filter encounters by type (well child, follow-up, etc.)")
    print("  4. Match duplicate uploads by filename hash")
    print("  5. Build provider-specific reports and analytics")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
