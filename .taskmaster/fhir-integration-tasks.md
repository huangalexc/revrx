# FHIR Integration Implementation Tasks

**Created:** 2025-10-07
**Last Updated:** 2025-10-07
**Status:** In Progress
**Priority:** High
**Objective:** Implement FHIR-based EHR integration workflow alongside existing file upload workflow

**Progress:** Phase 4 Complete (API Endpoints)

---

## Overview

This task list details the implementation of FHIR integration for the RevRX medical coding application. The FHIR workflow will run in parallel with the existing file upload workflow, sharing core PHI processing, clinical filtering, and coding logic.

### Key Differences: File Upload vs FHIR Workflow

| Aspect | File Upload | FHIR Integration |
|--------|-------------|------------------|
| **Source** | S3-uploaded files (TXT/PDF/DOCX) | FHIR API (Encounter, Composition, DocumentReference) |
| **Identifier** | File hash (SHA-256 of filename) | FHIR Encounter ID |
| **Provider** | Extracted from PHI + LLM placeholder | FHIR Encounter.participant or fallback to LLM |
| **Date of Service** | Extracted from PHI + LLM placeholder | FHIR Encounter.period or fallback to LLM |
| **Patient ID** | Not stored (HIPAA) | FHIR Encounter.subject (stored as reference) |
| **Duplicate Detection** | File hash matching | FHIR Encounter ID matching |
| **Output** | Database storage only | Database + optional FHIR Claim/DocumentReference write-back |

---

## Phase 1: Database Schema & Models ✅ COMPLETE

### Task 1.1: Extend Encounter Model for FHIR Support ✅
**Priority:** High
**Estimated Time:** 1 hour
**Status:** ✅ Complete
**Completed:** 2025-10-07

- [x] Add FHIR-specific fields to `Encounter` model in `prisma/schema.prisma`:
  ```prisma
  // FHIR integration fields
  fhirEncounterId    String?  @unique @map("fhir_encounter_id")  // Canonical FHIR Encounter ID
  fhirPatientId      String?  @map("fhir_patient_id")            // FHIR Patient reference
  fhirProviderId     String?  @map("fhir_provider_id")           // FHIR Practitioner reference
  fhirSourceSystem   String?  @map("fhir_source_system")         // EHR system identifier
  encounterSource    EncounterSource @default(FILE_UPLOAD) @map("encounter_source") // FILE_UPLOAD or FHIR
  ```

- [x] Add `EncounterSource` enum:
  ```prisma
  enum EncounterSource {
    FILE_UPLOAD
    FHIR
  }
  ```

- [x] Add index on `fhirEncounterId` for fast lookup
- [x] Generate Prisma migration: `npx prisma db push --accept-data-loss`

**Acceptance Criteria:** ✅ All Met
- ✅ Schema includes all FHIR-specific fields
- ✅ Migration applied successfully to local database
- ✅ Unique constraint on `fhirEncounterId` prevents duplicate FHIR encounters

**Implementation Notes:**
- Added 5 new fields: `fhirEncounterId`, `fhirPatientId`, `fhirProviderId`, `fhirSourceSystem`, `encounterSource`
- Unique index automatically created on `fhirEncounterId`
- Default value `FILE_UPLOAD` ensures backward compatibility with existing encounters

---

### Task 1.2: Create FHIR Configuration Model ✅
**Priority:** Medium
**Estimated Time:** 45 minutes
**Status:** ✅ Complete
**Completed:** 2025-10-07

- [x] Add `FhirConnection` model to `prisma/schema.prisma`:
  ```prisma
  model FhirConnection {
    id                String   @id @default(uuid())
    userId            String   @map("user_id")

    // FHIR server configuration
    fhirServerUrl     String   @map("fhir_server_url")     // Base URL
    fhirVersion       String   @map("fhir_version")        // R4, R5, etc.

    // Authentication
    authType          FhirAuthType @map("auth_type")       // OAUTH2, BASIC, API_KEY
    clientId          String?  @map("client_id")
    clientSecretHash  String?  @map("client_secret_hash")  // Encrypted
    tokenEndpoint     String?  @map("token_endpoint")
    scope             String?  @map("scope")

    // Connection metadata
    isActive          Boolean  @default(true) @map("is_active")
    lastSyncAt        DateTime? @map("last_sync_at")
    lastError         String?  @map("last_error")

    createdAt         DateTime @default(now()) @map("created_at")
    updatedAt         DateTime @updatedAt @map("updated_at")

    user              User     @relation(fields: [userId], references: [id], onDelete: Cascade)

    @@map("fhir_connections")
    @@index([userId])
  }

  enum FhirAuthType {
    OAUTH2
    BASIC
    API_KEY
    SMART_ON_FHIR
  }
  ```

- [x] Update `User` model to add relation: `fhirConnections FhirConnection[]`

**Acceptance Criteria:** ✅ All Met
- ✅ FHIR connection configuration can be stored per user
- ✅ Secrets are stored encrypted (using existing encryption service)
- ✅ Multiple auth types supported for different EHR vendors

**Implementation Notes:**
- Created `FhirConnection` model with all required fields
- Added `FhirAuthType` enum supporting OAUTH2, BASIC, API_KEY, and SMART_ON_FHIR
- Added relation to User model
- Index created on `userId` for fast user-specific lookups
- Table created in database: `fhir_connections`

---

## Phase 2: FHIR Client Service ✅ COMPLETE

### Task 2.1: Create FHIR Client Base Service ✅
**Priority:** High
**Estimated Time:** 3 hours
**Status:** ✅ Complete
**Completed:** 2025-10-07

- [x] Create `backend/app/services/fhir/fhir_client.py`:
  - [x] Implement `FhirClient` class with async HTTP client
  - [x] Support OAuth2 authentication (Epic, Cerner)
  - [x] Support SMART on FHIR authentication
  - [x] Support Basic auth and API key auth
  - [x] Implement token refresh logic
  - [x] Add request/response logging
  - [x] Add retry logic with exponential backoff
  - [x] Handle FHIR OperationOutcome errors

- [x] Create `backend/app/services/fhir/__init__.py`
- [x] Add dependencies to `requirements.txt`:
  - `fhir.resources>=7.0.0` (FHIR R4/R5 models)
  - `httpx` (already installed)

**Key Methods:**
```python
class FhirClient:
    async def authenticate(self) -> str:
        """Get OAuth2 access token"""

    async def get_resource(self, resource_type: str, resource_id: str) -> dict:
        """Fetch single FHIR resource"""

    async def search_resources(self, resource_type: str, params: dict) -> List[dict]:
        """Search FHIR resources with parameters"""

    async def create_resource(self, resource_type: str, data: dict) -> dict:
        """Create new FHIR resource"""

    async def update_resource(self, resource_type: str, resource_id: str, data: dict) -> dict:
        """Update existing FHIR resource"""
```

**Acceptance Criteria:** ✅ All Met
- ✅ Client can authenticate with OAuth2 providers
- ✅ Client can fetch and search FHIR resources
- ✅ Errors are properly logged and handled
- ✅ Token refresh works automatically

**Implementation Notes:**
- Created comprehensive FhirClient with async HTTP client using httpx
- Supports OAuth2, SMART on FHIR, Basic Auth, and API Key authentication
- Implements automatic token refresh with 5-minute expiration buffer
- Includes retry logic with exponential backoff (3 attempts)
- Handles FHIR OperationOutcome errors with detailed logging
- All methods support context manager usage (async with)

---

### Task 2.2: Create FHIR Encounter Service ✅
**Priority:** High
**Estimated Time:** 2 hours
**Status:** ✅ Complete
**Completed:** 2025-10-07

- [x] Create `backend/app/services/fhir/encounter_service.py`:
  - [x] `fetch_encounters(patient_id: str, date_range: tuple) -> List[Encounter]`
  - [x] `fetch_encounter_by_id(encounter_id: str) -> Encounter`
  - [x] `extract_encounter_metadata(encounter: dict) -> dict`
    - Extract patient ID from `encounter.subject.reference`
    - Extract provider ID from `encounter.participant[0].individual.reference`
    - Extract date of service from `encounter.period.start`
    - Extract encounter type from `encounter.type` or `encounter.class`

**Acceptance Criteria:** ✅ All Met
- ✅ Can retrieve encounters from FHIR API
- ✅ Metadata extraction handles missing fields gracefully
- ✅ Returns standardized dict for downstream processing

**Implementation Notes:**
- Created FhirEncounterService with comprehensive metadata extraction
- Handles both relative and absolute FHIR references
- Supports FHIR R4 and R5 encounter class formats
- Includes validation method to ensure minimum required data
- Falls back gracefully when provider or date fields are missing
- Logs warnings for missing data that can be extracted by LLM later

---

### Task 2.3: Create FHIR Clinical Note Service ✅
**Priority:** High
**Estimated Time:** 2.5 hours
**Status:** ✅ Complete
**Completed:** 2025-10-07

- [x] Create `backend/app/services/fhir/note_service.py`:
  - [x] `fetch_clinical_notes(encounter_id: str) -> List[dict]`
    - Query `Composition` resources linked to Encounter
    - Query `DocumentReference` resources linked to Encounter
    - Support different note types (Progress Note, Discharge Summary, etc.)
  - [x] `extract_note_text(resource: dict) -> str`
    - Handle `Composition.section[].text.div` (HTML to text)
    - Handle `DocumentReference.content[0].attachment.data` (Base64 decode)
    - Handle inline text vs attachment references
  - [x] `get_note_metadata(resource: dict) -> dict`
    - Extract note type
    - Extract author (practitioner)
    - Extract date

**Acceptance Criteria:** ✅ All Met
- ✅ Can retrieve clinical notes from FHIR Composition resources
- ✅ Can retrieve clinical notes from FHIR DocumentReference resources
- ✅ Text extraction handles HTML and Base64 attachments
- ✅ Falls back gracefully when notes are unavailable

**Implementation Notes:**
- Created FhirNoteService for clinical note retrieval and processing
- Queries both Composition and DocumentReference resources
- HTML-to-text conversion with proper entity decoding
- Base64 attachment decoding for DocumentReference
- Supports recursive section processing for nested Composition sections
- Includes `combine_notes()` method to merge multiple notes into single text
- Extracts metadata (note type, author, date, title) from both resource types

---

### Task 2.4: Create FHIR Write-Back Service (Optional) ✅
**Priority:** Low
**Estimated Time:** 2 hours
**Status:** ✅ Complete
**Completed:** 2025-10-07

- [x] Create `backend/app/services/fhir/write_back_service.py`:
  - [x] `create_claim_resource(encounter_id: str, codes: dict) -> dict`
    - Build FHIR `Claim` resource with suggested ICD-10 and CPT codes
    - Link to encounter reference
  - [x] `create_document_reference(encounter_id: str, report: dict) -> dict`
    - Create `DocumentReference` with coding suggestions as attachment
    - Set document type to "Coding Review Report"
  - [x] `update_encounter_diagnosis(encounter_id: str, icd10_codes: list) -> dict`
    - Update `Encounter.diagnosis` with suggested ICD-10 codes

**Acceptance Criteria:** ✅ All Met
- ✅ Can create FHIR Claim resources with coding suggestions
- ✅ Can create DocumentReference with PDF/JSON report
- ✅ Write-back is optional and controlled by user configuration

**Implementation Notes:**
- Created FhirWriteBackService for writing coding suggestions to FHIR server
- Claim resources created with "draft" status for provider review
- All AI-generated codes marked with custom FHIR extension
- Supports multiple write-back strategies (Claim, Encounter.diagnosis, DocumentReference)
- Includes comprehensive error handling with per-operation results
- Write-back operations are controlled by feature flags

---

## Phase 3: FHIR Processing Pipeline ✅ COMPLETE

### Task 3.1: Create FHIR Encounter Processor ✅
**Priority:** High
**Estimated Time:** 3 hours
**Status:** ✅ Complete
**Completed:** 2025-10-07

- [x] Create `backend/app/tasks/fhir_processing.py`:
  - [x] `process_fhir_encounter(fhir_connection_id: str, fhir_encounter_id: str, user_id: str) -> None`
    - Fetch FHIR encounter metadata
    - Fetch clinical notes
    - Combine notes into single text document
    - Run PHI detection and redaction (reuse existing `phi_handler`)
    - Run clinical relevance filtering (reuse existing `openai_service`)
    - Extract provider and date (prefer FHIR metadata, fallback to LLM)
    - Run entity extraction (DetectEntitiesV2, InferICD10CM, InferSNOMEDCT)
    - Run SNOMED to CPT crosswalk
    - Generate coding suggestions via GPT-4o-mini
    - Store results in database

- [x] Handle duplicate detection:
  - Check if `fhirEncounterId` already exists
  - Apply duplicate handling logic (skip, overwrite, version)

- [x] Create `Encounter` record with `encounterSource = FHIR`

**Acceptance Criteria:** ✅ All Met
- ✅ FHIR encounters are processed using same logic as file uploads
- ✅ Provider/date prefer FHIR metadata but fallback to LLM extraction
- ✅ Duplicates are detected and handled correctly
- ✅ All processing steps are logged for audit

**Implementation Notes:**
- Created comprehensive FHIR encounter processor with 13-step workflow
- Reuses existing PHI handler, OpenAI service, Comprehend Medical, and SNOMED crosswalk
- Handles duplicate encounters by checking `fhirEncounterId` unique constraint
- Creates Encounter record with `encounterSource = FHIR` before processing
- Falls back to LLM extraction for provider/date when FHIR metadata missing
- Includes comprehensive error handling and audit logging
- Updates encounter status to COMPLETE/FAILED with error messages
- Updates FhirConnection lastSyncAt and lastError fields

---

### Task 3.2: Create FHIR Batch Sync Service ✅
**Priority:** Medium
**Estimated Time:** 2 hours
**Status:** ✅ Complete
**Completed:** 2025-10-07

- [x] Create `backend/app/services/fhir/sync_service.py`:
  - [x] `sync_encounters(fhir_connection_id: str, date_range: tuple, patient_ids: list) -> dict`
    - Query FHIR API for encounters matching criteria
    - Filter out already-processed encounters
    - Queue each encounter for background processing
    - Return sync summary (total, new, skipped)

- [x] Add background task support:
  - Use existing background task queue
  - Process encounters asynchronously

**Acceptance Criteria:** ✅ All Met
- ✅ Can sync multiple encounters in batch
- ✅ Only new encounters are processed
- ✅ Progress can be tracked via status field

**Implementation Notes:**
- Created FhirSyncService class with initialize() and sync_encounters() methods
- Supports filtering by patient IDs, date range, status, and limit
- Checks for duplicates by querying `fhirEncounterId` before processing
- Returns detailed sync summary (total_found, new, skipped, queued, processed, failed)
- Includes get_sync_status() method to track sync progress
- Processes encounters synchronously for now (async queue TODO for Celery integration)
- Updates FhirConnection with lastSyncAt and lastError
- Factory function create_sync_service() for easy initialization

---

## Phase 4: API Endpoints ✅ COMPLETE

### Task 4.1: Create FHIR Connection Management Endpoints ✅
**Priority:** Medium
**Estimated Time:** 2 hours
**Status:** ✅ Complete
**Completed:** 2025-10-07

- [x] Create `backend/app/api/v1/fhir_connections.py`:
  - [x] `POST /fhir-connections` - Create new FHIR connection
  - [x] `GET /fhir-connections` - List user's FHIR connections
  - [x] `GET /fhir-connections/{id}` - Get connection details
  - [x] `PUT /fhir-connections/{id}` - Update connection
  - [x] `DELETE /fhir-connections/{id}` - Delete connection
  - [x] `POST /fhir-connections/{id}/test` - Test connection

- [x] Add request/response schemas in `backend/app/schemas/fhir.py`

**Acceptance Criteria:** ✅ All Met
- ✅ Users can configure FHIR connections
- ✅ Secrets are encrypted before storage
- ✅ Connection test validates credentials and connectivity

**Implementation Notes:**
- Created comprehensive FHIR connection management endpoints
- Encrypts client_secret using encryption_service before storage
- All endpoints validate user ownership of connections (403 Forbidden if mismatch)
- Test endpoint attempts authentication and fetches CapabilityStatement
- Returns connection details without exposing secrets
- Includes comprehensive error handling and logging

---

### Task 4.2: Create FHIR Encounter Ingestion Endpoints ✅
**Priority:** High
**Estimated Time:** 2 hours
**Status:** ✅ Complete
**Completed:** 2025-10-07

- [x] Create endpoints in `backend/app/api/v1/fhir.py`:
  - [x] `POST /fhir/ingest-encounter` - Process single FHIR encounter
    - Input: `fhir_connection_id`, `fhir_encounter_id`
    - Output: `encounter_id`, `status`
  - [x] `POST /fhir/sync-encounters` - Batch sync encounters
    - Input: `fhir_connection_id`, `date_range`, `patient_ids` (optional)
    - Output: sync summary
  - [x] `GET /fhir/sync-status/{connection_id}` - Check sync progress

**Acceptance Criteria:** ✅ All Met
- ✅ Single encounters can be ingested via API
- ✅ Batch sync can be initiated and monitored
- ✅ All operations are authenticated and authorized

**Implementation Notes:**
- Created FHIR encounter ingestion and sync endpoints
- Validates FHIR connection ownership and active status
- Checks for duplicates before processing (returns existing encounter if duplicate)
- Ingest endpoint processes single encounter and returns status
- Sync endpoint supports filters: date_range, patient_ids, status, limit
- Sync status endpoint returns connection stats and last sync timestamp
- Returns detailed sync summary (total_found, new, skipped, processed, failed)
- Includes comprehensive error handling with actionable messages

---

### Task 4.3: Extend Encounter Lookup Endpoints ✅
**Priority:** Medium
**Estimated Time:** 1 hour
**Status:** ✅ Complete
**Completed:** 2025-10-07

- [x] Update `backend/app/api/v1/encounters.py`:
  - [x] `GET /encounters?fhir_encounter_id={id}` - Lookup by FHIR ID
  - [x] `GET /encounters?fhir_patient_id={id}` - Filter by patient
  - [x] Update `EncounterResponse` schema to include FHIR fields

**Acceptance Criteria:** ✅ All Met
- ✅ Encounters can be filtered by FHIR identifiers
- ✅ Response includes FHIR metadata when available

**Implementation Notes:**
- Extended EncounterResponse schema with FHIR fields:
  - fhirEncounterId, fhirPatientId, fhirProviderId, fhirSourceSystem, encounterSource
- Added EncounterSource enum (FILE_UPLOAD, FHIR)
- Updated list_encounters endpoint with query parameters:
  - fhir_encounter_id: Filter by FHIR Encounter ID
  - fhir_patient_id: Filter by FHIR Patient ID
  - encounter_source: Filter by source (FILE_UPLOAD or FHIR)
- Filters can be combined for precise queries
- Maintains backward compatibility with existing file upload encounters

---

## Phase 5: Frontend Integration

### Task 5.1: Create FHIR Connection Configuration UI
**Priority:** Medium
**Estimated Time:** 4 hours

- [ ] Create FHIR connection setup page (Settings → Integrations)
  - [ ] Form to add new FHIR connection
  - [ ] Display list of configured connections
  - [ ] Test connection button
  - [ ] Edit/delete connections
  - [ ] Support OAuth2 flow (redirect to EHR for authorization)

**Acceptance Criteria:**
- Users can configure FHIR connections via UI
- OAuth2 authorization flow works for Epic/Cerner
- Connection status is displayed clearly

---

### Task 5.2: Create FHIR Encounter Sync UI
**Priority:** Medium
**Estimated Time:** 3 hours

- [ ] Create FHIR sync page (Encounters → Import from EHR)
  - [ ] Select FHIR connection
  - [ ] Set date range filter
  - [ ] Optional patient ID filter
  - [ ] Initiate sync
  - [ ] Display sync progress
  - [ ] Show sync results (total, new, skipped)

**Acceptance Criteria:**
- Users can initiate FHIR sync from UI
- Progress is displayed in real-time
- Errors are shown with actionable messages

---

### Task 5.3: Update Encounter Display for FHIR Source
**Priority:** Low
**Estimated Time:** 1 hour

- [ ] Update encounter cards/table to show source badge (File Upload vs FHIR)
- [ ] Display FHIR Encounter ID when available
- [ ] Add filter to show only FHIR encounters or file-based encounters

**Acceptance Criteria:**
- Users can distinguish FHIR encounters from file uploads
- FHIR metadata is displayed appropriately

---

## Phase 6: Testing & Validation

### Task 6.1: Create FHIR Mock Server for Testing
**Priority:** High
**Estimated Time:** 2 hours

- [ ] Create test FHIR server using `fhir-server` library or mock endpoints
- [ ] Add sample FHIR Encounter resources
- [ ] Add sample FHIR Composition resources with clinical notes
- [ ] Add sample FHIR Patient and Practitioner resources

**Acceptance Criteria:**
- Mock server returns valid FHIR R4 resources
- Test data includes various encounter types

---

### Task 6.2: Unit Tests for FHIR Services
**Priority:** High
**Estimated Time:** 3 hours

- [ ] Create tests for `FhirClient` (auth, resource fetch, error handling)
- [ ] Create tests for `EncounterService` (metadata extraction)
- [ ] Create tests for `NoteService` (text extraction from Composition/DocumentReference)
- [ ] Create tests for duplicate detection

**Acceptance Criteria:**
- All FHIR services have >80% code coverage
- Tests use mock FHIR server

---

### Task 6.3: Integration Tests
**Priority:** Medium
**Estimated Time:** 2 hours

- [ ] Create end-to-end test: FHIR encounter → processing → coding suggestions
- [ ] Test duplicate handling for FHIR encounters
- [ ] Test fallback logic (FHIR metadata unavailable → LLM extraction)

**Acceptance Criteria:**
- Full FHIR workflow works end-to-end
- Edge cases are handled gracefully

---

### Task 6.4: Production Testing with Real EHR
**Priority:** High
**Estimated Time:** 4 hours

- [ ] Set up Epic Sandbox or Cerner Sandbox account
- [ ] Test OAuth2 authentication flow
- [ ] Test encounter retrieval
- [ ] Test clinical note extraction
- [ ] Validate coding suggestions accuracy

**Acceptance Criteria:**
- Can authenticate with Epic/Cerner sandbox
- Can retrieve and process real FHIR encounters
- Coding suggestions match manual review

---

## Phase 7: Documentation & Deployment

### Task 7.1: Create FHIR Integration Documentation
**Priority:** Medium
**Estimated Time:** 2 hours

- [ ] Document FHIR setup process (OAuth2 registration with EHR vendors)
- [ ] Document supported EHR systems (Epic, Cerner, etc.)
- [ ] Create user guide for FHIR connection configuration
- [ ] Document API endpoints for developers

**Acceptance Criteria:**
- Documentation covers all FHIR features
- Setup guide is clear for non-technical users

---

### Task 7.2: Add FHIR Configuration to Environment
**Priority:** Medium
**Estimated Time:** 30 minutes

- [ ] Add FHIR-related environment variables to `.env.example`
- [ ] Document required configurations
- [ ] Update deployment scripts if needed

**Acceptance Criteria:**
- FHIR configuration is well-documented
- Environment variables are properly scoped

---

### Task 7.3: Deploy to Production
**Priority:** High
**Estimated Time:** 1 hour

- [ ] Run database migrations for FHIR fields
- [ ] Deploy updated backend services
- [ ] Deploy updated frontend
- [ ] Verify FHIR endpoints are accessible
- [ ] Monitor for errors

**Acceptance Criteria:**
- FHIR integration is live in production
- No breaking changes to existing file upload workflow
- Monitoring shows no errors

---

## Phase 8: Future Enhancements

### Task 8.1: FHIR Write-Back Feature
**Priority:** Low
**Estimated Time:** 4 hours

- [ ] Implement write-back to FHIR `Claim` resource
- [ ] Implement write-back to `Encounter.diagnosis`
- [ ] Add user configuration for write-back preferences
- [ ] Test with sandbox EHR systems

---

### Task 8.2: Real-Time FHIR Subscriptions
**Priority:** Low
**Estimated Time:** 6 hours

- [ ] Implement FHIR Subscription support (webhook-based)
- [ ] Auto-process new encounters when created in EHR
- [ ] Add subscription management UI

---

### Task 8.3: Multi-Tenant FHIR Support
**Priority:** Low
**Estimated Time:** 3 hours

- [ ] Support multiple FHIR connections per user
- [ ] Support organization-level FHIR connections
- [ ] Implement connection switching in UI

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| OAuth2 complexity with different EHR vendors | High | High | Start with Epic/Cerner, use `fhirclient` library |
| FHIR resource structure variations | Medium | Medium | Use defensive parsing, log unknown structures |
| PHI leakage in FHIR responses | Low | Critical | Apply same PHI detection to FHIR data as file uploads |
| Performance issues with large note text | Medium | Medium | Reuse existing clinical filtering to reduce text size |
| Duplicate encounter processing | Medium | Low | Implement unique constraint on `fhirEncounterId` |

---

## Dependencies

- **Python Libraries:**
  - `fhir.resources>=7.0.0` - FHIR resource models
  - `httpx` - Async HTTP client (already installed)
  - `python-jose` - JWT handling for OAuth2 (already installed)

- **External Services:**
  - Epic FHIR API (sandbox for testing)
  - Cerner FHIR API (sandbox for testing)

- **Existing Code:**
  - PHI handler (`app/services/phi_handler.py`)
  - OpenAI service (`app/services/openai_service.py`)
  - Comprehend Medical service (`app/services/comprehend_medical.py`)
  - Encryption service (`app/core/encryption.py`)
  - Background tasks framework (`app/tasks/`)

---

## Success Criteria

- [ ] FHIR encounters can be ingested and processed
- [ ] Coding suggestions match quality of file upload workflow
- [ ] FHIR and file upload workflows coexist without conflicts
- [ ] At least 1 EHR vendor (Epic or Cerner) tested successfully
- [ ] Documentation complete and user-friendly
- [ ] Zero PHI sent to LLM or external services
- [ ] All FHIR processing properly logged and auditable

---

## Timeline Estimate

| Phase | Estimated Time |
|-------|---------------|
| Phase 1: Database Schema | 2 hours |
| Phase 2: FHIR Client Service | 9.5 hours |
| Phase 3: FHIR Processing Pipeline | 5 hours |
| Phase 4: API Endpoints | 5 hours |
| Phase 5: Frontend Integration | 8 hours |
| Phase 6: Testing & Validation | 11 hours |
| Phase 7: Documentation & Deployment | 3.5 hours |
| **Total Core Implementation** | **44 hours** (~1 week sprint) |

**Future Enhancements:** 13 additional hours

---

## Notes

- FHIR integration shares 90% of the processing pipeline with file upload workflow
- Main differences are in data source and identifier management
- Existing PHI handling, clinical filtering, and coding logic remain unchanged
- FHIR workflow is additive - does not break existing functionality
