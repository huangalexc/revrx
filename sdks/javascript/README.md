# RevRx JavaScript SDK

Official JavaScript/Node.js client library for the Post-Facto Coding Review API.

## Installation

```bash
npm install @revrx/sdk
```

## Quick Start

```javascript
const { RevRxClient } = require('@revrx/sdk');

// Initialize client with API key
const client = new RevRxClient({
  apiKey: 'revx_...'
});

// Submit encounter for analysis
const encounter = await client.encounters.submit({
  clinicalNote: 'Patient presents with chest pain...',
  billedCodes: [
    { type: 'CPT', code: '99213' },
    { type: 'ICD10', code: 'R07.9' }
  ],
  patientAge: 45,
  patientSex: 'M',
  visitDate: '2024-01-15'
});

console.log(`Encounter submitted: ${encounter.id}`);
console.log(`Status: ${encounter.status}`);

// Get report when processing is complete
const report = await client.reports.get(encounter.id);
console.log(`Incremental revenue: $${report.incrementalRevenue}`);
console.log(`Suggested codes: ${report.suggestedCodes.length}`);
```

## Authentication

Get your API key from the RevRx dashboard:

```javascript
const client = new RevRxClient({
  apiKey: 'revx_your_api_key_here'
});
```

## Encounters

### Submit Encounter

```javascript
const encounter = await client.encounters.submit({
  clinicalNote: 'Patient documentation...',
  billedCodes: [
    { type: 'CPT', code: '99213' }
  ],
  patientAge: 45,
  patientSex: 'M'
});
```

### Get Encounter

```javascript
const encounter = await client.encounters.get('encounter_id');
console.log(encounter.status); // PENDING, PROCESSING, COMPLETED, FAILED
```

### List Encounters

```javascript
const encounters = await client.encounters.list({ limit: 50, offset: 0 });
encounters.forEach(encounter => {
  console.log(`${encounter.id}: ${encounter.status}`);
});
```

## Reports

### Get Report

```javascript
const report = await client.reports.get('encounter_id');

// Billed codes
report.billedCodes.forEach(code => {
  console.log(`${code.type}: ${code.code}`);
});

// Suggested additional codes
report.suggestedCodes.forEach(suggestion => {
  console.log(`${suggestion.code}: ${suggestion.justification}`);
  console.log(`Revenue: $${suggestion.estimatedRevenue}`);
});

// Total incremental revenue
console.log(`Total additional revenue: $${report.incrementalRevenue}`);
```

## Webhooks

### Create Webhook

```javascript
const webhook = await client.webhooks.create({
  url: 'https://your-app.com/webhooks/revrx',
  events: [
    'encounter.completed',
    'encounter.failed'
  ]
});

// Save the secret for signature verification
console.log(`Webhook secret: ${webhook.secret}`);
```

### List Webhooks

```javascript
const webhooks = await client.webhooks.list();
webhooks.forEach(webhook => {
  console.log(`${webhook.url}: ${webhook.isActive}`);
});
```

### Update Webhook

```javascript
const webhook = await client.webhooks.update('webhook_id', {
  isActive: false
});
```

### Verify Webhook Signature (Express Example)

```javascript
const express = require('express');
const { RevRxClient } = require('@revrx/sdk');

const app = express();
const client = new RevRxClient({ apiKey: 'revx_...' });

app.post('/webhooks/revrx', express.raw({ type: 'application/json' }), (req, res) => {
  const signature = req.headers['x-webhook-signature'];
  const payload = req.body.toString('utf8');

  // Verify signature
  const isValid = client.webhooks.verifySignature(
    payload,
    signature,
    process.env.WEBHOOK_SECRET
  );

  if (!isValid) {
    return res.status(401).json({ error: 'Invalid signature' });
  }

  const data = JSON.parse(payload);
  console.log(`Event: ${data.event}`);
  console.log(`Encounter: ${data.data.encounter_id}`);

  res.json({ status: 'ok' });
});
```

### Get Webhook Deliveries

```javascript
const deliveries = await client.webhooks.listDeliveries('webhook_id', {
  limit: 50,
  offset: 0
});

deliveries.forEach(delivery => {
  console.log(`${delivery.event}: ${delivery.status}`);
  if (delivery.error) {
    console.log(`Error: ${delivery.error}`);
  }
});
```

## API Keys

### Create API Key

```javascript
const apiKey = await client.apiKeys.create({
  name: 'Production Server',
  rateLimit: 100,
  expiresInDays: 365
});

// IMPORTANT: Save the key now - it's only shown once
console.log(`API Key: ${apiKey.key}`);
console.log(`Key ID: ${apiKey.id}`);
```

### List API Keys

```javascript
const keys = await client.apiKeys.list();
keys.forEach(key => {
  console.log(`${key.name}: ${key.keyPrefix}...`);
  console.log(`Usage: ${key.usageCount} requests`);
});
```

### Update API Key

```javascript
const apiKey = await client.apiKeys.update('key_id', {
  isActive: false
});
```

## Error Handling

```javascript
const {
  RevRxClient,
  RevRxError,
  AuthenticationError,
  RateLimitError,
  ValidationError,
  NotFoundError
} = require('@revrx/sdk');

try {
  const encounter = await client.encounters.submit({...});
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error('Invalid API key');
  } else if (error instanceof RateLimitError) {
    console.error(`Rate limit exceeded. Retry after ${error.retryAfter}s`);
  } else if (error instanceof ValidationError) {
    console.error(`Validation error: ${error.message}`);
  } else if (error instanceof NotFoundError) {
    console.error('Resource not found');
  } else if (error instanceof RevRxError) {
    console.error(`API error: ${error.message}`);
  } else {
    console.error(`Unexpected error: ${error.message}`);
  }
}
```

## TypeScript Support

Type definitions are included:

```typescript
import { RevRxClient, Encounter, Report } from '@revrx/sdk';

const client = new RevRxClient({
  apiKey: 'revx_...'
});

const encounter: Encounter = await client.encounters.submit({
  clinicalNote: '...',
  billedCodes: [{ type: 'CPT', code: '99213' }]
});
```

## Configuration Options

```javascript
const client = new RevRxClient({
  apiKey: 'revx_...',              // Required
  baseUrl: 'https://api.revrx.com/api/v1',  // Optional (default: production)
  timeout: 30000                    // Optional (default: 30s)
});
```

## Rate Limiting

API key requests are rate limited. Access rate limit info from the response:

```javascript
try {
  await client.encounters.submit({...});
} catch (error) {
  if (error instanceof RateLimitError) {
    console.log(`Limit: ${error.limit}`);
    console.log(`Remaining: ${error.remaining}`);
    console.log(`Reset: ${error.reset}`);
    console.log(`Retry after: ${error.retryAfter}s`);
  }
}
```

## Development

```bash
# Install dependencies
npm install

# Run tests
npm test

# Lint code
npm run lint
```

## Support

- Documentation: https://docs.revrx.com
- API Reference: https://api.revrx.com/docs
- Issues: https://github.com/revrx/revrx-javascript/issues
- Email: support@revrx.com

## License

Proprietary - See LICENSE file for details
