# Analysis Features Schema Design Documentation

**Created:** 2025-10-03
**Version:** 1.0.0
**Status:** Complete

## Overview

This document explains the design decisions, rationale, and field descriptions for the extended analysis features schemas. These schemas support post-facto coding review functionality including documentation quality checks, denial risk prediction, revenue comparison, modifier suggestions, charge capture, and audit logging.

---

## Design Principles

### 1. **Type Safety**
- All schemas use TypeScript for compile-time type checking
- Zod validation provides runtime type safety
- Strict validation rules prevent invalid data from propagating through the system

### 2. **HIPAA Compliance**
- All PHI (Protected Health Information) fields are explicitly marked for anonymization
- Audit logs use anonymized identifiers (`providerId`, `patientId`)
- No direct patient names, SSNs, or other identifying information in schemas

### 3. **Backward Compatibility**
- Extended analysis results use optional fields
- Existing analysis pipeline continues to work without modifications
- New features can be enabled incrementally

### 4. **Actionable Data**
- Every schema includes justifications and contextual information
- Suggestions are specific and implementable
- Priority levels help users focus on high-impact items

### 5. **Auditability**
- All suggestions include chart references
- Timestamps track when analysis occurred
- Metadata preserves context for compliance reviews

---

## Schema Descriptions

### 1. Missing Documentation Schema

**Purpose:** Identify gaps in clinical documentation that could justify higher-value billing codes.

```typescript
interface MissingDocumentation {
  section: string;      // E.g., "History of Present Illness", "Physical Exam"
  issue: string;        // E.g., "Missing duration of symptoms"
  suggestion: string;   // E.g., "Add specific timeline of symptom onset"
  priority?: string;    // Optional: "High" | "Medium" | "Low"
}
```

**Field Decisions:**

- **`section`** (required): Structured location in chart helps providers quickly locate gaps
  - Validation: Non-empty string
  - Examples: "HPI", "Physical Exam", "Review of Systems", "Assessment & Plan"

- **`issue`** (required): Clear description of what's missing
  - Validation: Non-empty string
  - Should be specific and actionable

- **`suggestion`** (required): Concrete action provider can take
  - Validation: Non-empty string
  - Should provide explicit guidance (e.g., "Document pain scale 1-10")

- **`priority`** (optional): Helps triage documentation improvements
  - Validation: Enum - "High" | "Medium" | "Low"
  - Rationale: Optional because not all issues have clear priority
  - High: Could significantly increase reimbursement
  - Medium: Moderate impact on coding level
  - Low: Minor documentation improvement

**Use Cases:**
- Provider reviews note before finalizing
- Quality improvement teams identify common documentation gaps
- Training programs highlight areas for improvement

---

### 2. Denial Risk Schema

**Purpose:** Predict which codes are at risk of payer denial based on documentation quality.

```typescript
interface DenialRisk {
  code: string;           // CPT/ICD code
  riskLevel: 'Low' | 'Medium' | 'High';
  reasons: string[];      // Common denial reasons
  addressed: boolean;     // Does note address the risks?
  justification: string;  // Explanation of risk assessment
}
```

**Field Decisions:**

- **`code`** (required): The specific billing code being assessed
  - Validation: Regex pattern `^[A-Z0-9-]+$`
  - Format: Standard CPT/ICD format (e.g., "99214", "M79.3")

- **`riskLevel`** (required): Three-tier risk classification
  - Validation: Enum - "Low" | "Medium" | "High"
  - Rationale: Three levels provide sufficient granularity without overwhelming users
  - Low: Well-documented, low denial probability
  - Medium: Some documentation concerns
  - High: Significant denial risk, requires attention

- **`reasons`** (required array, min 1 item): Common payer denial triggers
  - Validation: Array of strings, minimum 1 reason
  - Examples: "Insufficient medical necessity", "MDM not clearly documented"
  - Rationale: Educates providers about specific denial triggers

- **`addressed`** (required boolean): Quick indicator of documentation quality
  - `true`: Note adequately addresses denial risks
  - `false`: Note has gaps that could trigger denial
  - Helps providers prioritize corrections

- **`justification`** (required): Detailed explanation of the risk assessment
  - Validation: Non-empty string
  - Should reference specific parts of note
  - Provides audit trail for compliance

**Risk Level Criteria:**

| Risk Level | Denial Probability | Action Required |
|------------|-------------------|-----------------|
| Low | < 5% | Proceed with billing |
| Medium | 5-20% | Review documentation, consider addendum |
| High | > 20% | Improve documentation or reconsider code |

---

### 3. Revenue Comparison Schema

**Purpose:** Quantify potential missed revenue by comparing billed vs suggested codes.

```typescript
interface RevenueComparison {
  billedCodes: string[];      // Codes actually billed
  billedRVUs: number;         // Total RVUs for billed codes
  suggestedCodes: string[];   // LLM-suggested codes
  suggestedRVUs: number;      // Total RVUs for suggested codes
  missedRevenue: number;      // Difference (can be negative)
  percentDifference: number;  // Percentage change
}
```

**Field Decisions:**

- **`billedCodes`** (required array): Codes the provider actually billed
  - Validation: Array of strings (can be empty for new encounters)
  - Preserves original billing for comparison

- **`billedRVUs`** (required number >= 0): Relative Value Units for billed codes
  - Validation: Non-negative number
  - RVU = work RVU + practice expense RVU + malpractice RVU
  - Industry-standard metric for comparing service complexity

- **`suggestedCodes`** (required array): AI-recommended codes
  - Validation: Array of strings (can be empty)
  - Based on LLM analysis of clinical note

- **`suggestedRVUs`** (required number >= 0): RVUs for suggested codes
  - Validation: Non-negative number
  - Allows direct comparison with billed RVUs

- **`missedRevenue`** (required number, can be negative): Revenue delta
  - Validation: Any number (positive or negative)
  - Positive: Under-coding (missed revenue)
  - Negative: Potential over-coding (compliance risk)
  - Formula: `suggestedRVUs - billedRVUs`

- **`percentDifference`** (required number): Percentage change
  - Validation: -100% to 1000% (reasonable bounds)
  - Formula: `((suggestedRVUs - billedRVUs) / billedRVUs) * 100`
  - Provides context for magnitude of difference

**Interpretation Guide:**

| Missed Revenue | Interpretation | Action |
|----------------|----------------|--------|
| > 0.5 RVU | Significant under-coding | Review suggested codes |
| 0 to 0.5 RVU | Minor under-coding | Consider suggestions |
| 0 RVU | Optimal coding | Continue current practice |
| < 0 RVU | Potential over-coding | Compliance review |

---

### 4. Modifier Suggestion Schema

**Purpose:** Identify when CPT modifiers should be added to maximize appropriate reimbursement.

```typescript
interface ModifierSuggestion {
  code: string;           // CPT code
  modifier: string;       // Modifier code (e.g., "-25")
  justification: string;  // Why this modifier applies
  isNewSuggestion: boolean; // New or already billed?
}
```

**Field Decisions:**

- **`code`** (required): The CPT code to modify
  - Validation: Regex `^[A-Z0-9-]+$`
  - Must be a valid CPT code

- **`modifier`** (required): Two-digit modifier
  - Validation: Regex `^-\d{2}$` (e.g., "-25", "-59")
  - Format enforces standard CPT modifier notation
  - Common modifiers:
    - `-25`: Significant, separately identifiable E/M service
    - `-59`: Distinct procedural service
    - `-76`: Repeat procedure by same physician
    - `-77`: Repeat procedure by another physician
    - `-51`: Multiple procedures

- **`justification`** (required): Clinical rationale for modifier
  - Validation: Non-empty string
  - Should reference specific documentation
  - Supports medical necessity in audits

- **`isNewSuggestion`** (required boolean): Distinguishes new vs existing
  - `true`: AI is suggesting adding this modifier
  - `false`: Modifier already billed correctly
  - Helps providers focus on actionable changes

**Common Modifier Scenarios:**

| Modifier | When to Use | Example |
|----------|-------------|---------|
| -25 | Separate E/M on same day as procedure | Office visit + minor procedure |
| -59 | Distinct procedural service | Two procedures, different anatomic sites |
| -76 | Repeat procedure, same doctor | Second X-ray same day |
| -51 | Multiple procedures | Colonoscopy + biopsy |

---

### 5. Uncaptured Service Schema

**Purpose:** Identify services documented but not linked to billing codes (charge capture).

```typescript
interface UncapturedService {
  service: string;          // Description of service
  location: string;         // Where documented in chart
  suggestedCodes: string[]; // Applicable CPT codes
  priority: 'High' | 'Medium' | 'Low';
  estimatedRVUs?: number;   // Potential revenue value
}
```

**Field Decisions:**

- **`service`** (required): Clear description of performed service
  - Validation: Non-empty string
  - Examples: "EKG interpretation", "Wound debridement", "Patient education"

- **`location`** (required): Chart reference
  - Validation: Non-empty string
  - Examples: "Progress Note - Page 2", "Nursing Notes", "Procedure Note"
  - Helps provider verify service was actually performed

- **`suggestedCodes`** (required array, min 1): Applicable billing codes
  - Validation: Array with at least one code
  - Provides specific codes to bill
  - May include multiple options (e.g., different levels of wound care)

- **`priority`** (required): Urgency of capturing this charge
  - Validation: Enum - "High" | "Medium" | "Low"
  - High: Significant revenue impact or common miss
  - Medium: Moderate revenue value
  - Low: Minor charge but worth capturing

- **`estimatedRVUs`** (optional): Revenue potential
  - Validation: Non-negative number (if provided)
  - Helps prioritize charge capture efforts
  - Optional because not all services have clear RVU values

**Priority Assignment Logic:**

| Priority | Criteria |
|----------|----------|
| High | RVUs > 1.0 OR commonly missed service |
| Medium | RVUs 0.5-1.0 OR moderate complexity |
| Low | RVUs < 0.5 OR simple service |

---

### 6. Audit Log Export Schema

**Purpose:** Generate compliant audit trail for billing suggestions and compliance reviews.

```typescript
interface AuditLogExport {
  metadata: AuditLogMetadata;
  suggestedCodes: AuditSuggestedCode[];
  justifications: {
    assessment: string;
    qualityNotes?: string[];
    riskNotes?: string[];
  };
  timestamp: string;
}

interface AuditLogMetadata {
  providerId: string;           // Anonymized
  patientId: string;            // Anonymized
  dateOfService: string;        // YYYY-MM-DD
  encounterType: 'inpatient' | 'outpatient' | 'emergency' | ...;
  analysisTimestamp: string;    // ISO datetime
}

interface AuditSuggestedCode {
  code: string;
  description: string;
  justification: string;
  chartReference: string;
}
```

**Field Decisions:**

**Metadata Fields:**

- **`providerId`** (required): Anonymized provider identifier
  - Validation: Non-empty string
  - MUST NOT contain actual provider name or NPI
  - Use internal ID or hash

- **`patientId`** (required): Anonymized patient identifier
  - Validation: Non-empty string
  - MUST NOT contain MRN, SSN, or identifiable information
  - Use session ID or temporary hash

- **`dateOfService`** (required): When care was provided
  - Validation: YYYY-MM-DD format (regex: `^\d{4}-\d{2}-\d{2}$`)
  - Standard ISO date format for consistency

- **`encounterType`** (required): Type of visit
  - Validation: Enum with specific encounter types
  - Options: "inpatient", "outpatient", "emergency", "urgent_care", "telehealth", "other"
  - Affects coding rules and reimbursement

- **`analysisTimestamp`** (required): When AI analysis occurred
  - Validation: ISO 8601 datetime format
  - Provides audit trail timestamp

**Suggested Code Fields:**

- **`code`** (required): The CPT/ICD code
- **`description`** (required): Plain-language code description
  - Helps non-coders understand suggestions
- **`justification`** (required): Why this code applies
  - Must reference specific clinical findings
- **`chartReference`** (required): Where evidence is located
  - Critical for audit defense

**Justifications Object:**

- **`assessment`** (required): Overall coding assessment
  - Summary of analysis findings
- **`qualityNotes`** (optional array): Documentation strengths
  - Positive findings (e.g., "Thorough HPI")
- **`riskNotes`** (optional array): Compliance concerns
  - Risk factors or areas needing attention

**PHI Protection:**

- ✅ All identifiers are anonymized
- ✅ No patient names, addresses, or direct identifiers
- ✅ Compliant with HIPAA audit requirements
- ✅ Minimal necessary information for compliance review

---

## Validation Strategy

### Runtime Validation
All data entering the system is validated using Zod schemas:

```typescript
// Throws error if invalid
validateMissingDocumentation(data);

// Returns {success: boolean, data?: T, error?: ZodError}
safeParseMissingDocumentation(data);
```

### Validation Benefits
1. **Type Safety**: Catch errors at boundaries
2. **Clear Errors**: Zod provides detailed error messages
3. **Documentation**: Schemas serve as API documentation
4. **Consistency**: Same validation logic everywhere

### Error Handling

```typescript
const result = safeParseDenialRisks(unknownData);

if (!result.success) {
  // Handle validation error
  console.error('Validation failed:', result.error.format());
  return;
}

// Type-safe access to validated data
const denialRisks: DenialRisk[] = result.data;
```

---

## Testing Strategy

### Test Coverage
- ✅ Valid data acceptance
- ✅ Invalid data rejection
- ✅ Edge cases (empty arrays, boundary values)
- ✅ Optional fields
- ✅ Safe parse functions
- ✅ Array validations

### Test Organization
- One test file per schema module
- Describe blocks for each schema type
- Positive and negative test cases
- Integration tests for complex schemas

---

## Usage Examples

### Frontend Usage

```typescript
import { safeParseDenialRisks } from '@/lib/schemas/analysis-features';
import type { DenialRisk } from '@/types/analysis-features';

function DenialRiskTable({ data }: { data: unknown }) {
  const result = safeParseDenialRisks(data);

  if (!result.success) {
    return <ErrorMessage error={result.error} />;
  }

  const risks: DenialRisk[] = result.data;

  return (
    <table>
      {risks.map(risk => (
        <tr key={risk.code}>
          <td>{risk.code}</td>
          <td className={getRiskColor(risk.riskLevel)}>
            {risk.riskLevel}
          </td>
        </tr>
      ))}
    </table>
  );
}
```

### Backend Usage

```typescript
import { validateRevenueComparison } from '@/lib/schemas/analysis-features';

async function calculateRevenue(encounter: Encounter) {
  const comparison = {
    billedCodes: encounter.billedCodes,
    billedRVUs: calculateRVUs(encounter.billedCodes),
    suggestedCodes: encounter.suggestedCodes,
    suggestedRVUs: calculateRVUs(encounter.suggestedCodes),
    missedRevenue: /* calculation */,
    percentDifference: /* calculation */,
  };

  // Validate before saving
  validateRevenueComparison(comparison);

  await db.revenueComparison.create({ data: comparison });
}
```

---

## Future Enhancements

### Planned Additions
1. **Historical Comparison**: Track coding patterns over time
2. **Provider Benchmarking**: Compare against peer providers
3. **Payer-Specific Rules**: Denial risk varies by payer
4. **Auto-Correction**: Suggest specific documentation templates

### Schema Versioning
- Use semantic versioning for schema changes
- Maintain backward compatibility
- Document breaking changes in migration guides

---

## References

- [CMS RVU Files](https://www.cms.gov/medicare/physician-fee-schedule/search)
- [CPT Modifier Guidelines](https://www.ama-assn.org/practice-management/cpt/cpt-modifiers)
- [HIPAA Audit Requirements](https://www.hhs.gov/hipaa/for-professionals/compliance-enforcement/audit/index.html)
- [Zod Documentation](https://zod.dev/)

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-03 | Initial schema design and documentation |

---

## Contact

For questions about schema design decisions, contact the development team or refer to the project repository.
