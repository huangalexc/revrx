/**
 * TypeScript interfaces for extended analysis features
 *
 * These types support the post-facto coding review MVP features:
 * - Documentation Quality Checks
 * - Denial Risk Prediction
 * - Revenue Comparison (Under-coding Detection)
 * - Modifier Suggestions
 * - Charge Capture
 * - Audit Log Export
 */

// ============================================================================
// Documentation Quality
// ============================================================================

/**
 * Represents a missing documentation element that could justify higher-value codes
 */
export interface MissingDocumentation {
  /** The section or area of documentation that is incomplete */
  section: string;

  /** Description of what is missing */
  issue: string;

  /** Actionable suggestion for improving documentation */
  suggestion: string;

  /** Optional priority level for addressing this issue */
  priority?: 'High' | 'Medium' | 'Low';
}

// ============================================================================
// Denial Risk Prediction
// ============================================================================

/**
 * Risk level for code denial by payers
 */
export type DenialRiskLevel = 'Low' | 'Medium' | 'High';

/**
 * Represents denial risk assessment for a specific code
 */
export interface DenialRisk {
  /** The CPT/ICD code being assessed */
  code: string;

  /** Risk level of denial */
  riskLevel: DenialRiskLevel;

  /** Common reasons this code might be denied */
  reasons: string[];

  /** Whether the clinical note addresses the denial risks */
  addressed: boolean;

  /** Justification for the risk assessment */
  justification: string;
}

// ============================================================================
// Revenue Comparison (Under-coding Detection)
// ============================================================================

/**
 * Comparison between billed codes and suggested codes with RVU analysis
 */
export interface RevenueComparison {
  /** Codes that were actually billed */
  billedCodes: string[];

  /** Total RVUs for billed codes */
  billedRVUs: number;

  /** Codes suggested by the analysis */
  suggestedCodes: string[];

  /** Total RVUs for suggested codes */
  suggestedRVUs: number;

  /** Potential missed revenue (positive means under-coding) */
  missedRevenue: number;

  /** Percentage difference between billed and suggested RVUs */
  percentDifference: number;
}

// ============================================================================
// Modifier Suggestions
// ============================================================================

/**
 * Suggested modifier for a CPT code
 */
export interface ModifierSuggestion {
  /** The CPT code to which the modifier applies */
  code: string;

  /** The modifier code (e.g., '-25', '-59', '-76', '-77') */
  modifier: string;

  /** Explanation of why this modifier is suggested */
  justification: string;

  /** Whether this is a new suggestion or already billed */
  isNewSuggestion: boolean;
}

// ============================================================================
// Charge Capture (Uncaptured Services)
// ============================================================================

/**
 * Priority level for uncaptured services
 */
export type UncapturedServicePriority = 'High' | 'Medium' | 'Low';

/**
 * Represents a service that was documented but not linked to billing codes
 */
export interface UncapturedService {
  /** Description of the service performed */
  service: string;

  /** Location/section in chart where service was documented */
  location: string;

  /** Suggested CPT codes for this service */
  suggestedCodes: string[];

  /** Priority for capturing this charge */
  priority: UncapturedServicePriority;

  /** Estimated RVUs if coded (optional) */
  estimatedRVUs?: number;
}

// ============================================================================
// Audit Log Export
// ============================================================================

/**
 * Metadata for audit log export
 */
export interface AuditLogMetadata {
  /** Provider identifier (anonymized for PHI compliance) */
  providerId: string;

  /** Patient identifier (anonymized for PHI compliance) */
  patientId: string;

  /** Date of service */
  dateOfService: string;

  /** Encounter type (inpatient, outpatient, ER, etc.) */
  encounterType: string;

  /** Timestamp of analysis */
  analysisTimestamp: string;
}

/**
 * Suggested codes with justifications for audit trail
 */
export interface AuditSuggestedCode {
  /** CPT/ICD code */
  code: string;

  /** Code description */
  description: string;

  /** Justification from clinical note */
  justification: string;

  /** Chart reference where evidence was found */
  chartReference: string;
}

/**
 * Complete audit log export structure
 */
export interface AuditLogExport {
  /** Metadata about the encounter and analysis */
  metadata: AuditLogMetadata;

  /** Suggested codes with complete justifications */
  suggestedCodes: AuditSuggestedCode[];

  /** Additional justifications and notes */
  justifications: {
    /** Overall assessment */
    assessment: string;

    /** Documentation quality notes */
    qualityNotes?: string[];

    /** Risk considerations */
    riskNotes?: string[];
  };

  /** Export generation timestamp */
  timestamp: string;
}

// ============================================================================
// Extended Analysis Result
// ============================================================================

/**
 * Extended analysis result including all new features
 * This extends the base analysis result with additional fields
 */
export interface ExtendedAnalysisResult {
  /** Original analysis fields would be included here */
  // ... existing fields from current AnalysisResult type

  /** Documentation quality analysis */
  missingDocumentation?: MissingDocumentation[];

  /** Denial risk predictions for all codes */
  denialRisks?: DenialRisk[];

  /** Revenue comparison between billed and suggested codes */
  revenueComparison?: RevenueComparison;

  /** Modifier suggestions */
  modifierSuggestions?: ModifierSuggestion[];

  /** Uncaptured services that should be billed */
  uncapturedServices?: UncapturedService[];

  /** Audit log data for export */
  auditLog?: AuditLogExport;
}
