#!/usr/bin/env python3
"""
Test Placeholder-Based Provider/Date Extraction

Tests the new approach where GPT-4o-mini identifies which numbered
placeholders correspond to the provider and service date.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.openai_service import openai_service
from app.services.comprehend_medical import comprehend_medical_service
from app.services.phi_handler import phi_handler


async def main():
    """Test placeholder-based extraction"""

    # Read example chart
    script_dir = Path(__file__).parent
    chart_file = script_dir.parent.parent / "scripts" / "example_charts.txt"

    with open(chart_file, "r") as f:
        clinical_text = f.read()

    print("=" * 80)
    print("PLACEHOLDER-BASED PROVIDER/DATE EXTRACTION TEST")
    print("=" * 80)

    # Step 1: Deidentify text (creates numbered placeholders)
    print("\n" + "=" * 80)
    print("STEP 1: DEIDENTIFY TEXT (CREATE PLACEHOLDERS)")
    print("=" * 80)

    deid_result = phi_handler.detect_and_deidentify(clinical_text)

    print(f"\nPHI Entities Detected: {len(deid_result.phi_entities)}")
    print(f"Unique Placeholders Created:")

    # Group mappings by type
    by_type = {}
    for mapping in deid_result.phi_mappings:
        if mapping.entity_type not in by_type:
            by_type[mapping.entity_type] = []
        by_type[mapping.entity_type].append(mapping)

    for entity_type in sorted(by_type.keys()):
        print(f"\n{entity_type}:")
        for mapping in by_type[entity_type][:5]:  # Show first 5
            print(f"  {mapping.token} = {mapping.original}")
        if len(by_type[entity_type]) > 5:
            print(f"  ... and {len(by_type[entity_type]) - 5} more")

    # Step 2: Send to LLM for placeholder identification
    print("\n" + "=" * 80)
    print("STEP 2: LLM IDENTIFIES PROVIDER & SERVICE DATE PLACEHOLDERS")
    print("=" * 80)

    print(f"\nDeidentified Text Preview ({len(deid_result.deidentified_text)} chars):")
    print("-" * 80)
    print(deid_result.deidentified_text[:500] + "...")
    print("-" * 80)

    filtering_result = await openai_service.filter_clinical_relevance(
        deidentified_text=deid_result.deidentified_text
    )

    provider_placeholder = filtering_result.get("provider_placeholder")
    service_date_placeholder = filtering_result.get("service_date_placeholder")
    encounter_type = filtering_result.get("encounter_type")

    print(f"\n✅ Encounter Type: {encounter_type}")
    print(f"✅ Provider Placeholder: {provider_placeholder}")
    print(f"✅ Service Date Placeholder: {service_date_placeholder}")

    # Step 3: Extract actual values from placeholders
    print("\n" + "=" * 80)
    print("STEP 3: EXTRACT ACTUAL VALUES FROM PLACEHOLDERS")
    print("=" * 80)

    provider_name = None
    provider_initials = None
    service_date = None

    if provider_placeholder:
        provider_mapping = next(
            (m for m in deid_result.phi_mappings if m.token == f"[{provider_placeholder}]"),
            None
        )
        if provider_mapping:
            provider_name = provider_mapping.original
            name_parts = provider_name.split()
            if len(name_parts) >= 2:
                provider_initials = ''.join([part[0].upper() for part in name_parts[:2] if part])

            print(f"\nProvider Mapping Found:")
            print(f"  Placeholder: [{provider_placeholder}]")
            print(f"  Actual Name: {provider_name}")
            print(f"  Initials: {provider_initials}")

    if service_date_placeholder:
        date_mapping = next(
            (m for m in deid_result.phi_mappings if m.token == f"[{service_date_placeholder}]"),
            None
        )
        if date_mapping:
            service_date = date_mapping.original
            print(f"\nService Date Mapping Found:")
            print(f"  Placeholder: [{service_date_placeholder}]")
            print(f"  Actual Date: {service_date}")

    # Validation
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)

    print("\nExpected Results:")
    print("  Provider Initials: NT (Nancy Turner)")
    print("  Date of Service: June 5, 2025")
    print("  Encounter Type: well child visit")

    print("\nActual Results:")
    print(f"  Provider Initials: {provider_initials or 'NOT FOUND'} {'✅' if provider_initials == 'NT' else '❌'}")
    print(f"  Date of Service: {service_date or 'NOT FOUND'} {'✅' if service_date and 'June 5, 2025' in service_date else '❌'}")
    print(f"  Encounter Type: {encounter_type or 'NOT FOUND'} {'✅' if encounter_type and 'well child' in encounter_type.lower() else '❌'}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
