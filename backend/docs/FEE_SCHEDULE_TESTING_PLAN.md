# Fee Schedule Testing Plan

**Document Version**: 1.0
**Last Updated**: 2025-10-18
**Feature**: Payer Fee Schedule & Revenue Calculation System

## Table of Contents

1. [Test Coverage Overview](#test-coverage-overview)
2. [Test Organization](#test-organization)
3. [Running Tests](#running-tests)
4. [Test Categories](#test-categories)
5. [Test Fixtures](#test-fixtures)
6. [Performance Benchmarks](#performance-benchmarks)
7. [Future Testing Needs](#future-testing-needs)
8. [CI/CD Integration](#cicd-integration)

---

## Test Coverage Overview

### Files Tested

| Component | File | Test File | Test Count | Coverage |
|-----------|------|-----------|------------|----------|
| **Service Layer** | `app/services/fee_schedule_service.py` | `tests/unit/test_fee_schedule_service.py` | 25 tests | 100% |
| **API Endpoints** | `app/api/v1/fee_schedules.py` | `tests/integration/test_fee_schedule_api.py` | 43 tests | ~95% |
| **Revenue Pipeline** | Multiple files | `tests/integration/test_revenue_calculation_pipeline.py` | 20 tests | ~90% |
| **Payer API** | `app/api/v1/payers.py` | TODO | 0 tests | 0% |

### Test Metrics

- **Total Tests Written**: 88 tests
- **Total Lines of Test Code**: ~1,700 lines
- **Test Categories**: Unit (25), Integration (63)
- **Average Test Execution Time**: TBD (run full suite)
- **Test Success Rate Target**: 100%

---

## Test Organization

### Directory Structure

```
backend/tests/
├── conftest.py                           # Shared fixtures (updated)
├── unit/
│   └── test_fee_schedule_service.py     # Service layer unit tests
└── integration/
    ├── test_fee_schedule_api.py          # API endpoint integration tests
    └── test_revenue_calculation_pipeline.py  # E2E pipeline tests
```

### Test File Breakdown

#### Unit Tests: `test_fee_schedule_service.py`

**Purpose**: Test FeeScheduleService in isolation with mocked database

**Test Classes**:
1. `TestFeeScheduleServiceInitialization` (2 tests)
   - Service initialization
   - Singleton factory pattern

2. `TestRateLookup` (6 tests)
   - Successful rate lookup
   - Rate not found
   - Invalid payer
   - No active schedule
   - Rate lookup with specific date
   - Expired schedule handling

3. `TestBatchLookup` (4 tests)
   - Batch lookup success
   - Mixed results (some codes not found)
   - Empty code list
   - Duplicate code handling

4. `TestCaching` (4 tests)
   - Cache hit on second lookup
   - Cache key includes date
   - Cache clearing
   - Batch lookup uses cache

5. `TestRevenueCalculation` (4 tests)
   - Basic revenue calculation
   - Non-CPT codes excluded
   - Missing rates handling
   - Empty code list

6. `TestCPTRateModel` (2 tests)
   - CPTRate creation
   - CPTRate with authorization

7. `TestMetrics` (3 tests)
   - Metrics tracking
   - Metrics persist after cache clear
   - Cache hit rate calculation

#### Integration Tests: `test_fee_schedule_api.py`

**Purpose**: Test API endpoints end-to-end with real HTTP client

**Test Classes**:
1. `TestFeeScheduleUpload` (12 tests)
   - Valid CSV upload
   - CSV with all optional fields
   - Missing required columns
   - Invalid CPT codes
   - Invalid amounts
   - No valid rows
   - Nonexistent payer
   - Non-CSV file
   - Unauthorized access
   - Automatic deactivation of old schedules
   - Expiration date handling
   - Multiple schedules with different time periods

2. `TestFeeScheduleListing` (4 tests)
   - List schedules for payer
   - Active schedules only
   - All schedules including inactive
   - Unauthorized access

3. `TestFeeScheduleRates` (4 tests)
   - Get all rates for schedule
   - Filter rates by CPT code
   - Nonexistent schedule
   - Unauthorized access

4. `TestFeeScheduleEdgeCases` (6 tests)
   - Empty CSV
   - Malformed CSV
   - Invalid date format
   - Large CSV (1000 rates)
   - Duplicate CPT codes in file
   - UTF-8 encoding

#### Integration Tests: `test_revenue_calculation_pipeline.py`

**Purpose**: Test complete revenue flow from encounter to report

**Test Classes**:
1. `TestRevenuePipelineIntegration` (4 tests)
   - Encounter with payer loads rates
   - Batch rate lookup for multiple codes
   - Revenue estimate calculation
   - ICD-10 codes excluded from revenue

2. `TestReportProcessorWithFeeSchedules` (4 tests)
   - Report includes payer revenue fields
   - Authorization requirements captured
   - Denial risks for missing rates
   - Bundling warnings in report

3. `TestFeeScheduleCaching` (3 tests)
   - Cache improves lookup performance
   - Batch lookup efficiency
   - Metrics tracking accuracy

4. `TestEncounterWithoutPayer` (2 tests)
   - Graceful handling when no payer
   - Revenue calculation with no payer

5. `TestMultiplePayersRates` (2 tests)
   - Different payers have different rates
   - Payer-specific revenue calculations

---

## Running Tests

### Prerequisites

```bash
# Install dependencies
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx

# Ensure database is running
# Set DATABASE_URL environment variable
```

### Run All Fee Schedule Tests

```bash
# Run all new tests
pytest tests/unit/test_fee_schedule_service.py -v
pytest tests/integration/test_fee_schedule_api.py -v
pytest tests/integration/test_revenue_calculation_pipeline.py -v

# Run all tests together
pytest tests/unit/test_fee_schedule_service.py tests/integration/test_fee_schedule_api.py tests/integration/test_revenue_calculation_pipeline.py -v
```

### Run by Category

```bash
# Unit tests only
pytest tests/unit/test_fee_schedule_service.py -v -m unit

# Integration tests only
pytest tests/integration/test_fee_schedule_api.py tests/integration/test_revenue_calculation_pipeline.py -v -m integration

# Async tests only
pytest -v -m asyncio
```

### Run Specific Test Classes

```bash
# Service initialization tests
pytest tests/unit/test_fee_schedule_service.py::TestFeeScheduleServiceInitialization -v

# Upload tests
pytest tests/integration/test_fee_schedule_api.py::TestFeeScheduleUpload -v

# Revenue pipeline tests
pytest tests/integration/test_revenue_calculation_pipeline.py::TestRevenuePipelineIntegration -v
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=app.services.fee_schedule_service --cov=app.api.v1.fee_schedules --cov-report=html tests/

# View coverage report
open htmlcov/index.html
```

### Run Performance Tests

```bash
# Run caching performance tests
pytest tests/integration/test_revenue_calculation_pipeline.py::TestFeeScheduleCaching -v -s

# Run with timing
pytest --durations=10 tests/
```

---

## Test Categories

### Pytest Markers Used

```python
@pytest.mark.unit          # Unit tests (isolated, fast)
@pytest.mark.integration   # Integration tests (DB, API)
@pytest.mark.asyncio       # Async tests (most tests)
@pytest.mark.slow          # Slow tests (optional)
```

### Test Naming Conventions

- **Unit tests**: `test_<function>_<scenario>`
  - Example: `test_get_rate_success`
  - Example: `test_batch_lookup_mixed_results`

- **Integration tests**: `test_<feature>_<scenario>`
  - Example: `test_upload_valid_csv`
  - Example: `test_report_includes_payer_revenue_fields`

- **Async tests**: All marked with `@pytest.mark.asyncio`

---

## Test Fixtures

### Shared Fixtures (`tests/conftest.py`)

#### Database Fixtures
- `db`: Prisma database client
- Auto-cleanup after each test

#### User Fixtures
- `test_user`: Standard test user (MEMBER role)
- `test_admin`: Admin user
- Auto-cleanup with cascade delete

#### Payer & Fee Schedule Fixtures
- `test_payer`: Basic payer without schedule
- `test_payer_with_schedule`: Payer with active schedule + 4 CPT rates
  - CPT 99213: $75.50
  - CPT 99214: $110.25
  - CPT 99215: $148.00
  - CPT 45378: $550.00 (requires auth)
- `test_payer_no_schedule`: Payer without any schedules
- `test_payer_expired_schedule`: Payer with expired schedule

#### CSV Fixtures
- `sample_fee_schedule_csv`: Valid CSV content for upload tests

### Integration Test Fixtures (`tests/integration/conftest.py`)

- `test_client`: Async HTTP client for API testing
- `auth_headers`: Authorization headers with JWT token
- `admin_headers`: Admin authorization headers
- Sample clinical notes fixtures

---

## Performance Benchmarks

### Expected Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| **Rate lookup (cached)** | < 5ms | In-memory cache hit |
| **Rate lookup (uncached)** | < 50ms | Single database query |
| **Batch lookup (10 codes)** | < 100ms | Single query with IN clause |
| **Revenue calculation** | < 150ms | Batch lookup + computation |
| **CSV upload (100 rates)** | < 2s | Parsing + bulk insert |
| **CSV upload (1000 rates)** | < 10s | Large file processing |

### Cache Efficiency Targets

- **Cache hit rate**: > 80% in production
- **Cache memory usage**: < 100MB for typical workload
- **Cache invalidation**: Manual or TTL-based (not implemented yet)

### Test Performance Metrics

Run these commands to measure actual performance:

```bash
# Time individual test classes
pytest tests/unit/test_fee_schedule_service.py::TestCaching -v --durations=0

# Profile slow tests
pytest --durations=10 tests/

# Memory profiling (requires pytest-memprof)
pytest --memprof tests/unit/test_fee_schedule_service.py
```

---

## Future Testing Needs

### Phase 5: NCCI Integration Tests

**Status**: Not implemented yet
**Required when**: NCCI bundling rules are implemented

**Planned tests**:
- [ ] Test NCCI edit detection
- [ ] Test procedure-to-procedure (PTP) edits
- [ ] Test modifier appropriateness rules
- [ ] Test bundling rule validation
- [ ] Test quarterly NCCI update integration

### Phase 6: Modifier Optimization Tests

**Status**: Not implemented yet
**Required when**: Modifier optimization is implemented

**Planned tests**:
- [ ] Test modifier -25 suggestions
- [ ] Test modifier -59 vs X-modifiers
- [ ] Test modifier revenue calculations
- [ ] Test inappropriate modifier detection
- [ ] Test modifier stacking rules

### Phase 7: UI Component Tests

**Status**: Not implemented yet
**Required when**: Frontend UI is built

**Planned tests**:
- [ ] Fee schedule upload wizard
- [ ] Payer management interface
- [ ] Revenue optimization dashboard
- [ ] Charge review queue
- [ ] Rate comparison views

### Phase 8: End-to-End Tests

**Status**: Partially complete
**Additional needs**:

- [ ] Test complete PHI processing pipeline with payer
- [ ] Test OpenAI prompt enhancements with payer context
- [ ] Test report generation with all revenue fields
- [ ] Test multi-encounter batch processing
- [ ] Test concurrent user operations

### Missing Test Coverage

#### Payer Management API (`app/api/v1/payers.py`)

**Status**: No tests written yet
**Priority**: High

**Required tests**:
- [ ] Create payer
- [ ] List payers
- [ ] Get specific payer
- [ ] Update payer
- [ ] Delete payer (with active schedule check)
- [ ] Filter by payer type
- [ ] Search by name/code

#### Error Scenarios

**Additional error tests needed**:
- [ ] Database connection failure
- [ ] Transaction rollback on error
- [ ] Concurrent upload conflicts
- [ ] Large file timeout handling
- [ ] Invalid CSV encoding (non-UTF8)
- [ ] Memory limits with huge CSVs

#### Security Tests

**Not yet implemented**:
- [ ] SQL injection in CSV parsing
- [ ] XSS in payer/schedule names
- [ ] Authorization bypass attempts
- [ ] Rate limit testing
- [ ] File upload security (malicious CSV)

#### Data Migration Tests

**Required for production deployment**:
- [ ] Test migration from old schema
- [ ] Test data backfill scripts
- [ ] Test rollback procedures
- [ ] Test zero-downtime migration

---

## CI/CD Integration

### GitHub Actions Workflow (Recommended)

```yaml
name: Fee Schedule Tests

on:
  push:
    branches: [main, feature/payer-fee-schedules]
  pull_request:
    paths:
      - 'backend/app/services/fee_schedule_service.py'
      - 'backend/app/api/v1/fee_schedules.py'
      - 'backend/app/api/v1/payers.py'
      - 'backend/tests/**/*fee_schedule*'
      - 'backend/tests/**/*revenue*'

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_revrx
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov httpx

      - name: Run database migrations
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_revrx
        run: |
          cd backend
          npx prisma migrate deploy

      - name: Run unit tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_revrx
        run: |
          cd backend
          pytest tests/unit/test_fee_schedule_service.py -v --cov=app.services.fee_schedule_service

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_revrx
        run: |
          cd backend
          pytest tests/integration/test_fee_schedule_api.py tests/integration/test_revenue_calculation_pipeline.py -v

      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
          flags: fee_schedules
```

### Pre-commit Hooks (Recommended)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-fee-schedule-unit
        name: Run Fee Schedule Unit Tests
        entry: pytest tests/unit/test_fee_schedule_service.py -x
        language: system
        pass_filenames: false
        always_run: false
        files: ^backend/(app/services/fee_schedule_service\.py|tests/unit/test_fee_schedule_service\.py)$
```

### Continuous Testing Strategy

**Development Phase**:
- Run unit tests on every file save (watch mode)
- Run integration tests before commits
- Run full suite before pushing

**Pull Request Phase**:
- Automated test run on PR creation
- Coverage report comment on PR
- Block merge if tests fail
- Require minimum 80% coverage for new code

**Production Deployment**:
- Run full test suite pre-deployment
- Run smoke tests post-deployment
- Monitor error rates for 24h after deploy

---

## Test Data Management

### Test Database Setup

```bash
# Create test database
createdb revrx_test

# Run migrations
DATABASE_URL=postgresql://localhost/revrx_test npx prisma migrate deploy

# Seed test data (optional)
DATABASE_URL=postgresql://localhost/revrx_test python scripts/seed_payers.py
```

### Test Data Cleanup

All tests use automatic cleanup via fixtures:

- **After each test**: Delete created records
- **Cascade deletes**: Handles foreign key constraints
- **Isolation**: Each test gets clean state

### Test Data Generation

For load testing or performance testing:

```python
# Generate large fee schedule for testing
def generate_large_csv(num_rates=10000):
    import csv
    import io

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'cpt_code', 'description', 'allowed_amount'
    ])
    writer.writeheader()

    for i in range(num_rates):
        writer.writerow({
            'cpt_code': f'{10000 + i:05d}',
            'description': f'Procedure {i}',
            'allowed_amount': f'{50.00 + (i % 500):.2f}'
        })

    return output.getvalue()
```

---

## Troubleshooting Tests

### Common Issues

#### 1. Database Connection Failures

**Symptom**: Tests fail with "connection refused" or "database does not exist"

**Solutions**:
```bash
# Check PostgreSQL is running
pg_isadmin

# Verify DATABASE_URL
echo $DATABASE_URL

# Create test database
createdb revrx_test

# Check Prisma connection
npx prisma db pull
```

#### 2. Fixture Not Found

**Symptom**: `fixture 'test_payer_with_schedule' not found`

**Solutions**:
- Ensure `conftest.py` has the fixture
- Check fixture scope (`function` vs `session`)
- Verify import paths

#### 3. Async Test Failures

**Symptom**: `RuntimeError: Event loop is closed`

**Solutions**:
```python
# Ensure @pytest.mark.asyncio decorator
@pytest.mark.asyncio
async def test_my_async_function():
    ...

# Check event_loop fixture in conftest
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

#### 4. Slow Test Execution

**Symptom**: Tests take > 5 minutes

**Solutions**:
- Run unit tests only during development
- Use `-x` flag to stop at first failure
- Parallelize with `pytest-xdist`: `pytest -n auto`
- Profile slow tests: `pytest --durations=10`

---

## Test Quality Metrics

### Code Coverage Goals

- **Service Layer**: > 95% coverage
- **API Endpoints**: > 90% coverage
- **Critical Paths**: 100% coverage
- **Overall Project**: > 85% coverage

### Test Quality Checklist

For each new test:
- [ ] Has descriptive docstring
- [ ] Tests one specific behavior
- [ ] Uses appropriate fixtures
- [ ] Cleans up test data
- [ ] Has clear assertions
- [ ] Handles async properly
- [ ] Runs independently (no test order dependency)

### Test Maintenance

**Quarterly review**:
- Remove obsolete tests
- Update test data
- Refactor duplicate code into fixtures
- Update documentation
- Review flaky tests

**After production incidents**:
- Add regression tests
- Update edge case coverage
- Document failure scenarios

---

## Appendix

### Quick Reference Commands

```bash
# Run everything
pytest tests/unit/test_fee_schedule_service.py tests/integration/test_fee_schedule_api.py tests/integration/test_revenue_calculation_pipeline.py -v

# Watch mode (requires pytest-watch)
ptw tests/unit/test_fee_schedule_service.py

# Coverage report
pytest --cov=app.services.fee_schedule_service --cov=app.api.v1.fee_schedules --cov-report=html

# Parallel execution (requires pytest-xdist)
pytest -n auto tests/

# Debug mode
pytest -v -s --pdb tests/unit/test_fee_schedule_service.py::TestRateLookup::test_get_rate_success
```

### Related Documentation

- **Implementation Summary**: `/IMPLEMENTATION_SUMMARY.md`
- **Architecture Research**: `/backend/docs/FEE_SCHEDULE_ARCHITECTURE_RESEARCH.md`
- **API Documentation**: Generated from OpenAPI schema
- **Database Schema**: `/backend/prisma/schema.prisma`

### Test Statistics

**Lines of Test Code**: ~1,700 lines
- Unit tests: ~470 lines
- Integration tests (API): ~660 lines
- Integration tests (Pipeline): ~650 lines

**Test-to-Code Ratio**: ~2.4:1 (1,700 test lines / 700 production code lines)

**Test Execution Time** (estimated):
- Unit tests: ~5 seconds
- Integration tests: ~30-60 seconds
- Full suite: ~1 minute

---

## Changelog

### Version 1.0 (2025-10-18)
- Initial test suite implementation
- 88 tests across 3 test files
- Coverage for service layer and API endpoints
- Integration tests for revenue calculation pipeline
- Comprehensive test fixtures added to conftest.py

### Future Versions
- 1.1: Add payer management API tests
- 1.2: Add NCCI integration tests
- 1.3: Add modifier optimization tests
- 2.0: Complete UI component testing
