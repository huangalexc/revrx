# RevRx Python SDK

Official Python client library for the Post-Facto Coding Review API.

## Installation

```bash
pip install revrx
```

## Quick Start

```python
from revrx import RevRxClient

# Initialize client with API key
client = RevRxClient(api_key="revx_...")

# Submit encounter for analysis
encounter = client.encounters.submit(
    clinical_note="Patient presents with chest pain...",
    billed_codes=[
        {"type": "CPT", "code": "99213"},
        {"type": "ICD10", "code": "R07.9"}
    ],
    patient_age=45,
    patient_sex="M",
    visit_date="2024-01-15"
)

print(f"Encounter submitted: {encounter.id}")
print(f"Status: {encounter.status}")

# Get report when processing is complete
report = client.reports.get(encounter.id)
print(f"Incremental revenue: ${report.incremental_revenue}")
print(f"Suggested codes: {len(report.suggested_codes)}")
```

## Authentication

Get your API key from the RevRx dashboard:

```python
client = RevRxClient(api_key="revx_your_api_key_here")
```

## Encounters

### Submit Encounter

```python
encounter = client.encounters.submit(
    clinical_note="Patient documentation...",
    billed_codes=[
        {"type": "CPT", "code": "99213"}
    ],
    patient_age=45,
    patient_sex="M"
)
```

### Get Encounter

```python
encounter = client.encounters.get("encounter_id")
print(encounter.status)  # PENDING, PROCESSING, COMPLETED, FAILED
```

### List Encounters

```python
encounters = client.encounters.list(limit=50, offset=0)
for encounter in encounters:
    print(f"{encounter.id}: {encounter.status}")
```

## Reports

### Get Report

```python
report = client.reports.get("encounter_id")

# Billed codes
for code in report.billed_codes:
    print(f"{code['type']}: {code['code']}")

# Suggested additional codes
for suggestion in report.suggested_codes:
    print(f"{suggestion['code']}: {suggestion['justification']}")
    print(f"Revenue: ${suggestion['estimated_revenue']}")

# Total incremental revenue
print(f"Total additional revenue: ${report.incremental_revenue}")
```

## Webhooks

### Create Webhook

```python
webhook = client.webhooks.create(
    url="https://your-app.com/webhooks/revrx",
    events=[
        "encounter.completed",
        "encounter.failed"
    ]
)

# Save the secret for signature verification
print(f"Webhook secret: {webhook.secret}")
```

### List Webhooks

```python
webhooks = client.webhooks.list()
for webhook in webhooks:
    print(f"{webhook.url}: {webhook.is_active}")
```

### Update Webhook

```python
webhook = client.webhooks.update(
    webhook_id="webhook_id",
    is_active=False
)
```

### Verify Webhook Signature

```python
import hmac
import hashlib

def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify webhook payload signature"""
    expected = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

# In your webhook handler
@app.post("/webhooks/revrx")
def handle_webhook(request):
    signature = request.headers.get("X-Webhook-Signature")
    payload = request.body.decode('utf-8')

    if not verify_webhook_signature(payload, signature, WEBHOOK_SECRET):
        return {"error": "Invalid signature"}, 401

    data = request.json()
    print(f"Event: {data['event']}")
    print(f"Encounter: {data['data']['encounter_id']}")

    return {"status": "ok"}
```

### Get Webhook Deliveries

```python
deliveries = client.webhooks.list_deliveries("webhook_id", limit=50)
for delivery in deliveries:
    print(f"{delivery.event}: {delivery.status}")
    if delivery.error:
        print(f"Error: {delivery.error}")
```

## API Keys

### Create API Key

```python
api_key = client.api_keys.create(
    name="Production Server",
    rate_limit=100,
    expires_in_days=365
)

# IMPORTANT: Save the key now - it's only shown once
print(f"API Key: {api_key.key}")
print(f"Key ID: {api_key.id}")
```

### List API Keys

```python
keys = client.api_keys.list()
for key in keys:
    print(f"{key.name}: {key.key_prefix}...")
    print(f"Usage: {key.usage_count} requests")
```

### Update API Key

```python
api_key = client.api_keys.update(
    api_key_id="key_id",
    is_active=False
)
```

## Error Handling

```python
from revrx import (
    RevRxError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NotFoundError
)

try:
    encounter = client.encounters.submit(...)
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limit exceeded. Retry after {e.retry_after}s")
except ValidationError as e:
    print(f"Validation error: {e.message}")
except NotFoundError:
    print("Resource not found")
except RevRxError as e:
    print(f"API error: {e.message}")
```

## Rate Limiting

API key requests are rate limited. Check response headers:

```python
response = client._client.last_response
print(f"Limit: {response.headers.get('X-RateLimit-Limit')}")
print(f"Remaining: {response.headers.get('X-RateLimit-Remaining')}")
print(f"Reset: {response.headers.get('X-RateLimit-Reset')}")
```

## Context Manager

Use the client as a context manager to ensure proper cleanup:

```python
with RevRxClient(api_key="revx_...") as client:
    encounter = client.encounters.submit(...)
    report = client.reports.get(encounter.id)
# Client is automatically closed
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black revrx/

# Type checking
mypy revrx/
```

## Support

- Documentation: https://docs.revrx.com
- API Reference: https://api.revrx.com/docs
- Issues: https://github.com/revrx/revrx-python/issues
- Email: support@revrx.com

## License

Proprietary - See LICENSE file for details
