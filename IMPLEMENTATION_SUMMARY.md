# Payer Fee Schedule Implementation Summary

**Feature Branch**: `feature/payer-fee-schedules`
**Implementation Date**: 2025-10-17
**Status**: Core Implementation Complete

## Overview

This implementation adds comprehensive payer-specific fee schedule management and CPT code optimization to RevRX. The system allows uploading insurance payer rate tables, automatically enriches CPT code suggestions with reimbursement rates, and provides revenue analysis for billing optimization.

## What Was Implemented

### Phase 1: Database Foundation ✅

**Files Modified:**
- `backend/prisma/schema.prisma` - Added 3 new models and updated 3 existing models

**New Database Models:**
1. **Payer** - Insurance company/payer management
   - Fields: name, payer_code, payer_type, website, phone, is_active, notes
   - Supports: Commercial, Medicare, Medicaid, TRICARE, Workers Comp, Self-Pay

2. **FeeSchedule** - Version-controlled fee schedules
   - Fields: name, effective_date, expiration_date, is_active, upload metadata
   - Relationships: belongs to Payer, uploaded by User

3. **FeeScheduleRate** - Individual CPT code rates
   - Fields: cpt_code, allowed_amount, facility/non-facility rates
   - Modifier rates: modifier_25, modifier_59, modifier_tc, modifier_pc
   - Authorization: requires_auth, auth_criteria
   - RVU data: work_rvu, practice_rvu, malpractice_rvu, total_rvu
   - Bundling support: bundling_rules (JSON)

**Enhanced Models:**
- **Encounter**: Added `payerId` field to link encounters to payers
- **Report**: Added payer-specific revenue analysis fields:
  - `payerId`, `feeScheduleId`
  - `billedRevenueEstimate`, `suggestedRevenueEstimate`, `optimizedRevenueEstimate`
  - `payerDenialRisks`, `authRequirements`, `bundlingWarnings`
- **User**: Added `uploadedFeeSchedules` relation

**Seed Script:**
- `backend/scripts/seed_payers.py` - Seeds 10 common payers (BCBS, UHC, Aetna, Cigna, Humana, Medicare, Medicaid, TRICARE, Workers Comp, Self-Pay)

### Phase 2: Service Layer ✅

**Files Created:**
- `backend/app/services/fee_schedule_service.py` - Core service (418 lines)
  - Pattern modeled after `SNOMEDCrosswalkService`
  - Features: In-memory caching, batch lookups, performance metrics
  - Methods:
    - `get_active_fee_schedule()` - Find active schedule for payer
    - `get_rate()` - Lookup single CPT code rate
    - `get_rates_batch()` - Efficient batch lookups
    - `calculate_revenue_estimate()` - Revenue calculations
    - `get_metrics()`, `clear_cache()` - Performance monitoring

- `backend/app/schemas/fee_schedule.py` - Pydantic schemas (163 lines)
  - Request/Response models for all API endpoints
  - Enums: `PayerTypeSchema`
  - Models: `PayerResponse`, `FeeScheduleResponse`, `FeeScheduleRateResponse`
  - Upload: `FeeScheduleUploadResponse` with validation error tracking
  - Revenue: `RevenueEstimateResponse`, `RateDetailResponse`

### Phase 3: API Endpoints ✅

**Files Created:**
- `backend/app/api/v1/fee_schedules.py` - Fee schedule management (250 lines)
  - `POST /{payer_id}/upload` - Upload CSV fee schedules
    - CSV validation with detailed error reporting
    - Supports all rate types and modifiers
    - Automatic deactivation of old schedules
    - Bulk insert optimization
  - `GET /{payer_id}/schedules` - List all schedules for payer
  - `GET /{fee_schedule_id}/rates` - Get rates with optional CPT filter

- `backend/app/api/v1/payers.py` - Payer management (218 lines)
  - `GET /` - List all payers (with filters)
  - `GET /{payer_id}` - Get specific payer
  - `POST /` - Create new payer
  - `PATCH /{payer_id}` - Update payer
  - `DELETE /{payer_id}` - Soft delete (checks for active schedules)

### Phase 4: Pipeline Integration ✅

**Files Modified:**
- `backend/app/tasks/phi_processing.py` (lines 443-502)
  - Added Step 6.46: Fee schedule lookup after SNOMED crosswalk
  - Enhances CPT suggestions with:
    - Allowed amounts and reimbursement rates
    - Authorization requirements
    - Payer-specific information
  - Calculates total revenue estimates
  - Logs performance metrics
  - Graceful degradation if payer not specified

**Integration Flow:**
```
SNOMED Crosswalk (Step 6.45)
  ↓
Extract CPT codes from suggestions
  ↓
Batch lookup fee schedule rates (NEW)
  ↓
Enhance suggestions with reimbursement data (NEW)
  ↓
Calculate revenue estimates (NEW)
  ↓
Continue to ICD-10 filtering (Step 6.5)
```

## CSV Upload Format

### Required Columns:
- `cpt_code` - CPT code (5 digits)
- `allowed_amount` - Maximum reimbursement (float)

### Optional Columns:
- `description` - Code description
- `facility_rate` - Hospital/facility rate
- `non_facility_rate` - Office rate
- `modifier_25_rate` - Significant E&M rate
- `modifier_59_rate` - Distinct procedure rate
- `modifier_tc_rate` - Technical component rate
- `modifier_pc_rate` - Professional component rate
- `requires_auth` - Boolean (true/false)
- `auth_criteria` - Authorization requirements
- `work_rvu`, `practice_rvu`, `malpractice_rvu`, `total_rvu` - RVU data
- `notes` - Additional information

### Example CSV:
```csv
cpt_code,description,allowed_amount,facility_rate,non_facility_rate,requires_auth
99213,Office visit 15 min,75.50,70.00,75.50,false
99214,Office visit 25 min,110.25,105.00,110.25,false
45378,Colonoscopy diagnostic,550.00,550.00,550.00,true
```

## Post-Merge Steps

### 1. Run Database Migration
```bash
cd backend
npx prisma migrate dev --name add_payer_fee_schedules
npx prisma generate
```

### 2. Seed Initial Payers
```bash
python scripts/seed_payers.py
```

### 3. Register API Routes
Add to your FastAPI app router registration:
```python
from app.api.v1 import fee_schedules, payers

app.include_router(fee_schedules.router, prefix="/api/v1")
app.include_router(payers.router, prefix="/api/v1")
```

### 4. Upload Fee Schedules
Use the API or admin interface to upload payer-specific fee schedules:
```bash
POST /api/v1/fee-schedules/{payer_id}/upload
Content-Type: multipart/form-data

file: schedule.csv
name: "2025 Q1 Fee Schedule"
effective_date: "2025-01-01"
```

### 5. Link Encounters to Payers
Update encounter creation to include payer:
```python
encounter = await prisma.encounter.create(
    data={
        "userId": user_id,
        "payerId": payer_id,  # NEW
        # ... other fields
    }
)
```

## Testing

### Manual Testing Checklist:
- [ ] Create payers via API
- [ ] Upload fee schedule CSV for each payer
- [ ] Verify CSV validation (invalid rows reported)
- [ ] Create encounter with payer_id
- [ ] Upload clinical note
- [ ] Verify PHI processing enriches CPT suggestions with rates
- [ ] Check revenue estimates in logs
- [ ] Query fee schedule rates via API
- [ ] Test payer management (CRUD operations)

### Unit Tests Needed (Future):
- `test_fee_schedule_service.py` - Service layer tests
- `test_fee_schedule_api.py` - API endpoint tests
- `test_payer_api.py` - Payer management tests

### Integration Tests Needed (Future):
- End-to-end encounter processing with payer
- Fee schedule upload validation
- Revenue calculation accuracy

## Known Limitations & Future Enhancements

### Current Limitations:
1. **No NCCI Edit Integration** - Bundling rules are stored as JSON but not automatically applied
2. **No Modifier Optimization** - System suggests codes but doesn't optimize modifier usage
3. **No Report Processor Enhancement** - report_processor.py not yet updated with payer-specific analysis
4. **No OpenAI Optimization** - AI prompts not yet enhanced with fee schedule data
5. **Manual Payer Selection** - Users must manually specify payer for encounters

### Future Enhancements (Phase 5-8):
1. **NCCI Compliance** (Phase 5)
   - Download quarterly NCCI edits
   - Implement bundling rule validation
   - Flag PTP (Procedure-to-Procedure) edits

2. **Modifier Optimization** (Phase 6)
   - Suggest appropriate modifiers (25, 59, X-modifiers)
   - Calculate modifier-adjusted reimbursement
   - Validate modifier appropriateness

3. **Report Enhancement** (Phase 7)
   - Update `report_processor.py` with payer-specific revenue breakdown
   - Add denial risk analysis
   - Include authorization requirements in reports

4. **AI Optimization** (Phase 8)
   - Enhance OpenAI prompts with fee schedule context
   - Optimize code selection for maximum appropriate reimbursement
   - Provide scenario comparisons

5. **UI Development** (Phase 9)
   - Fee schedule upload wizard
   - Payer management interface
   - Revenue optimization dashboard
   - Charge review queue

## Architecture Patterns

### Service Layer Pattern
Modeled after `SNOMEDCrosswalkService`:
- Dataclass for results (`CPTRate`)
- Prisma client injection
- In-memory caching with metrics
- Batch lookup optimization
- Singleton factory pattern

### API Pattern
Following `encounters.py` upload pattern:
- FastAPI with `UploadFile`
- CSV parsing with `DictReader`
- Row-level validation with error collection
- Bulk database operations
- Structured logging

### Integration Pattern
Similar to SNOMED crosswalk integration:
1. Extract candidate codes from AI/AWS
2. Batch lookup in service
3. Enhance suggestions with additional data
4. Pass enriched data to downstream processing
5. Log performance metrics

## Performance Considerations

### Caching Strategy:
- In-memory cache for rate lookups
- Cache key: `{payer_id}:{cpt_code}:{as_of_date}`
- Cache hit rate logged in metrics
- Manual cache clearing available

### Database Optimization:
- Compound indexes on frequently queried fields
- `@@unique([feeScheduleId, cptCode])` for rate lookups
- `@@index([payerId, effectiveDate])` for schedule queries
- Batch inserts for rate uploads

### Query Efficiency:
- Batch lookups preferred over individual queries
- Single query to get active fee schedule
- `find_many` with `in` clause for batch rates
- Metrics tracking (lookups, cache hits, DB queries)

## Security & Compliance

### HIPAA Compliance:
- No PHI in fee schedules
- Audit logs for all upload operations
- User authentication required for all endpoints
- Soft deletes for data retention

### Data Validation:
- CPT code format validation (5 digits minimum)
- Positive amount validation
- Date range validation (effective < expiration)
- Duplicate payer code prevention

### Access Control:
- All endpoints require authentication
- User ID tracked for uploads
- Payer ownership not enforced (admin feature)

## Dependencies

### New Python Packages:
- `python-dateutil` (for date parsing) - likely already installed
- All other dependencies already in project

### No New External Services:
- Uses existing Prisma/PostgreSQL setup
- Uses existing FastAPI framework
- No new AWS services required

## File Summary

### Created (8 files):
1. `backend/scripts/seed_payers.py` (100 lines)
2. `backend/app/services/fee_schedule_service.py` (418 lines)
3. `backend/app/schemas/fee_schedule.py` (163 lines)
4. `backend/app/api/v1/fee_schedules.py` (250 lines)
5. `backend/app/api/v1/payers.py` (218 lines)
6. `IMPLEMENTATION_SUMMARY.md` (this file)
7. `backend/docs/FEE_SCHEDULE_ARCHITECTURE_RESEARCH.md` (2111 lines) - existing
8. `research/RESEARCH_SUMMARY.md` (344 lines) - existing

### Modified (2 files):
1. `backend/prisma/schema.prisma` (+140 lines)
2. `backend/app/tasks/phi_processing.py` (+60 lines)

### Total Implementation:
- **~1,349 new lines of production code**
- **~180 lines of schema changes**
- **8 new files created**
- **2 files modified**

## Success Metrics (Expected)

### Operational:
- **Rate lookup time**: < 50ms (cached), < 200ms (uncached)
- **CSV upload processing**: ~100 rates/second
- **Cache hit rate**: > 80% in production
- **API response time**: < 500ms for list operations

### Business Impact:
- **Revenue visibility**: Immediate reimbursement estimates
- **Authorization alerts**: Pre-emptive auth requirement flagging
- **Code optimization**: Foundation for AI-powered suggestions
- **Payer management**: Centralized rate table management

## Questions & Support

### Common Questions:

**Q: Do I need a CPT code license?**
A: Yes, CPT codes are copyrighted by the AMA. Display appropriate copyright notices in your UI.

**Q: How often should fee schedules be updated?**
A: Annually at minimum. Medicare updates January 1st. Commercial payers vary.

**Q: Can I have multiple active schedules for one payer?**
A: Yes, using effective/expiration dates for version control.

**Q: What happens if no fee schedule exists for a payer?**
A: System degrades gracefully. Codes are still suggested, just without rate data.

**Q: How do I handle modifier combinations?**
A: Store common modifiers in separate rate columns. Complex rules go in `bundling_rules` JSON field.

### References:
- Research Document: `/research/payer-fee-schedule-cpt-optimization-best-practices.md`
- Architecture Analysis: `backend/docs/FEE_SCHEDULE_ARCHITECTURE_RESEARCH.md`
- Quick Reference: `research/RESEARCH_SUMMARY.md`

---

**Implementation completed by**: Claude Code
**Review status**: Awaiting code review
**Deployment readiness**: Core features complete, tests pending
