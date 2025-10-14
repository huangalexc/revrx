/**
 * Test suite for analysis features schemas
 *
 * Tests validation logic for:
 * - Documentation Quality
 * - Denial Risk
 * - Revenue Comparison
 * - Modifier Suggestions
 * - Uncaptured Services
 * - Audit Log Export
 */

import {
  missingDocumentationSchema,
  denialRiskSchema,
  revenueComparisonSchema,
  modifierSuggestionSchema,
  uncapturedServiceSchema,
  auditLogExportSchema,
  validateMissingDocumentation,
  validateDenialRisks,
  validateRevenueComparison,
  validateModifierSuggestions,
  validateUncapturedServices,
  validateAuditLogExport,
  safeParseMissingDocumentation,
  safeParseDenialRisks,
  safeParseRevenueComparison,
  safeParseModifierSuggestions,
  safeParseUncapturedServices,
  safeParseAuditLogExport,
} from '../analysis-features';

describe('MissingDocumentation Schema', () => {
  it('should validate valid missing documentation', () => {
    const validData = {
      section: 'History of Present Illness',
      issue: 'Missing duration of symptoms',
      suggestion: 'Add specific timeline of symptom onset',
      priority: 'High' as const,
    };

    expect(() => missingDocumentationSchema.parse(validData)).not.toThrow();
  });

  it('should validate without optional priority', () => {
    const validData = {
      section: 'Physical Exam',
      issue: 'Missing cardiovascular exam',
      suggestion: 'Document heart sounds and rhythm',
    };

    expect(() => missingDocumentationSchema.parse(validData)).not.toThrow();
  });

  it('should reject empty section', () => {
    const invalidData = {
      section: '',
      issue: 'Some issue',
      suggestion: 'Some suggestion',
    };

    expect(() => missingDocumentationSchema.parse(invalidData)).toThrow();
  });

  it('should reject invalid priority', () => {
    const invalidData = {
      section: 'Review of Systems',
      issue: 'Incomplete',
      suggestion: 'Complete all systems',
      priority: 'Critical', // Invalid value
    };

    expect(() => missingDocumentationSchema.parse(invalidData)).toThrow();
  });

  it('should validate array of missing documentation', () => {
    const validArray = [
      {
        section: 'HPI',
        issue: 'Missing severity',
        suggestion: 'Rate pain on 1-10 scale',
      },
      {
        section: 'ROS',
        issue: 'Incomplete',
        suggestion: 'Document all organ systems',
        priority: 'Medium' as const,
      },
    ];

    expect(() => validateMissingDocumentation(validArray)).not.toThrow();
  });
});

describe('DenialRisk Schema', () => {
  it('should validate valid denial risk', () => {
    const validData = {
      code: '99214',
      riskLevel: 'Medium' as const,
      reasons: ['Insufficient documentation of complexity', 'MDM not clearly stated'],
      addressed: true,
      justification: 'Note includes detailed assessment and plan addressing complexity',
    };

    expect(() => denialRiskSchema.parse(validData)).not.toThrow();
  });

  it('should reject invalid code format', () => {
    const invalidData = {
      code: 'invalid_code',
      riskLevel: 'Low' as const,
      reasons: ['Some reason'],
      addressed: false,
      justification: 'Some justification',
    };

    expect(() => denialRiskSchema.parse(invalidData)).toThrow();
  });

  it('should reject empty reasons array', () => {
    const invalidData = {
      code: '99213',
      riskLevel: 'Low' as const,
      reasons: [],
      addressed: true,
      justification: 'Justification',
    };

    expect(() => denialRiskSchema.parse(invalidData)).toThrow();
  });

  it('should validate array of denial risks', () => {
    const validArray = [
      {
        code: '99214',
        riskLevel: 'High' as const,
        reasons: ['Lack of medical necessity'],
        addressed: false,
        justification: 'Chief complaint does not support level 4 visit',
      },
      {
        code: '80053',
        riskLevel: 'Low' as const,
        reasons: ['Generally well-documented'],
        addressed: true,
        justification: 'Order clearly documented with medical necessity',
      },
    ];

    expect(() => validateDenialRisks(validArray)).not.toThrow();
  });
});

describe('RevenueComparison Schema', () => {
  it('should validate valid revenue comparison', () => {
    const validData = {
      billedCodes: ['99213', '80053'],
      billedRVUs: 2.5,
      suggestedCodes: ['99214', '80053', '36415'],
      suggestedRVUs: 3.2,
      missedRevenue: 0.7,
      percentDifference: 28.0,
    };

    expect(() => revenueComparisonSchema.parse(validData)).not.toThrow();
  });

  it('should allow negative missed revenue (over-coding)', () => {
    const validData = {
      billedCodes: ['99215'],
      billedRVUs: 3.2,
      suggestedCodes: ['99214'],
      suggestedRVUs: 2.6,
      missedRevenue: -0.6,
      percentDifference: -18.75,
    };

    expect(() => revenueComparisonSchema.parse(validData)).not.toThrow();
  });

  it('should reject negative RVUs', () => {
    const invalidData = {
      billedCodes: [],
      billedRVUs: -1.0,
      suggestedCodes: [],
      suggestedRVUs: 0,
      missedRevenue: 0,
      percentDifference: 0,
    };

    expect(() => revenueComparisonSchema.parse(invalidData)).toThrow();
  });

  it('should validate empty code arrays', () => {
    const validData = {
      billedCodes: [],
      billedRVUs: 0,
      suggestedCodes: [],
      suggestedRVUs: 0,
      missedRevenue: 0,
      percentDifference: 0,
    };

    expect(() => validateRevenueComparison(validData)).not.toThrow();
  });
});

describe('ModifierSuggestion Schema', () => {
  it('should validate valid modifier suggestion', () => {
    const validData = {
      code: '99214',
      modifier: '-25',
      justification: 'Separately identifiable E/M service on same day as procedure',
      isNewSuggestion: true,
    };

    expect(() => modifierSuggestionSchema.parse(validData)).not.toThrow();
  });

  it('should validate existing modifier (not new)', () => {
    const validData = {
      code: '27447',
      modifier: '-59',
      justification: 'Distinct procedural service already billed correctly',
      isNewSuggestion: false,
    };

    expect(() => modifierSuggestionSchema.parse(validData)).not.toThrow();
  });

  it('should reject invalid modifier format', () => {
    const invalidData = {
      code: '99213',
      modifier: '25', // Missing hyphen
      justification: 'Some justification',
      isNewSuggestion: true,
    };

    expect(() => modifierSuggestionSchema.parse(invalidData)).toThrow();
  });

  it('should validate array of modifier suggestions', () => {
    const validArray = [
      {
        code: '99214',
        modifier: '-25',
        justification: 'E/M with procedure',
        isNewSuggestion: true,
      },
      {
        code: '99214',
        modifier: '-59',
        justification: 'Distinct service',
        isNewSuggestion: false,
      },
    ];

    expect(() => validateModifierSuggestions(validArray)).not.toThrow();
  });
});

describe('UncapturedService Schema', () => {
  it('should validate valid uncaptured service', () => {
    const validData = {
      service: 'EKG interpretation',
      location: 'Progress Note - Page 2',
      suggestedCodes: ['93000'],
      priority: 'High' as const,
      estimatedRVUs: 0.17,
    };

    expect(() => uncapturedServiceSchema.parse(validData)).not.toThrow();
  });

  it('should validate without optional estimatedRVUs', () => {
    const validData = {
      service: 'Wound care',
      location: 'Nursing Notes',
      suggestedCodes: ['97597', '97598'],
      priority: 'Medium' as const,
    };

    expect(() => uncapturedServiceSchema.parse(validData)).not.toThrow();
  });

  it('should reject empty suggested codes array', () => {
    const invalidData = {
      service: 'Some service',
      location: 'Some location',
      suggestedCodes: [],
      priority: 'Low' as const,
    };

    expect(() => uncapturedServiceSchema.parse(invalidData)).toThrow();
  });

  it('should reject negative estimatedRVUs', () => {
    const invalidData = {
      service: 'Service',
      location: 'Location',
      suggestedCodes: ['12345'],
      priority: 'High' as const,
      estimatedRVUs: -1.0,
    };

    expect(() => uncapturedServiceSchema.parse(invalidData)).toThrow();
  });

  it('should validate array of uncaptured services', () => {
    const validArray = [
      {
        service: 'Spirometry',
        location: 'Pulmonary Note',
        suggestedCodes: ['94010'],
        priority: 'High' as const,
        estimatedRVUs: 0.26,
      },
      {
        service: 'Patient education',
        location: 'Discharge Summary',
        suggestedCodes: ['99071'],
        priority: 'Low' as const,
      },
    ];

    expect(() => validateUncapturedServices(validArray)).not.toThrow();
  });
});

describe('AuditLogExport Schema', () => {
  it('should validate valid audit log export', () => {
    const validData = {
      metadata: {
        providerId: 'PROV-12345',
        patientId: 'PAT-67890',
        dateOfService: '2025-01-15',
        encounterType: 'outpatient' as const,
        analysisTimestamp: '2025-01-16T10:30:00Z',
      },
      suggestedCodes: [
        {
          code: '99214',
          description: 'Office visit, established patient, level 4',
          justification: 'Moderate complexity MDM with detailed history',
          chartReference: 'Progress Note, Page 1',
        },
      ],
      justifications: {
        assessment: 'Comprehensive coding review completed',
        qualityNotes: ['HPI well-documented', 'Physical exam thorough'],
        riskNotes: ['Low denial risk for all suggested codes'],
      },
      timestamp: '2025-01-16T10:35:00Z',
    };

    expect(() => auditLogExportSchema.parse(validData)).not.toThrow();
  });

  it('should reject invalid date format', () => {
    const invalidData = {
      metadata: {
        providerId: 'PROV-123',
        patientId: 'PAT-456',
        dateOfService: '01/15/2025', // Wrong format
        encounterType: 'outpatient' as const,
        analysisTimestamp: '2025-01-16T10:30:00Z',
      },
      suggestedCodes: [],
      justifications: {
        assessment: 'Assessment',
      },
      timestamp: '2025-01-16T10:35:00Z',
    };

    expect(() => auditLogExportSchema.parse(invalidData)).toThrow();
  });

  it('should reject invalid encounter type', () => {
    const invalidData = {
      metadata: {
        providerId: 'PROV-123',
        patientId: 'PAT-456',
        dateOfService: '2025-01-15',
        encounterType: 'invalid_type',
        analysisTimestamp: '2025-01-16T10:30:00Z',
      },
      suggestedCodes: [],
      justifications: {
        assessment: 'Assessment',
      },
      timestamp: '2025-01-16T10:35:00Z',
    };

    expect(() => auditLogExportSchema.parse(invalidData)).toThrow();
  });

  it('should validate with optional notes arrays', () => {
    const validData = {
      metadata: {
        providerId: 'PROV-123',
        patientId: 'PAT-456',
        dateOfService: '2025-01-15',
        encounterType: 'emergency' as const,
        analysisTimestamp: '2025-01-16T10:30:00Z',
      },
      suggestedCodes: [],
      justifications: {
        assessment: 'Complete assessment',
        // qualityNotes and riskNotes are optional
      },
      timestamp: '2025-01-16T10:35:00Z',
    };

    expect(() => validateAuditLogExport(validData)).not.toThrow();
  });
});

describe('Safe Parse Functions', () => {
  it('should return success for valid data', () => {
    const validData = [
      {
        section: 'HPI',
        issue: 'Missing timeline',
        suggestion: 'Add duration',
      },
    ];

    const result = safeParseMissingDocumentation(validData);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data).toEqual(validData);
    }
  });

  it('should return error for invalid data', () => {
    const invalidData = [
      {
        section: '', // Empty section
        issue: 'Issue',
        suggestion: 'Suggestion',
      },
    ];

    const result = safeParseMissingDocumentation(invalidData);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error).toBeDefined();
    }
  });

  it('should safely parse denial risks', () => {
    const invalidData = {
      code: 'invalid',
      riskLevel: 'Low',
      reasons: [],
      addressed: true,
      justification: 'Test',
    };

    const result = safeParseDenialRisks([invalidData]);
    expect(result.success).toBe(false);
  });

  it('should safely parse revenue comparison', () => {
    const validData = {
      billedCodes: [],
      billedRVUs: 0,
      suggestedCodes: [],
      suggestedRVUs: 0,
      missedRevenue: 0,
      percentDifference: 0,
    };

    const result = safeParseRevenueComparison(validData);
    expect(result.success).toBe(true);
  });

  it('should safely parse modifier suggestions', () => {
    const invalidData = [
      {
        code: '99213',
        modifier: 'XX', // Missing hyphen
        justification: 'Test',
        isNewSuggestion: true,
      },
    ];

    const result = safeParseModifierSuggestions(invalidData);
    expect(result.success).toBe(false);
  });

  it('should safely parse uncaptured services', () => {
    const validData = [
      {
        service: 'Test service',
        location: 'Test location',
        suggestedCodes: ['12345'],
        priority: 'High' as const,
      },
    ];

    const result = safeParseUncapturedServices(validData);
    expect(result.success).toBe(true);
  });

  it('should safely parse audit log export', () => {
    const invalidData = {
      metadata: {
        providerId: '',
        patientId: 'PAT-123',
        dateOfService: '2025-01-15',
        encounterType: 'outpatient',
        analysisTimestamp: '2025-01-16T10:30:00Z',
      },
      suggestedCodes: [],
      justifications: {
        assessment: 'Test',
      },
      timestamp: '2025-01-16T10:35:00Z',
    };

    const result = safeParseAuditLogExport(invalidData);
    expect(result.success).toBe(false);
  });
});
