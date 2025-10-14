# Feature Expansion Tasks

**Source:** `scripts/feature_expansion.txt`
**Created:** 2025-10-03
**Status:** In Progress - Tracks A, D, E, F Complete ✅

This document breaks down the post-facto coding review MVP features into actionable development tasks. All features leverage the existing HIPAA-compliant pipeline (file upload → PHI removal → text extraction → LLM analysis → suggested codes output).

---

## 1. Documentation Quality Checks

**Epic Goal:** Analyze clinical notes for missing elements that could justify higher-value codes

### Tasks

- [ ] **1.1 Update LLM prompt template**
  - Add documentation quality analysis section to prompt
  - Include request: "Identify any missing documentation that may prevent billing at a higher level"
  - Add request: "Provide suggestions for improving documentation"
  - Location: Update in LLM service/prompt configuration

- [ ] **1.2 Define output schema**
  - Create TypeScript interface for missing documentation items
  - Structure: `{ section: string, issue: string, suggestion: string }[]`
  - Add Zod validation schema

- [ ] **1.3 Update API response**
  - Extend analysis API to include `missingDocumentation` field
  - Ensure proper typing in response interfaces

- [ ] **1.4 Create UI component**
  - Design "Documentation Quality" card/section
  - Display missing elements with actionable guidance
  - Add appropriate icons and visual hierarchy
  - Location: Add to review results page

- [ ] **1.5 Add unit tests**
  - Test prompt formatting with quality check requirements
  - Test parsing of LLM response for documentation gaps
  - Test UI rendering of suggestions

---

## 2. Denial Risk Predictor (Basic)

**Epic Goal:** Highlight codes at risk of denial if documentation is insufficient

### Tasks

- [ ] **2.1 Extend LLM prompt**
  - Add denial risk analysis section
  - Request: "For each billed and suggested code, list common payer denial reasons"
  - Request: "Assess whether the note addresses these denial risks"
  - Define risk levels: Low/Medium/High

- [ ] **2.2 Create denial risk schema**
  - TypeScript interface: `{ code: string, riskLevel: 'Low'|'Medium'|'High', reasons: string[], addressed: boolean }[]`
  - Add Zod validation

- [ ] **2.3 Update analysis service**
  - Parse denial risk data from LLM response
  - Map risk levels to visual indicators (colors, icons)

- [ ] **2.4 Create denial risk table UI**
  - Design table with columns: Code, Risk Level, Denial Reasons, Documentation Status
  - Add color coding (green/yellow/red for risk levels)
  - Include expandable rows for detailed justification

- [ ] **2.5 Add filtering/sorting**
  - Allow filtering by risk level
  - Sort by code or risk level
  - Add "Show only high-risk" toggle

- [ ] **2.6 Testing**
  - Test with various note types
  - Verify risk assessment accuracy
  - Test UI responsiveness

---

## 3. Under-coding Dashboard (Per Note Level)

**Epic Goal:** Compare billed vs suggested codes and quantify potential lost revenue

### Tasks

- [x] **3.1 RVU calculation in LLM prompt** ✅ *Completed 2025-10-03 (Track A)*
  - Extend prompt: "Compute RVUs for billed codes"
  - Request: "Compute RVUs for suggested codes"
  - Request: "Calculate potential missed revenue as (Suggested RVUs - Billed RVUs)"

- [x] **3.2 Create revenue comparison schema** ✅ *Completed 2025-10-03 (Track B)*
  - Interface: `{ billedCodes: string[], billedRVUs: number, suggestedCodes: string[], suggestedRVUs: number, missedRevenue: number }`
  - Add validation

- [x] **3.3 Build summary widget component** ✅ *Completed 2025-10-03 (Track E)*
  - Display billed codes with total RVUs
  - Display suggested codes with total RVUs
  - Highlight potential missed revenue
  - Add visual indicator (chart or progress bar)
  - Position at bottom of review report

- [x] **3.4 Add data visualization** ✅ *Completed 2025-10-03 (Track E)*
  - Create bar chart comparing billed vs suggested RVUs
  - Show percentage difference
  - Use color coding for easy interpretation

- [ ] **3.5 Aggregate reporting (optional)**
  - Consider adding dashboard to show totals across multiple notes
  - Track missed revenue trends over time

- [x] **3.6 Testing** ✅ *Completed 2025-10-03 (Track E)*
  - Test RVU calculations with known values
  - Verify revenue difference accuracy
  - Test edge cases (zero RVUs, equal values)

---

## 4. Modifier Suggestions

**Epic Goal:** Suggest when modifiers (e.g., -25, -59) are applicable

### Tasks

- [x] **4.1 Update LLM prompt for modifiers** ✅ *Completed 2025-10-03 (Track A)*
  - Add section: "Identify if modifiers should be added to billed/suggested CPT codes"
  - Request justification based on documentation
  - List common modifiers (-25, -59, -76, -77, etc.)

- [x] **4.2 Create modifier schema** ✅ *Completed 2025-10-03 (Track B)*
  - Interface: `{ code: string, modifier: string, justification: string }[]`
  - Add validation for valid modifier formats

- [x] **4.3 Update code display UI** ✅ *Completed 2025-10-03 (Track E)*
  - Show CPT + modifier combination (e.g., "99214-25")
  - Add tooltip/popover explaining modifier purpose
  - Highlight when modifier is newly suggested

- [x] **4.4 Add modifier education** ✅ *Completed 2025-10-03 (Track E)*
  - Include brief description of common modifiers
  - Link to reference documentation
  - Show examples of appropriate usage

- [x] **4.5 Testing** ✅ *Completed 2025-10-03 (Track E)*
  - Test with notes requiring multiple procedure modifiers
  - Verify modifier applicability logic
  - Test UI display with various modifier combinations

---

## 5. Audit Log / Compliance Export

**Epic Goal:** Generate structured report for audit purposes

### Tasks

- [x] **5.1 Design export data structure** ✅ *Completed 2025-10-03 (Track F)*
  - Include: suggested codes, justifications, chart references
  - Add metadata: provider (anonymized), patient ID (anonymized), timestamp
  - Define formats: PDF, CSV, JSON, YAML, HTML

- [x] **5.2 Create export service** ✅ *Completed 2025-10-03 (Track F)*
  - Built PDF generator using WeasyPrint (Python server-side)
  - Built CSV generator with hierarchical structure
  - Enhanced HTML template with all features
  - Ensured proper formatting and layout for all formats

- [x] **5.3 Add export API endpoint** ✅ *Completed 2025-10-03 (Track F)*
  - Created `/reports/{encounter_id}/export` route
  - Support query param for format type (`?format=pdf|csv|json|yaml|html`)
  - Added JWT authentication/authorization via `get_current_user`
  - Implemented rate limiting

- [x] **5.4 Create export UI controls** ✅ *Completed 2025-10-03 (Track F)*
  - Added "Export Report" button component to review page
  - Implemented format selection dropdown with descriptions
  - Added loading state with spinner during generation
  - Added success/error toast notifications

- [x] **5.5 Implement compliance features** ✅ *Completed 2025-10-03 (Track F)*
  - Ensured all PHI remains redacted in exports
  - Added watermark/header with export timestamp and PHI status
  - Included disclaimer text for audit use
  - Added compliance notices to all export formats

- [x] **5.6 Testing** ✅ *Completed 2025-10-03 (Track F)*
  - Tested PDF generation with various content lengths
  - Tested CSV format compatibility with Excel/Google Sheets
  - Verified no PHI leakage in exports
  - 40+ test cases covering all formats and edge cases

---

## 6. Charge Capture Reminders

**Epic Goal:** Detect documented services without corresponding billing codes

### Tasks

- [x] **6.1 Extend LLM prompt for service detection** ✅ *Completed 2025-10-03 (Track A)*
  - Request: "Identify clinically significant services or procedures documented but not linked to any billing codes"
  - Request: "Suggest the appropriate code(s) for each uncaptured service"

- [x] **6.2 Create uncaptured service schema** ✅ *Completed 2025-10-03 (Track B)*
  - Interface: `{ service: string, location: string, suggestedCodes: string[], priority: 'High'|'Medium'|'Low' }[]`
  - Add validation

- [x] **6.3 Build uncaptured services UI section** ✅ *Completed 2025-10-03 (Track E)*
  - Create "Missed Charges" or "Charge Capture Opportunities" card
  - List services with suggested codes
  - Add priority indicators
  - Include chart location references

- [x] **6.4 Add notification/alert system** ✅ *Completed 2025-10-03 (Track E)*
  - Show count of uncaptured services in summary
  - Add visual indicator (badge, alert banner)
  - Consider notification for high-priority items

- [x] **6.5 Integration with revenue tracking** ✅ *Completed 2025-10-03 (Track E)*
  - Link to under-coding dashboard
  - Show potential revenue from captured charges

- [x] **6.6 Testing** ✅ *Completed 2025-10-03 (Track E)*
  - Test with notes containing various undocumented procedures
  - Verify code suggestions are appropriate
  - Test priority assignment logic

---

## Cross-Feature Tasks

### Infrastructure & Integration

- [ ] **7.1 Update main analysis pipeline**
  - Consolidate all new prompt sections
  - Ensure proper prompt ordering and structure
  - Test token limits with expanded prompts

- [ ] **7.2 Create unified response schema**
  - Extend existing analysis response to include all new features
  - Ensure backward compatibility
  - Update API documentation

- [ ] **7.3 Database schema updates (if needed)**
  - Consider storing analysis results for historical tracking
  - Add fields for new feature data
  - Create migration scripts

- [ ] **7.4 Update results page layout**
  - Redesign to accommodate all new sections
  - Organize with tabs or collapsible sections
  - Ensure mobile responsiveness

- [ ] **7.5 Performance optimization**
  - Test with large notes and multiple features
  - Implement lazy loading for heavy components
  - Consider caching strategies

### Testing & Quality

- [x] **8.1 Unit testing (Track G1-G2)** ✅ *Completed 2025-10-03*
  - Test prompt formatting and structure (Track A) - 39 tests passing
  - Test schema validation (Track B) - 21+ tests passing
  - Test UI components (Tracks D, E, F) - all tests passing
  - Test export generation - 40+ tests passing

- [x] **8.2 Integration testing (Track G7-G12)** ✅ *Completed 2025-10-03*
  - Test all features working together - 23 tests passing
  - Complete analysis pipeline (outpatient, inpatient, emergency)
  - API response structure validation
  - Error handling (empty notes, malformed codes, special chars, long notes)
  - Various note types (outpatient, inpatient, ER, procedure, telehealth)

- [x] **8.3 End-to-end testing (Track G13-G17)** ✅ *Completed 2025-10-03*
  - Test complete workflow: upload → analysis → display - 26 tests passing
  - Verify exports work with all features included (4 export tests)
  - Test filtering and sorting across features (6 filter/sort tests)
  - Test responsive design data requirements (4 responsive tests)
  - Test accessibility requirements (6 accessibility tests)
  - Test error handling (included in integration tests)

- [ ] **8.4 Performance benchmarking** (Track G18-G22 - pending Track C)
  - Measure analysis time with all features enabled
  - Test concurrent requests
  - Monitor LLM token usage

### Documentation & Compliance

- [ ] **9.1 Update user documentation**
  - Document each new feature
  - Provide examples and use cases
  - Create training materials

- [ ] **9.2 HIPAA compliance review**
  - Verify PHI handling in new features
  - Review export functionality for compliance
  - Update security documentation

- [ ] **9.3 Prompt engineering documentation**
  - Document final prompt structure
  - Provide examples of LLM responses
  - Create troubleshooting guide

---

## Implementation Priority Recommendation

### Phase 1 (MVP Core Enhancement)
1. Documentation Quality Checks (1.x)
2. Under-coding Dashboard (3.x)
3. Charge Capture Reminders (6.x)

### Phase 2 (Risk & Compliance)
4. Denial Risk Predictor (2.x)
5. Audit Log / Compliance Export (5.x)

### Phase 3 (Advanced Features)
6. Modifier Suggestions (4.x)

### Phase 4 (Polish & Scale)
7. Cross-Feature Infrastructure (7.x)
8. Testing & Quality (8.x)
9. Documentation (9.x)

---

## Notes

- All features use prompt engineering - no new external data sources required
- Outputs should be consistently formatted (tables, structured JSON/YAML)
- Existing PHI redaction and encryption workflow applies to all features
- Consider A/B testing different prompt variations for optimal results
- Monitor LLM costs as feature set expands
