"""
Extract 20 encounters from Antione's FHIR bundle for async testing
"""

import json
from pathlib import Path

BUNDLE_PATH = "/Users/alexander/code/revrx/synthetic_data/synthea_fhir4_100/Antione404_Mayert710_ed57974f-3241-3504-ad70-4ea38bb549e5.json"
OUTPUT_PATH = "/tmp/antione_20_encounters.json"

def extract_encounters():
    """Extract first 20 encounters from Antione's bundle"""

    with open(BUNDLE_PATH, 'r') as f:
        bundle = json.load(f)

    # Find all encounter resources
    encounters = []
    for entry in bundle.get('entry', []):
        resource = entry.get('resource', {})
        if resource.get('resourceType') == 'Encounter':
            # Extract encounter metadata
            encounter_id = resource.get('id')
            period = resource.get('period', {})
            start_date = period.get('start', 'Unknown')
            reason_code = resource.get('reasonCode', [{}])[0].get('coding', [{}])[0].get('display', 'Unknown')

            encounters.append({
                'id': encounter_id,
                'date': start_date,
                'reason': reason_code,
                'resource': resource
            })

    # Sort by date and take first 20
    encounters.sort(key=lambda x: x['date'])
    selected = encounters[:20]

    # Save metadata
    with open(OUTPUT_PATH, 'w') as f:
        json.dump([{
            'id': e['id'],
            'date': e['date'],
            'reason': e['reason']
        } for e in selected], f, indent=2)

    print(f"Extracted {len(selected)} encounters from Antione's bundle")
    print(f"Date range: {selected[0]['date']} to {selected[-1]['date']}")
    print(f"\nSaved to: {OUTPUT_PATH}")

    # Print summary
    print("\nEncounters:")
    for i, enc in enumerate(selected, 1):
        print(f"{i:2d}. {enc['date'][:10]} | {enc['reason']}")

    return selected

if __name__ == "__main__":
    extract_encounters()
