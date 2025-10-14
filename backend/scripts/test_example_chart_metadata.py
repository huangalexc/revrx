#!/usr/bin/env python3
"""
Test Search Metadata Extraction on Example Chart

Expected results:
- Date of Service: June 5, 2025
- Provider Initials: NT (Nancy Turner)
- Encounter Type: well child visit
"""

import asyncio
import sys
from pathlib import Path
import hashlib

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.openai_service import openai_service
from app.services.comprehend_medical import comprehend_medical_service


async def main():
    """Test search metadata extraction on example chart"""

    # Read example chart
    script_dir = Path(__file__).parent
    chart_file = script_dir.parent.parent / "scripts" / "example_charts.txt"

    with open(chart_file, "r") as f:
        clinical_text = f.read()

    print("=" * 80)
    print("SEARCH METADATA EXTRACTION - EXAMPLE CHART")
    print("=" * 80)

    filename = "example_charts.txt"

    # 1. Calculate filename hash
    print("\n" + "=" * 80)
    print("1. FILENAME HASH")
    print("=" * 80)

    filename_hash = hashlib.sha256(filename.encode()).hexdigest()
    print(f"\nFilename: {filename}")
    print(f"SHA-256 Hash: {filename_hash}")

    # 2. Detect PHI and extract provider/date
    print("\n" + "=" * 80)
    print("2. PHI DETECTION - EXTRACT PROVIDER & DATE")
    print("=" * 80)

    phi_entities = comprehend_medical_service.detect_phi(clinical_text)

    print(f"\nPHI Entities Detected: {len(phi_entities)}")

    # Collect all NAME and DATE entities
    name_entities = []
    date_entities = []

    for entity in phi_entities:
        if entity.type == "NAME":
            name_entities.append(entity)
        elif entity.type == "DATE":
            date_entities.append(entity)

    print(f"\nNAME Entities: {len(name_entities)}")
    for entity in name_entities[:10]:  # Show first 10
        print(f"  - {entity.text} (score: {entity.score:.3f})")

    print(f"\nDATE Entities: {len(date_entities)}")
    for entity in date_entities[:10]:  # Show first 10
        print(f"  - {entity.text} (score: {entity.score:.3f})")

    # Extract provider initials (skip location names)
    provider_initials = None
    provider_name = None

    for entity in name_entities:
        # Skip location names (contain commas or state abbreviations)
        if ',' in entity.text or any(state in entity.text.upper() for state in [' TX', ' NC', ' CA', ' NY']):
            continue

        # Extract initials from name
        name_parts = entity.text.split()
        if len(name_parts) >= 2:
            initials = ''.join([part[0].upper() for part in name_parts[:2] if part])
            if initials and len(initials) >= 2:
                provider_initials = initials
                provider_name = entity.text
                break

    # Extract date of service
    date_of_service = None
    date_text = None

    for entity in date_entities:
        from dateutil import parser as date_parser
        try:
            parsed_date = date_parser.parse(entity.text)
            # Prioritize dates in 2025 (likely service date, not DOB)
            if parsed_date.year == 2025:
                date_of_service = parsed_date
                date_text = entity.text
                break
        except:
            pass

    # If no 2025 date found, take first parseable date
    if not date_of_service:
        for entity in date_entities:
            from dateutil import parser as date_parser
            try:
                parsed_date = date_parser.parse(entity.text)
                date_of_service = parsed_date
                date_text = entity.text
                break
            except:
                pass

    print("\n" + "-" * 80)
    print("EXTRACTION RESULTS:")
    print("-" * 80)
    print(f"✅ Provider Name: {provider_name or 'Not found'}")
    print(f"✅ Provider Initials: {provider_initials or 'Not found'}")
    print(f"✅ Date Text: {date_text or 'Not found'}")
    print(f"✅ Date of Service: {date_of_service.strftime('%B %d, %Y') if date_of_service else 'Not found'}")

    # 3. Clinical relevance filtering - extract encounter type
    print("\n" + "=" * 80)
    print("3. CLINICAL FILTERING - EXTRACT ENCOUNTER TYPE")
    print("=" * 80)

    filtering_result = await openai_service.filter_clinical_relevance(
        deidentified_text=clinical_text
    )

    encounter_type = filtering_result.get("encounter_type")

    print(f"\nOriginal Length: {filtering_result['original_length']:,} chars")
    print(f"Filtered Length: {filtering_result['filtered_length']:,} chars")
    print(f"Reduction: {filtering_result['reduction_pct']}%")
    print(f"✅ Encounter Type: {encounter_type or 'Not found'}")

    # 4. Validation
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)

    print("\nExpected Results:")
    print("  Provider Initials: NT (Nancy Turner)")
    print("  Date of Service: June 5, 2025")
    print("  Encounter Type: well child visit")

    print("\nActual Results:")
    print(f"  Provider Initials: {provider_initials or 'NOT FOUND'} {'✅' if provider_initials == 'NT' else '❌'}")
    print(f"  Date of Service: {date_of_service.strftime('%B %d, %Y') if date_of_service else 'NOT FOUND'} {'✅' if date_of_service and date_of_service.strftime('%B %d, %Y') == 'June 05, 2025' else '❌'}")
    print(f"  Encounter Type: {encounter_type or 'NOT FOUND'} {'✅' if encounter_type and 'well child' in encounter_type.lower() else '❌'}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
