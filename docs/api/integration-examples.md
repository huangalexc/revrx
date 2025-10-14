# API Integration Examples

Complete code examples for integrating with the RevRx API.

## Table of Contents

- [Python Examples](#python-examples)
- [JavaScript Examples](#javascript-examples)
- [Webhook Integration](#webhook-integration)
- [Common Workflows](#common-workflows)

## Python Examples

### Basic Setup

```python
from revrx import RevRxClient

# Initialize client
client = RevRxClient(api_key="revx_your_api_key_here")
```

### Submit and Poll for Results

```python
import time
from revrx import RevRxClient

client = RevRxClient(api_key="revx_...")

# Submit encounter
encounter = client.encounters.submit(
    clinical_note="""
    Chief Complaint: Chest pain

    HPI: 45 year old male presents with chest pain onset 2 hours ago.
    Pain described as pressure, radiating to left arm. Associated with
    shortness of breath and diaphoresis.

    Physical Exam: BP 150/90, HR 110, RR 22, O2 Sat 95% on RA
    Cardiac: Tachycardic, regular rhythm, no murmurs
    Lungs: Clear to auscultation bilaterally

    Assessment/Plan:
    1. Acute chest pain, concerning for ACS
    2. ECG ordered - shows ST elevation in V2-V4
    3. Troponin elevated at 2.5
    4. Cardiology consulted, patient to cath lab
    """,
    billed_codes=[
        {"type": "CPT", "code": "99285"},  # ER visit
        {"type": "CPT", "code": "93000"},  # ECG
        {"type": "ICD10", "code": "R07.9"} # Chest pain
    ],
    patient_age=45,
    patient_sex="M",
    visit_date="2024-01-15T14:30:00Z"
)

print(f"Encounter ID: {encounter.id}")
print(f"Status: {encounter.status}")

# Poll for completion
while encounter.status in ["PENDING", "PROCESSING"]:
    time.sleep(5)
    encounter = client.encounters.get(encounter.id)
    print(f"Status: {encounter.status}")

if encounter.status == "COMPLETED":
    # Get report
    report = client.reports.get(encounter.id)

    print(f"\nOriginal Billing:")
    for code in report.billed_codes:
        print(f"  {code['type']}: {code['code']}")

    print(f"\nSuggested Additional Codes:")
    for suggestion in report.suggested_codes:
        print(f"  {suggestion['code']}: {suggestion['description']}")
        print(f"    Justification: {suggestion['justification']}")
        print(f"    Revenue: ${suggestion['estimated_revenue']}")

    print(f"\nTotal Incremental Revenue: ${report.incremental_revenue}")
else:
    print(f"Processing failed: {encounter.error_message}")
```

### Batch Processing

```python
from revrx import RevRxClient
import csv

client = RevRxClient(api_key="revx_...")

# Read encounters from CSV
encounters = []
with open('encounters.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        encounter = client.encounters.submit(
            clinical_note=row['clinical_note'],
            billed_codes=[
                {"type": "CPT", "code": code}
                for code in row['cpt_codes'].split(',')
            ],
            patient_age=int(row['age']),
            patient_sex=row['sex']
        )
        encounters.append(encounter)
        print(f"Submitted: {encounter.id}")

print(f"Submitted {len(encounters)} encounters")

# Later, retrieve results
for encounter_id in [e.id for e in encounters]:
    try:
        report = client.reports.get(encounter_id)
        print(f"{encounter_id}: ${report.incremental_revenue}")
    except NotFoundError:
        print(f"{encounter_id}: Still processing...")
```

### Error Handling

```python
from revrx import (
    RevRxClient,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NotFoundError,
    RevRxError
)
import time

client = RevRxClient(api_key="revx_...")

def submit_with_retry(clinical_note, billed_codes, max_retries=3):
    """Submit encounter with automatic retry on rate limits"""
    for attempt in range(max_retries):
        try:
            return client.encounters.submit(
                clinical_note=clinical_note,
                billed_codes=billed_codes
            )

        except RateLimitError as e:
            if attempt < max_retries - 1:
                print(f"Rate limited. Waiting {e.retry_after}s...")
                time.sleep(int(e.retry_after))
            else:
                raise

        except ValidationError as e:
            print(f"Validation error: {e.message}")
            print(f"Details: {e.response}")
            raise

        except AuthenticationError:
            print("Invalid API key!")
            raise

        except RevRxError as e:
            print(f"API error: {e.message} (status: {e.status_code})")
            raise

# Use it
try:
    encounter = submit_with_retry(
        clinical_note="...",
        billed_codes=[{"type": "CPT", "code": "99213"}]
    )
except Exception as e:
    print(f"Failed to submit: {e}")
```

## JavaScript Examples

### Basic Setup

```javascript
const { RevRxClient } = require('@revrx/sdk');

// Initialize client
const client = new RevRxClient({
  apiKey: 'revx_your_api_key_here'
});
```

### Submit and Poll for Results

```javascript
const { RevRxClient } = require('@revrx/sdk');

const client = new RevRxClient({ apiKey: 'revx_...' });

async function processEncounter() {
  // Submit encounter
  const encounter = await client.encounters.submit({
    clinicalNote: `
      Chief Complaint: Chest pain

      HPI: 45 year old male presents with chest pain onset 2 hours ago.
      Pain described as pressure, radiating to left arm. Associated with
      shortness of breath and diaphoresis.

      Physical Exam: BP 150/90, HR 110, RR 22, O2 Sat 95% on RA
      Cardiac: Tachycardic, regular rhythm, no murmurs
      Lungs: Clear to auscultation bilaterally

      Assessment/Plan:
      1. Acute chest pain, concerning for ACS
      2. ECG ordered - shows ST elevation in V2-V4
      3. Troponin elevated at 2.5
      4. Cardiology consulted, patient to cath lab
    `,
    billedCodes: [
      { type: 'CPT', code: '99285' },  // ER visit
      { type: 'CPT', code: '93000' },  // ECG
      { type: 'ICD10', code: 'R07.9' } // Chest pain
    ],
    patientAge: 45,
    patientSex: 'M',
    visitDate: '2024-01-15T14:30:00Z'
  });

  console.log(`Encounter ID: ${encounter.id}`);
  console.log(`Status: ${encounter.status}`);

  // Poll for completion
  let updated = encounter;
  while (['PENDING', 'PROCESSING'].includes(updated.status)) {
    await new Promise(resolve => setTimeout(resolve, 5000));
    updated = await client.encounters.get(encounter.id);
    console.log(`Status: ${updated.status}`);
  }

  if (updated.status === 'COMPLETED') {
    // Get report
    const report = await client.reports.get(encounter.id);

    console.log('\nOriginal Billing:');
    report.billedCodes.forEach(code => {
      console.log(`  ${code.type}: ${code.code}`);
    });

    console.log('\nSuggested Additional Codes:');
    report.suggestedCodes.forEach(suggestion => {
      console.log(`  ${suggestion.code}: ${suggestion.description}`);
      console.log(`    Justification: ${suggestion.justification}`);
      console.log(`    Revenue: $${suggestion.estimatedRevenue}`);
    });

    console.log(`\nTotal Incremental Revenue: $${report.incrementalRevenue}`);
  } else {
    console.log(`Processing failed: ${updated.errorMessage}`);
  }
}

processEncounter().catch(console.error);
```

### Batch Processing with Promise.all

```javascript
const { RevRxClient } = require('@revrx/sdk');
const fs = require('fs').promises;
const csv = require('csv-parse/sync');

const client = new RevRxClient({ apiKey: 'revx_...' });

async function batchProcess() {
  // Read encounters from CSV
  const csvContent = await fs.readFile('encounters.csv', 'utf-8');
  const records = csv.parse(csvContent, { columns: true });

  // Submit all encounters in parallel (respecting rate limits)
  const encounters = await Promise.all(
    records.map(async (row) => {
      try {
        const encounter = await client.encounters.submit({
          clinicalNote: row.clinical_note,
          billedCodes: row.cpt_codes.split(',').map(code => ({
            type: 'CPT',
            code: code.trim()
          })),
          patientAge: parseInt(row.age),
          patientSex: row.sex
        });
        console.log(`Submitted: ${encounter.id}`);
        return encounter;
      } catch (error) {
        console.error(`Failed to submit row: ${error.message}`);
        return null;
      }
    })
  );

  const successful = encounters.filter(e => e !== null);
  console.log(`Successfully submitted ${successful.length} encounters`);

  return successful;
}

batchProcess().catch(console.error);
```

### Error Handling with Async/Await

```javascript
const {
  RevRxClient,
  AuthenticationError,
  RateLimitError,
  ValidationError,
  NotFoundError,
  RevRxError
} = require('@revrx/sdk');

const client = new RevRxClient({ apiKey: 'revx_...' });

async function submitWithRetry(clinicalNote, billedCodes, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await client.encounters.submit({
        clinicalNote,
        billedCodes
      });
    } catch (error) {
      if (error instanceof RateLimitError) {
        if (attempt < maxRetries - 1) {
          console.log(`Rate limited. Waiting ${error.retryAfter}s...`);
          await new Promise(resolve => setTimeout(resolve, error.retryAfter * 1000));
          continue;
        }
      } else if (error instanceof ValidationError) {
        console.error(`Validation error: ${error.message}`);
        console.error(`Details:`, error.response);
        throw error;
      } else if (error instanceof AuthenticationError) {
        console.error('Invalid API key!');
        throw error;
      } else if (error instanceof RevRxError) {
        console.error(`API error: ${error.message} (status: ${error.statusCode})`);
        throw error;
      }

      throw error;
    }
  }
}

// Use it
submitWithRetry(
  'Clinical note...',
  [{ type: 'CPT', code: '99213' }]
)
  .then(encounter => console.log(`Success: ${encounter.id}`))
  .catch(error => console.error(`Failed: ${error.message}`));
```

## Webhook Integration

### Express.js Webhook Handler

```javascript
const express = require('express');
const { RevRxClient } = require('@revrx/sdk');

const app = express();
const client = new RevRxClient({ apiKey: process.env.REVRX_API_KEY });
const WEBHOOK_SECRET = process.env.REVRX_WEBHOOK_SECRET;

// Important: Use raw body for signature verification
app.post('/webhooks/revrx',
  express.raw({ type: 'application/json' }),
  async (req, res) => {
    const signature = req.headers['x-webhook-signature'];
    const payload = req.body.toString('utf8');

    // Verify signature
    if (!client.webhooks.verifySignature(payload, signature, WEBHOOK_SECRET)) {
      console.error('Invalid webhook signature');
      return res.status(401).json({ error: 'Invalid signature' });
    }

    const event = JSON.parse(payload);
    console.log(`Received event: ${event.event}`);

    try {
      switch (event.event) {
        case 'encounter.completed':
          await handleEncounterCompleted(event.data);
          break;

        case 'encounter.failed':
          await handleEncounterFailed(event.data);
          break;

        default:
          console.log(`Unknown event type: ${event.event}`);
      }

      res.json({ status: 'ok' });
    } catch (error) {
      console.error('Error handling webhook:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }
);

async function handleEncounterCompleted(data) {
  const { encounter_id } = data;
  console.log(`Encounter completed: ${encounter_id}`);

  // Fetch full report
  const report = await client.reports.get(encounter_id);

  // Process results (e.g., update your database)
  console.log(`Incremental revenue: $${report.incrementalRevenue}`);
  console.log(`Suggested codes: ${report.suggestedCodes.length}`);

  // Update your system
  // await updateEncounterInDatabase(encounter_id, report);
}

async function handleEncounterFailed(data) {
  const { encounter_id, error } = data;
  console.error(`Encounter failed: ${encounter_id}`, error);

  // Handle failure (e.g., notify user, log error)
  // await notifyUserOfFailure(encounter_id, error);
}

app.listen(3000, () => {
  console.log('Webhook server listening on port 3000');
});
```

### Flask Webhook Handler (Python)

```python
from flask import Flask, request, jsonify
import hmac
import hashlib
from revrx import RevRxClient

app = Flask(__name__)
client = RevRxClient(api_key=os.environ['REVRX_API_KEY'])
WEBHOOK_SECRET = os.environ['REVRX_WEBHOOK_SECRET']

def verify_signature(payload: str, signature: str) -> bool:
    """Verify webhook signature"""
    expected = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.route('/webhooks/revrx', methods=['POST'])
def handle_webhook():
    signature = request.headers.get('X-Webhook-Signature')
    payload = request.get_data(as_text=True)

    # Verify signature
    if not verify_signature(payload, signature):
        return jsonify({'error': 'Invalid signature'}), 401

    event = request.json
    print(f"Received event: {event['event']}")

    try:
        if event['event'] == 'encounter.completed':
            handle_encounter_completed(event['data'])
        elif event['event'] == 'encounter.failed':
            handle_encounter_failed(event['data'])
        else:
            print(f"Unknown event type: {event['event']}")

        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Error handling webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def handle_encounter_completed(data):
    encounter_id = data['encounter_id']
    print(f"Encounter completed: {encounter_id}")

    # Fetch full report
    report = client.reports.get(encounter_id)

    # Process results
    print(f"Incremental revenue: ${report.incremental_revenue}")
    print(f"Suggested codes: {len(report.suggested_codes)}")

    # Update your system
    # update_encounter_in_database(encounter_id, report)

def handle_encounter_failed(data):
    encounter_id = data['encounter_id']
    error = data.get('error')
    print(f"Encounter failed: {encounter_id}", error)

    # Handle failure
    # notify_user_of_failure(encounter_id, error)

if __name__ == '__main__':
    app.run(port=3000)
```

## Common Workflows

### Complete Integration Flow

```python
from revrx import RevRxClient
import time

client = RevRxClient(api_key="revx_...")

# 1. Create API key for programmatic access
api_key = client.api_keys.create(
    name="Production Server",
    rate_limit=100,
    expires_in_days=365
)
print(f"Save this API key: {api_key.key}")

# 2. Create webhook for notifications
webhook = client.webhooks.create(
    url="https://your-app.com/webhooks/revrx",
    events=[
        "encounter.completed",
        "encounter.failed"
    ]
)
print(f"Save this webhook secret: {webhook.secret}")

# 3. Submit encounters
encounter = client.encounters.submit(
    clinical_note="...",
    billed_codes=[{"type": "CPT", "code": "99213"}]
)

# 4. Your webhook will receive notification when complete
# Or poll for results:
while encounter.status in ["PENDING", "PROCESSING"]:
    time.sleep(5)
    encounter = client.encounters.get(encounter.id)

if encounter.status == "COMPLETED":
    report = client.reports.get(encounter.id)
    print(f"Revenue opportunity: ${report.incremental_revenue}")
```

### Managing Multiple Webhooks

```python
from revrx import RevRxClient

client = RevRxClient(api_key="revx_...")

# Create separate webhooks for different environments
webhooks = {
    "production": client.webhooks.create(
        url="https://api.prod.com/webhooks/revrx",
        events=["encounter.completed", "encounter.failed"]
    ),
    "staging": client.webhooks.create(
        url="https://api.staging.com/webhooks/revrx",
        events=["encounter.completed", "encounter.failed"]
    )
}

# Disable staging webhook
client.webhooks.update(
    webhooks["staging"].id,
    is_active=False
)

# Monitor webhook health
for name, webhook in webhooks.items():
    deliveries = client.webhooks.list_deliveries(webhook.id, limit=10)
    success_rate = sum(1 for d in deliveries if d.status == "DELIVERED") / len(deliveries)
    print(f"{name}: {success_rate*100}% success rate")
```

## Best Practices

### 1. Rate Limit Handling

Always implement exponential backoff when rate limited:

```python
import time

def exponential_backoff_retry(func, max_retries=5):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            wait_time = (2 ** attempt) + int(e.retry_after or 0)
            time.sleep(wait_time)
```

### 2. Webhook Reliability

Implement idempotency in webhook handlers:

```python
processed_events = set()

def handle_webhook(event_id, event_data):
    if event_id in processed_events:
        return  # Already processed

    # Process event
    process_event(event_data)

    # Mark as processed
    processed_events.add(event_id)
```

### 3. Error Logging

Log all API errors for debugging:

```python
import logging

logger = logging.getLogger(__name__)

try:
    encounter = client.encounters.submit(...)
except RevRxError as e:
    logger.error(
        "Failed to submit encounter",
        extra={
            "status_code": e.status_code,
            "message": e.message,
            "response": e.response
        }
    )
    raise
```

## Support

For more examples and integration help:
- API Documentation: https://docs.revrx.com
- SDK Documentation: https://docs.revrx.com/sdks
- Support: support@revrx.com
