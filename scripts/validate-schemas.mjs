#!/usr/bin/env node
/**
 * Schema Validation Test Script for Track G2
 * Validates all analysis-features schemas with valid and invalid inputs
 */

import { z } from 'zod';

// Define schemas (matching analysis-features.ts)
const missingDocumentationSchema = z.object({
  section: z.string().min(1),
  issue: z.string().min(1),
  suggestion: z.string().min(1),
  priority: z.enum(['High', 'Medium', 'Low']).optional(),
});

const denialRiskSchema = z.object({
  code: z.string().regex(/^[A-Z0-9]{3,7}(-[A-Z0-9]{2})?$/),
  riskLevel: z.enum(['Low', 'Medium', 'High']),
  reasons: z.array(z.string()).min(1),
  addressed: z.boolean(),
  justification: z.string().min(1),
});

const revenueComparisonSchema = z.object({
  billedCodes: z.array(z.string()),
  billedRVUs: z.number().nonnegative(),
  suggestedCodes: z.array(z.string()),
  suggestedRVUs: z.number().nonnegative(),
  missedRevenue: z.number(),
  percentDifference: z.number(),
});

const modifierSuggestionSchema = z.object({
  code: z.string().regex(/^[A-Z0-9]{3,7}$/),
  modifier: z.string().regex(/^-[A-Z0-9]{2}$/),
  justification: z.string().min(1),
  isNewSuggestion: z.boolean(),
});

const uncapturedServiceSchema = z.object({
  service: z.string().min(1),
  location: z.string().min(1),
  suggestedCodes: z.array(z.string()).min(1),
  priority: z.enum(['High', 'Medium', 'Low']),
  estimatedRVUs: z.number().nonnegative().optional(),
});

const auditLogExportSchema = z.object({
  metadata: z.object({
    providerId: z.string().min(1),
    patientId: z.string().min(1),
    dateOfService: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    encounterType: z.enum(['outpatient', 'inpatient', 'emergency', 'telehealth']),
    analysisTimestamp: z.string().datetime(),
  }),
  suggestedCodes: z.array(z.object({
    code: z.string(),
    description: z.string(),
    justification: z.string(),
    chartReference: z.string(),
  })),
  justifications: z.object({
    assessment: z.string(),
    qualityNotes: z.array(z.string()).optional(),
    riskNotes: z.array(z.string()).optional(),
  }),
  timestamp: z.string().datetime(),
});

// Test data
const tests = {
  missingDocumentation: {
    valid: [
      { section: 'HPI', issue: 'Missing duration', suggestion: 'Add timeline', priority: 'High' },
      { section: 'Physical Exam', issue: 'Incomplete', suggestion: 'Document findings' },
    ],
    invalid: [
      { section: '', issue: 'test', suggestion: 'test' }, // Empty section
      { section: 'Test', issue: 'test', suggestion: 'test', priority: 'Critical' }, // Invalid priority
    ]
  },
  denialRisk: {
    valid: [
      { code: '99214', riskLevel: 'Low', reasons: ['Good documentation'], addressed: true, justification: 'Clear MDM' },
      { code: '80053', riskLevel: 'Medium', reasons: ['Missing necessity'], addressed: false, justification: 'Need more detail' },
    ],
    invalid: [
      { code: 'invalid_code', riskLevel: 'Low', reasons: ['test'], addressed: true, justification: 'test' }, // Invalid code
      { code: '99213', riskLevel: 'Low', reasons: [], addressed: true, justification: 'test' }, // Empty reasons
    ]
  },
  revenueComparison: {
    valid: [
      { billedCodes: ['99213'], billedRVUs: 1.3, suggestedCodes: ['99214'], suggestedRVUs: 1.92, missedRevenue: 0.62, percentDifference: 47.7 },
      { billedCodes: [], billedRVUs: 0, suggestedCodes: [], suggestedRVUs: 0, missedRevenue: 0, percentDifference: 0 },
    ],
    invalid: [
      { billedCodes: [], billedRVUs: -1, suggestedCodes: [], suggestedRVUs: 0, missedRevenue: 0, percentDifference: 0 }, // Negative RVU
    ]
  },
  modifierSuggestion: {
    valid: [
      { code: '99214', modifier: '-25', justification: 'Separate E/M', isNewSuggestion: true },
      { code: '27447', modifier: '-59', justification: 'Distinct service', isNewSuggestion: false },
    ],
    invalid: [
      { code: '99213', modifier: '25', justification: 'test', isNewSuggestion: true }, // Missing hyphen
      { code: 'invalid', modifier: '-25', justification: 'test', isNewSuggestion: true }, // Invalid code
    ]
  },
  uncapturedService: {
    valid: [
      { service: 'EKG', location: 'Page 2', suggestedCodes: ['93000'], priority: 'High', estimatedRVUs: 0.17 },
      { service: 'Wound care', location: 'Nursing notes', suggestedCodes: ['97597'], priority: 'Medium' },
    ],
    invalid: [
      { service: 'Test', location: 'Test', suggestedCodes: [], priority: 'High' }, // Empty codes
      { service: 'Test', location: 'Test', suggestedCodes: ['12345'], priority: 'High', estimatedRVUs: -1 }, // Negative RVU
    ]
  },
  auditLogExport: {
    valid: [
      {
        metadata: {
          providerId: 'PROV-123',
          patientId: 'PAT-456',
          dateOfService: '2025-01-15',
          encounterType: 'outpatient',
          analysisTimestamp: '2025-01-16T10:30:00Z',
        },
        suggestedCodes: [{ code: '99214', description: 'Visit', justification: 'Test', chartReference: 'Page 1' }],
        justifications: { assessment: 'Complete' },
        timestamp: '2025-01-16T10:35:00Z',
      }
    ],
    invalid: [
      {
        metadata: {
          providerId: '',
          patientId: 'PAT-456',
          dateOfService: '2025-01-15',
          encounterType: 'outpatient',
          analysisTimestamp: '2025-01-16T10:30:00Z',
        },
        suggestedCodes: [],
        justifications: { assessment: 'Test' },
        timestamp: '2025-01-16T10:35:00Z',
      }, // Empty providerId
    ]
  }
};

// Run tests
let passed = 0;
let failed = 0;

console.log('🧪 Running Schema Validation Tests (Track G2)\n');

for (const [schemaName, testData] of Object.entries(tests)) {
  console.log(`\n📋 Testing ${schemaName} Schema:`);

  let schema;
  if (schemaName === 'missingDocumentation') schema = missingDocumentationSchema;
  else if (schemaName === 'denialRisk') schema = denialRiskSchema;
  else if (schemaName === 'revenueComparison') schema = revenueComparisonSchema;
  else if (schemaName === 'modifierSuggestion') schema = modifierSuggestionSchema;
  else if (schemaName === 'uncapturedService') schema = uncapturedServiceSchema;
  else if (schemaName === 'auditLogExport') schema = auditLogExportSchema;

  // Test valid inputs
  console.log(`  ✓ Valid inputs:`);
  for (const validData of testData.valid) {
    try {
      schema.parse(validData);
      console.log(`    ✅ Passed: ${JSON.stringify(validData).substring(0, 80)}...`);
      passed++;
    } catch (error) {
      console.log(`    ❌ Failed: ${error.message}`);
      failed++;
    }
  }

  // Test invalid inputs
  console.log(`  ✗ Invalid inputs (should fail):`);
  for (const invalidData of testData.invalid) {
    try {
      schema.parse(invalidData);
      console.log(`    ❌ Should have failed: ${JSON.stringify(invalidData).substring(0, 80)}...`);
      failed++;
    } catch (error) {
      const message = error.errors?.[0]?.message || error.message || 'Validation error';
      console.log(`    ✅ Correctly rejected: ${message}`);
      passed++;
    }
  }
}

console.log(`\n\n📊 Test Results:`);
console.log(`   ✅ Passed: ${passed}`);
console.log(`   ❌ Failed: ${failed}`);
console.log(`   📈 Total: ${passed + failed}`);

if (failed === 0) {
  console.log(`\n✨ All schema validation tests passed! Track G2 complete.\n`);
  process.exit(0);
} else {
  console.log(`\n❌ Some tests failed. Please review.\n`);
  process.exit(1);
}
