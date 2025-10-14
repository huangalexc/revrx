/**
 * Zod validation schemas for extended analysis features
 *
 * These schemas validate data structures for:
 * - Documentation Quality Checks
 * - Denial Risk Prediction
 * - Revenue Comparison (Under-coding Detection)
 * - Modifier Suggestions
 * - Charge Capture
 * - Audit Log Export
 */

import { z } from 'zod';

// ============================================================================
// Documentation Quality Schemas
// ============================================================================

/**
 * Schema for missing documentation elements
 */
export const missingDocumentationSchema = z.object({
  section: z.string().min(1, 'Section is required'),
  issue: z.string().min(1, 'Issue description is required'),
  suggestion: z.string().min(1, 'Suggestion is required'),
  priority: z.enum(['High', 'Medium', 'Low']).optional(),
});

export const missingDocumentationArraySchema = z.array(missingDocumentationSchema);

export type MissingDocumentationFormData = z.infer<typeof missingDocumentationSchema>;

// ============================================================================
// Denial Risk Schemas
// ============================================================================

/**
 * Schema for denial risk level
 */
export const denialRiskLevelSchema = z.enum(['Low', 'Medium', 'High']);

/**
 * Schema for denial risk assessment
 */
export const denialRiskSchema = z.object({
  code: z.string().min(1, 'Code is required').regex(/^[A-Z0-9-]+$/, 'Invalid code format'),
  riskLevel: denialRiskLevelSchema,
  reasons: z.array(z.string()).min(1, 'At least one denial reason is required'),
  addressed: z.boolean(),
  justification: z.string().min(1, 'Justification is required'),
});

export const denialRiskArraySchema = z.array(denialRiskSchema);

export type DenialRiskFormData = z.infer<typeof denialRiskSchema>;

// ============================================================================
// Revenue Comparison Schemas
// ============================================================================

/**
 * Schema for revenue comparison analysis
 */
export const revenueComparisonSchema = z.object({
  billedCodes: z.array(z.string()).min(0),
  billedRVUs: z.number().min(0, 'Billed RVUs must be non-negative'),
  suggestedCodes: z.array(z.string()).min(0),
  suggestedRVUs: z.number().min(0, 'Suggested RVUs must be non-negative'),
  missedRevenue: z.number(), // Can be negative if over-coding
  percentDifference: z.number().min(-100).max(1000), // Reasonable bounds for percentage
});

export type RevenueComparisonFormData = z.infer<typeof revenueComparisonSchema>;

// ============================================================================
// Modifier Suggestion Schemas
// ============================================================================

/**
 * Common CPT modifiers validation
 */
const commonModifiers = [
  '-25', // Significant, separately identifiable E/M service
  '-59', // Distinct procedural service
  '-76', // Repeat procedure by same physician
  '-77', // Repeat procedure by another physician
  '-24', // Unrelated E/M service during postoperative period
  '-57', // Decision for surgery
  '-51', // Multiple procedures
  '-52', // Reduced services
  '-53', // Discontinued procedure
  '-91', // Repeat clinical diagnostic laboratory test
] as const;

/**
 * Schema for modifier suggestions
 */
export const modifierSuggestionSchema = z.object({
  code: z.string().min(1, 'Code is required').regex(/^[A-Z0-9-]+$/, 'Invalid code format'),
  modifier: z.string().regex(/^-\d{2}$/, 'Modifier must be in format -XX'),
  justification: z.string().min(1, 'Justification is required'),
  isNewSuggestion: z.boolean(),
});

export const modifierSuggestionArraySchema = z.array(modifierSuggestionSchema);

export type ModifierSuggestionFormData = z.infer<typeof modifierSuggestionSchema>;

// ============================================================================
// Uncaptured Service Schemas
// ============================================================================

/**
 * Schema for uncaptured service priority
 */
export const uncapturedServicePrioritySchema = z.enum(['High', 'Medium', 'Low']);

/**
 * Schema for uncaptured services (charge capture)
 */
export const uncapturedServiceSchema = z.object({
  service: z.string().min(1, 'Service description is required'),
  location: z.string().min(1, 'Chart location is required'),
  suggestedCodes: z.array(z.string()).min(1, 'At least one suggested code is required'),
  priority: uncapturedServicePrioritySchema,
  estimatedRVUs: z.number().min(0).optional(),
});

export const uncapturedServiceArraySchema = z.array(uncapturedServiceSchema);

export type UncapturedServiceFormData = z.infer<typeof uncapturedServiceSchema>;

// ============================================================================
// Audit Log Export Schemas
// ============================================================================

/**
 * Schema for audit log metadata
 */
export const auditLogMetadataSchema = z.object({
  providerId: z.string().min(1, 'Provider ID is required'),
  patientId: z.string().min(1, 'Patient ID is required'),
  dateOfService: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Date must be in YYYY-MM-DD format'),
  encounterType: z.enum(['inpatient', 'outpatient', 'emergency', 'urgent_care', 'telehealth', 'other']),
  analysisTimestamp: z.string().datetime('Invalid ISO datetime format'),
});

/**
 * Schema for suggested code with audit details
 */
export const auditSuggestedCodeSchema = z.object({
  code: z.string().min(1, 'Code is required'),
  description: z.string().min(1, 'Description is required'),
  justification: z.string().min(1, 'Justification is required'),
  chartReference: z.string().min(1, 'Chart reference is required'),
});

/**
 * Schema for audit log justifications
 */
export const auditJustificationsSchema = z.object({
  assessment: z.string().min(1, 'Overall assessment is required'),
  qualityNotes: z.array(z.string()).optional(),
  riskNotes: z.array(z.string()).optional(),
});

/**
 * Complete audit log export schema
 */
export const auditLogExportSchema = z.object({
  metadata: auditLogMetadataSchema,
  suggestedCodes: z.array(auditSuggestedCodeSchema),
  justifications: auditJustificationsSchema,
  timestamp: z.string().datetime('Invalid ISO datetime format'),
});

export type AuditLogExportFormData = z.infer<typeof auditLogExportSchema>;

// ============================================================================
// Extended Analysis Result Schema
// ============================================================================

/**
 * Schema for extended analysis result with all new features
 */
export const extendedAnalysisResultSchema = z.object({
  // Base analysis fields would be spread here from existing schema
  // For now, just the extended fields:

  missingDocumentation: missingDocumentationArraySchema.optional(),
  denialRisks: denialRiskArraySchema.optional(),
  revenueComparison: revenueComparisonSchema.optional(),
  modifierSuggestions: modifierSuggestionArraySchema.optional(),
  uncapturedServices: uncapturedServiceArraySchema.optional(),
  auditLog: auditLogExportSchema.optional(),
});

export type ExtendedAnalysisResultFormData = z.infer<typeof extendedAnalysisResultSchema>;

// ============================================================================
// Validation Helper Functions
// ============================================================================

/**
 * Validates missing documentation data
 */
export function validateMissingDocumentation(data: unknown) {
  return missingDocumentationArraySchema.parse(data);
}

/**
 * Validates denial risk data
 */
export function validateDenialRisks(data: unknown) {
  return denialRiskArraySchema.parse(data);
}

/**
 * Validates revenue comparison data
 */
export function validateRevenueComparison(data: unknown) {
  return revenueComparisonSchema.parse(data);
}

/**
 * Validates modifier suggestions
 */
export function validateModifierSuggestions(data: unknown) {
  return modifierSuggestionArraySchema.parse(data);
}

/**
 * Validates uncaptured services
 */
export function validateUncapturedServices(data: unknown) {
  return uncapturedServiceArraySchema.parse(data);
}

/**
 * Validates audit log export data
 */
export function validateAuditLogExport(data: unknown) {
  return auditLogExportSchema.parse(data);
}

/**
 * Validates complete extended analysis result
 */
export function validateExtendedAnalysisResult(data: unknown) {
  return extendedAnalysisResultSchema.parse(data);
}

// ============================================================================
// Safe Parse Helpers (returns result instead of throwing)
// ============================================================================

/**
 * Safely validates missing documentation (doesn't throw)
 */
export function safeParseMissingDocumentation(data: unknown) {
  return missingDocumentationArraySchema.safeParse(data);
}

/**
 * Safely validates denial risks (doesn't throw)
 */
export function safeParseDenialRisks(data: unknown) {
  return denialRiskArraySchema.safeParse(data);
}

/**
 * Safely validates revenue comparison (doesn't throw)
 */
export function safeParseRevenueComparison(data: unknown) {
  return revenueComparisonSchema.safeParse(data);
}

/**
 * Safely validates modifier suggestions (doesn't throw)
 */
export function safeParseModifierSuggestions(data: unknown) {
  return modifierSuggestionArraySchema.safeParse(data);
}

/**
 * Safely validates uncaptured services (doesn't throw)
 */
export function safeParseUncapturedServices(data: unknown) {
  return uncapturedServiceArraySchema.safeParse(data);
}

/**
 * Safely validates audit log export (doesn't throw)
 */
export function safeParseAuditLogExport(data: unknown) {
  return auditLogExportSchema.safeParse(data);
}

/**
 * Safely validates extended analysis result (doesn't throw)
 */
export function safeParseExtendedAnalysisResult(data: unknown) {
  return extendedAnalysisResultSchema.safeParse(data);
}
