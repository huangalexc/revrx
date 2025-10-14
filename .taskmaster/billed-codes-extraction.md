# Billed Codes Extraction & Display - Implementation Tracks

**Goal**: Extract existing billed codes from clinical notes and display them in contrast to suggested codes to show the incremental value added by the app.

**Test Case**: Encounter #0f89ef53 should show CPT: 99393 and ICD-10: Z00.129 as originally billed codes.

---

## Track 1: Backend Schema & Data Model (Sequential)

**Dependencies**: None - Start immediately

### Tasks:
1. **Update Prisma Schema**
   - Add `billedCodes` Json field to `Report` model in `/backend/prisma/schema.prisma`
   - Structure: Array of `{code: string, code_type: string, description?: string}`

2. **Create Database Migration**
   - Run: `cd /Users/alexander/code/revrx/backend && npx prisma migrate dev --name add_billed_codes_to_report`
   - Verify migration created successfully

3. **Generate Prisma Client**
   - Run: `npx prisma generate`
   - Verify TypeScript types updated

**Completion Criteria**: Schema updated, migration applied, Prisma client regenerated

---

## Track 2: AI Code Extraction (Parallel with Track 1)

**Dependencies**: None - Can start immediately

### Tasks:
1. **Update OpenAI Prompt in `/backend/app/services/openai_service.py`**
   - Modify `CodeExtractionPrompt` class to extract existing billed codes from clinical notes
   - Add section to prompt: "Extract any existing CPT and ICD-10 codes mentioned in the clinical note"
   - Expected format: Look for patterns like "CPT: 99393", "ICD-10: Z00.129", "billed as...", etc.

2. **Update CodeAnalysisResult Schema**
   - Add `billed_codes: List[BilledCode]` field to `CodeAnalysisResult` dataclass
   - Create `BilledCode` dataclass with fields: `code`, `code_type`, `description?`

3. **Update `analyze_clinical_note()` Response Parsing**
   - Parse `billed_codes` from OpenAI response
   - Store in `CodeAnalysisResult.billed_codes`

**Completion Criteria**: OpenAI service extracts billed codes and returns them in structured format

---

## Track 3: Report Generation Integration (Sequential - Depends on Track 1 & 2)

**Dependencies**: Wait for Track 1 Task 3 and Track 2 Task 3 to complete

### Tasks:
1. **Update `/backend/app/services/report_generator.py`**
   - Store `code_analysis.billed_codes` in `report.billedCodes` field (line ~150)
   - Include billed codes in report response structure (line ~123)

2. **Update `/backend/app/api/v1/reports.py`**
   - Verify `billed_codes` are returned in GET `/v1/reports/encounters/{id}` response
   - Check serialization of JSON field

**Completion Criteria**: Backend API returns `code_analysis.billed_codes` in report response

---

## Track 4: Frontend Display (Parallel with Track 3)

**Dependencies**: Can start as soon as Track 2 is complete (to understand data structure)

### Tasks:
1. **Update TypeScript Interfaces in `/src/app/(dashboard)/reports/[id]/page.tsx`**
   - Add `BilledCode` interface: `{code: string, code_type: string, description?: string}`
   - Update `code_analysis` interface to include `billed_codes: BilledCode[]`

2. **Redesign "Originally Billed Codes" Section**
   - Move section to top of code analysis (before suggested codes)
   - Display each billed code with code type badge (CPT vs ICD-10)
   - Show code, type, and description if available

3. **Update "Suggested Additional Codes" Section**
   - Rename to clarify these are NEW/UPGRADE opportunities
   - Add contrast: "In addition to the X codes already billed..."
   - Filter out codes that match billed codes (avoid duplication)

4. **Add Value Summary Card**
   - Create new section showing:
     - "Originally Billed Codes: X codes"
     - "Additional Opportunities: Y codes"
     - "Potential Incremental Revenue: $Z"
   - Visual indicator of value added

**Completion Criteria**: Frontend displays billed vs suggested codes with clear value differentiation

---

## Track 5: Testing & Validation (Sequential - Depends on All Tracks)

**Dependencies**: Wait for all previous tracks to complete

### Tasks:
1. **Test Encounter #0f89ef53**
   - Navigate to report page
   - Verify "Originally Billed Codes" shows CPT: 99393 and ICD-10: Z00.129
   - Verify suggested codes don't duplicate these
   - Check revenue calculation only counts incremental opportunities

2. **Test Edge Cases**
   - Clinical note with no existing codes mentioned
   - Clinical note with many existing codes
   - Ensure no crashes when billed_codes is empty

3. **Visual Design Review**
   - Verify clear visual hierarchy between billed and suggested codes
   - Check responsive design on mobile/tablet
   - Ensure color-coding is accessible

**Completion Criteria**: All tests pass, UI is polished and accurate

---

## Parallel Execution Strategy

**Phase 1 (Parallel)**:
- Track 1: Schema updates (Tasks 1-3)
- Track 2: AI extraction (Tasks 1-3)
- Track 4: Frontend prep (Task 1)

**Phase 2 (After Phase 1)**:
- Track 3: Report integration (Tasks 1-2)
- Track 4: UI implementation (Tasks 2-4)

**Phase 3 (After Phase 2)**:
- Track 5: Testing (Tasks 1-3)

---

## Files to Modify

### Backend:
- `/backend/prisma/schema.prisma`
- `/backend/app/services/openai_service.py`
- `/backend/app/services/report_generator.py`
- `/backend/app/api/v1/reports.py`

### Frontend:
- `/src/app/(dashboard)/reports/[id]/page.tsx`

### Testing:
- Manual testing with encounter #0f89ef53
- Verify at: http://localhost:3000/reports/0f89ef53-c5d7-4623-9d59-79335a4dc5a6
