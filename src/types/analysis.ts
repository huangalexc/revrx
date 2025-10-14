/**
 * Type definitions for enhanced analysis features
 * Matches the JSON schema from backend prompt templates
 */

export interface MissingDocumentation {
  section: string;
  issue: string;
  suggestion: string;
  priority: 'High' | 'Medium' | 'Low';
}

export interface DenialRisk {
  code: string;
  risk_level: 'Low' | 'Medium' | 'High';
  denial_reasons: string[];
  documentation_addresses_risks: boolean;
  mitigation_notes: string;
}

export interface RVUDetail {
  code: string;
  rvus: number;
  description: string;
}

export interface RVUAnalysis {
  billed_codes_rvus: number;
  suggested_codes_rvus: number;
  incremental_rvus: number;
  billed_code_details: RVUDetail[];
  suggested_code_details: RVUDetail[];
}

export interface ModifierSuggestion {
  code: string;
  modifier: string;
  justification: string;
  documentation_support: string;
}

export interface UncapturedService {
  service: string;
  location_in_note: string;
  suggested_codes: string[];
  priority: 'High' | 'Medium' | 'Low';
  justification: string;
  estimated_rvus?: number;
}

export interface AuditMetadata {
  total_codes_identified: number;
  high_confidence_codes: number;
  documentation_quality_score: number;
  compliance_flags: string[];
  timestamp: string;
}

// Extended report data interface
export interface EnhancedReportData {
  encounter_id: string;
  generated_at: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETE' | 'FAILED';
  metadata: {
    encounter_created: string;
    processing_time_ms?: number;
    processing_completed?: string;
    user_email: string;
    phi_included: boolean;
    phi_detected: boolean;
  };
  clinical_note: {
    text: string;
    length: number;
    uploaded_files: Array<{
      filename: string;
      file_type: string;
      file_size: number;
      uploaded_at: string;
    }>;
  };
  code_analysis: {
    billed_codes: Array<{
      code: string;
      code_type: string;
      description?: string;
    }>;
    suggested_codes: Array<{
      code: string;
      code_type: string;
      description?: string;
      billed_code?: string;
      comparison_type?: 'new' | 'upgrade' | 'match';
      revenue_impact?: number;
      confidence: number;
      justification: string;
      supporting_text: string[];
    }>;
    ai_model: string;
    confidence_score: number;
  };
  revenue_analysis: {
    incremental_revenue: number;
    currency: string;
    calculation_method: string;
  };
  summary: {
    total_billed_codes: number;
    total_suggested_codes: number;
    new_code_opportunities: number;
    upgrade_opportunities: number;
  };
  // New enhanced features
  missing_documentation?: MissingDocumentation[];
  denial_risks?: DenialRisk[];
  rvu_analysis?: RVUAnalysis;
  modifier_suggestions?: ModifierSuggestion[];
  uncaptured_services?: UncapturedService[];
  audit_metadata?: AuditMetadata;
}
