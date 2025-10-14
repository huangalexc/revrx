#!/usr/bin/env python3
"""Extract encounter IDs from Andrea's FHIR bundle"""

import json

# Load the bundle
with open('/Users/alexander/code/revrx/synthetic_data/synthea_fhir4_100/Andrea7_Mercado213_77300ca5-921f-f1ac-1653-5fbfd2ff31ef.json', 'r') as f:
    bundle = json.load(f)

# Extract encounters
encounters = []
for entry in bundle.get('entry', []):
    resource = entry.get('resource', {})
    if resource.get('resourceType') == 'Encounter':
        enc_id = resource.get('id')
        period = resource.get('period', {})
        start = period.get('start', 'Unknown')
        enc_type = 'Unknown'
        if resource.get('type'):
            for type_entry in resource.get('type', []):
                for coding in type_entry.get('coding', []):
                    enc_type = coding.get('display', 'Unknown')
                    break
                if enc_type != 'Unknown':
                    break
        encounters.append({
            'id': enc_id,
            'date': start[:10] if len(start) >= 10 else start,
            'type': enc_type
        })

# Sort by date and take first 10
encounters.sort(key=lambda x: x['date'])
encounters = encounters[:10]

print(f'Found {len(encounters)} encounters:')
for i, enc in enumerate(encounters, 1):
    print(f'{i:2d}. {enc["date"]} | {enc["type"]} | ID: {enc["id"]}')
