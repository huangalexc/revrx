# SNOMED → CPT Crosswalk Feature Implementation

## Phase 1: AWS Comprehend Medical Integration Enhancement

### 1.1 Add ICD-10 Extraction ✅
- [x] Update `app/services/comprehend_medical.py` to add `infer_icd10_cm()` method
- [x] Create ICD10Entity class to represent ICD-10-CM codes with confidence scores
- [x] Add error handling and retry logic for InferICD10CM API calls
- [x] Add logging for ICD-10 extraction results

### 1.2 Add SNOMED CT Extraction ✅
- [x] Update `app/services/comprehend_medical.py` to add `infer_snomed_ct()` method
- [x] Create SNOMEDEntity class to represent SNOMED CT procedure concepts
- [x] Add error handling and retry logic for InferSNOMEDCT API calls
- [x] Add logging for SNOMED extraction results

### 1.3 Enhanced Entity Extraction (Optional) ✅
- [x] Add `detect_entities_v2()` method for medications, tests, and additional clinical context (already existed)
- [x] Create entity classes for medications, tests, and clinical attributes (MedicalEntity class already existed)
- [x] Integrate entity extraction into PHI processing workflow

## Phase 2: SNOMED → CPT Crosswalk System

### 2.1 Crosswalk Data Management ✅
- [x] Research and download CMS SNOMED CT to CPT crosswalk table
  - **Note**: No free CMS crosswalk exists. Using UMLS-based approach with expert-validated sample data
  - See `backend/docs/SNOMED_CPT_CROSSWALK.md` for details on data sources
- [x] Create database schema for crosswalk mappings (SNOMEDCrosswalk model)
  - Schema already exists in `backend/prisma/schema.prisma`
  - Includes ICD10Code, SNOMEDCode, and SNOMEDCrosswalk models
- [x] Write migration script to load crosswalk data into database
  - Created `backend/scripts/seed_snomed_crosswalk.py`
  - Supports sample data (16 expert-validated mappings) and custom CSV import
- [x] Add indexes on SNOMED codes for fast lookup
  - Indexes on both `snomedCode` and `cptCode` fields
  - Unique constraint on `(snomedCode, cptCode)` combination

### 2.2 Crosswalk Service Implementation ✅
- [x] Create `app/services/snomed_crosswalk.py` service
  - Comprehensive service with `SNOMEDCrosswalkService` class
  - Includes `CPTMapping` dataclass for structured results
  - Full error handling and structured logging
- [x] Implement `get_cpt_mappings(snomed_code)` method with caching
  - Single code lookup with configurable confidence threshold
  - Automatic cache integration
  - Results sorted by confidence (highest first)
- [x] Add fallback logic for SNOMED codes without direct CPT mappings
  - Returns empty list for unmapped codes
  - Tracks misses in metrics for monitoring
  - Logs all lookup attempts for debugging
- [x] Implement batch crosswalk lookup for multiple SNOMED codes
  - `get_cpt_mappings_batch()` method for efficient bulk lookups
  - Single database query for all uncached codes
  - Returns dict mapping SNOMED → List[CPTMapping]
- [x] Add telemetry for crosswalk hit/miss rates
  - `CrosswalkMetrics` class tracks all performance metrics
  - Cache hit/miss rates, DB hit/miss rates
  - Batch lookup statistics
  - `get_metrics()` and `log_performance_summary()` methods

### 2.3 Caching Layer ✅
- [x] Implement in-memory LRU cache for frequently accessed mappings
  - Simple LRU cache using Python dict (ordered in 3.7+)
  - Configurable cache size (default 1000 entries)
  - Automatic eviction of oldest entries when full
  - Cache stats available via `get_cache_stats()`
- [x] Add cache warming on application startup
  - `warm_cache()` method pre-loads top N most common SNOMED codes
  - Automatically called on service initialization
  - Uses batch lookup for efficiency
  - Configurable number of codes to warm (default 100)
- [x] Monitor cache performance and adjust size as needed
  - Real-time cache utilization tracking
  - Hit rate monitoring and logging
  - `get_cache_stats()` provides current size and utilization
  - Metrics include cache hits, misses, and hit rate percentage
- [x] Comprehensive unit tests created
  - `app/services/test_snomed_crosswalk.py` with 20+ test cases
  - Tests for caching, batch lookup, metrics, cache eviction
  - Mock database for isolated testing

## Phase 3: Database Schema Updates ✅

### 3.1 New Models ✅
- [x] Create `ICD10Code` model (similar to BillingCode but for diagnoses)
- [x] Create `SNOMEDCode` model for extracted procedure concepts
- [x] Create `SNOMEDCrosswalk` model for SNOMED → CPT mappings
- [x] Add relations to Encounter model
- [x] Run `prisma db push` to apply schema changes

### 3.2 Extend Existing Models ✅
- [x] Add `extractedIcd10Codes` JSON field to Report model
- [x] Add `extractedSnomedCodes` JSON field to Report model
- [x] Add `cptSuggestions` JSON field to Report model (from crosswalk)

## Phase 4: Processing Pipeline Updates

### 4.1 Update PHI Processing Task ✅
- [x] Integrate ICD-10 extraction into `app/tasks/phi_processing.py`
  - Extraction already implemented, now stores codes in database
  - Handles extraction errors gracefully with warnings
- [x] Integrate SNOMED CT extraction into processing pipeline
  - Extraction already implemented, now stores codes in database
  - Includes structured logging for monitoring
- [x] Store extracted ICD-10 codes in database
  - Creates ICD10Code records for each extracted code
  - Stores: code, description, category, type, score, text offsets
  - Links to Encounter via encounterId
  - **ICD-10 Filtering**: Uses fuzzy text matching with DetectEntitiesV2 diagnosis/symptom entities
    - Filters to MEDICAL_CONDITION entities with DIAGNOSIS or SYMPTOM trait (excludes NEGATION)
    - Matches InferICD10CM codes to diagnosis/symptom entities with fuzzy matching (threshold 0.6)
    - Increases recall while letting LLM handle final billability logic
- [x] Store extracted SNOMED codes in database
  - Creates SNOMEDCode records for each extracted code
  - Stores: code, description, category, type, score, text offsets
  - Links to Encounter via encounterId
- [x] Perform SNOMED → CPT crosswalk and store suggestions
  - Integrates SNOMEDCrosswalkService into processing pipeline
  - Batch lookup for all extracted SNOMED codes
  - Top 3 CPT suggestions per SNOMED code
  - **SNOMED Filtering**: Uses fuzzy text matching with DetectEntitiesV2 procedure entities (score > 0.5)
    - Filters SNOMED codes to only TEST_TREATMENT_PROCEDURE category
    - Matches to high-confidence procedure entities instead of relying on InferSNOMEDCT scores
    - Resolves issue where InferSNOMEDCT gives low confidence even for valid procedures
  - Stores in Report.cptSuggestions with full metadata:
    - CPT code and description
    - Mapping confidence and type (EXACT, BROADER, etc.)
    - Source SNOMED code and clinical text
    - AWS Comprehend confidence scores
  - Logs crosswalk service metrics for monitoring
- [x] Update Report model with extracted data
  - extractedIcd10Codes: JSON array of ICD-10 codes from AWS
  - extractedSnomedCodes: JSON array of SNOMED codes from AWS
  - cptSuggestions: JSON array of CPT codes from crosswalk
  - All with source attribution and confidence scores
- [x] Enhanced audit logging
  - Tracks ICD-10 and SNOMED extraction counts
  - Logs crosswalk suggestion counts
  - Includes metrics in report generation audit log

### 4.2 Relevant Context Extraction
- [ ] Implement context extraction based on entity offsets (Option A)
- [ ] Extract text snippets around diagnostic and procedure entities
- [ ] Store relevant context in structured format
- [ ] Optional: Add LLM-based summarization for complex relationships (Option B)

### 4.3 Update LLM Prompt
- [ ] Modify `app/services/prompt_templates.py` to include:
  - Extracted ICD-10 codes from Comprehend Medical
  - Extracted SNOMED procedure codes
  - CPT suggestions from crosswalk
  - Relevant context snippets
- [ ] Restructure prompt to focus LLM on validation/refinement rather than extraction
- [ ] Add instructions for LLM to justify additions/modifications to suggested codes
- [ ] Update JSON schema to include new structured input fields

## Phase 5: API Updates

### 5.1 Report Endpoints
- [ ] Update report response schema to include ICD-10 codes
- [ ] Update report response schema to include SNOMED codes
- [ ] Update report response schema to include CPT suggestions from crosswalk
- [ ] Add endpoint to retrieve detailed code provenance (Comprehend vs LLM)

### 5.2 Encounter Endpoints
- [ ] Add endpoint to view extracted clinical entities (ICD-10, SNOMED, medications, tests)
- [ ] Add filtering by entity type and confidence threshold
- [ ] Return entity offsets for highlighting in UI

## Phase 6: Testing & Validation

### 6.1 Unit Tests
- [ ] Test ICD-10 extraction with sample clinical notes
- [ ] Test SNOMED extraction with procedure-heavy notes
- [ ] Test crosswalk service with known SNOMED codes
- [ ] Test cache performance and eviction
- [ ] Test end-to-end processing with new pipeline

### 6.2 Integration Tests
- [ ] Test full workflow: upload → extract → crosswalk → LLM → report
- [ ] Verify all extracted codes are properly stored and retrieved
- [ ] Test edge cases (no procedures, no diagnoses, unknown SNOMED codes)

### 6.3 Performance Testing
- [ ] Benchmark Comprehend Medical API latency
- [ ] Measure crosswalk lookup performance
- [ ] Profile total processing time increase
- [ ] Optimize slow paths if needed

## Phase 7: Frontend Updates (Optional)

### 7.1 Report Display
- [ ] Add section showing extracted ICD-10 codes with confidence scores
- [ ] Add section showing extracted SNOMED codes
- [ ] Show CPT suggestions from crosswalk separately from LLM suggestions
- [ ] Add visual indicators for code provenance (AWS vs LLM)

### 7.2 Entity Highlighting
- [ ] Highlight entities in clinical note text based on offsets
- [ ] Color-code by entity type (diagnosis, procedure, medication, etc.)
- [ ] Show confidence scores on hover

## Phase 8: Documentation & Deployment

### 8.1 Documentation
- [ ] Document new Comprehend Medical API integrations
- [ ] Document SNOMED → CPT crosswalk system architecture
- [ ] Update API documentation with new endpoints and response schemas
- [ ] Add developer guide for crosswalk data updates

### 8.2 Deployment
- [ ] Add AWS Comprehend Medical permissions to IAM role
- [ ] Load crosswalk data into production database
- [ ] Deploy backend with new processing pipeline
- [ ] Monitor error rates and processing times
- [ ] Set up alerts for Comprehend Medical API errors

## Phase 9: Cost Optimization & Monitoring

### 9.1 Cost Tracking
- [ ] Track Comprehend Medical API call costs (InferICD10CM, InferSNOMEDCT)
- [ ] Compare new processing costs vs. old LLM-only approach
- [ ] Optimize batch sizes to reduce per-call overhead

### 9.2 Monitoring
- [ ] Add metrics for ICD-10 extraction success rate
- [ ] Add metrics for SNOMED extraction success rate
- [ ] Monitor crosswalk hit rate (% of SNOMED codes with CPT mappings)
- [ ] Track LLM token usage reduction from structured input
- [ ] Alert on low confidence scores or extraction failures
