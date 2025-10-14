# Backend Testing Guide

## Overview

This directory contains comprehensive test suites for the RevRX backend application, achieving ≥80% code coverage as required for HIPAA compliance and production readiness.

## Test Structure

```
tests/
├── conftest.py                          # Shared fixtures and test utilities
├── unit/                                # Unit tests (fast, isolated)
│   ├── test_authentication.py          # Auth, JWT, password hashing tests
│   ├── test_file_validation.py         # File upload validation tests
│   ├── test_phi_deidentification.py    # PHI detection and de-id tests
│   └── test_code_comparison.py         # Billing code comparison tests
└── integration/                         # Integration tests (API endpoints)
    ├── test_api_endpoints.py           # Full API endpoint tests
    └── test_payment_webhooks.py        # Stripe webhook integration tests
```

## Running Tests

### Prerequisites

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Set up test database (if needed)
export DATABASE_URL="postgresql://user:pass@localhost:5432/revrx_test"

# Generate Prisma client
npx prisma generate
```

### Run All Tests

```bash
# Run all tests with coverage report
pytest

# Run with verbose output
pytest -v

# Run with coverage HTML report
pytest --cov-report=html
```

### Run Specific Test Suites

```bash
# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/unit/test_authentication.py -v

# Run specific test class
pytest tests/unit/test_authentication.py::TestPasswordHashing -v

# Run specific test function
pytest tests/unit/test_authentication.py::TestPasswordHashing::test_hash_password_creates_valid_hash -v
```

### Run Tests by Marker

```bash
# Run only authentication tests
pytest -m auth

# Run only PHI tests
pytest -m phi

# Run only payment tests
pytest -m payment

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run slow tests only
pytest -m slow

# Exclude slow tests
pytest -m "not slow"
```

## Test Coverage

### Coverage Requirements

- **Minimum Coverage**: ≥80% (enforced by pytest.ini)
- **Target Coverage**: 85-90%

### Generate Coverage Reports

```bash
# Terminal report with missing lines
pytest --cov=app --cov-report=term-missing

# HTML coverage report (opens in browser)
pytest --cov=app --cov-report=html
open htmlcov/index.html

# XML coverage report (for CI/CD)
pytest --cov=app --cov-report=xml

# Combined reports
pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml
```

## Test Categories

### Unit Tests (Fast, Isolated)

**Authentication Tests** (`test_authentication.py`)
- Password hashing and verification (bcrypt)
- JWT token creation and validation
- Token expiration handling
- User registration validation
- Login flow testing
- Email verification tokens
- Password reset tokens
- Role-based access control (RBAC)
- Subscription status validation

**File Validation Tests** (`test_file_validation.py`)
- File type validation (TXT, PDF, DOCX, CSV, JSON)
- File size limits (5MB for clinical notes, 1MB for billing codes)
- MIME type validation
- File content structure validation
- Virus scanning workflow
- Multiple file uploads
- File metadata tracking

**PHI De-identification Tests** (`test_phi_deidentification.py`)
- PHI entity detection (names, dates, MRN, SSN, phone, email, address)
- Token-based de-identification
- PHI mapping storage and encryption
- Re-identification workflow
- AWS Comprehend Medical integration
- Edge cases (overlapping entities, Unicode, empty text)
- HIPAA compliance validation

**Code Comparison Tests** (`test_code_comparison.py`)
- Billing code parsing (CPT, ICD-10, modifiers)
- Code comparison logic
- Missing code detection
- Revenue calculation
- Code suggestions and justifications
- AI confidence scoring
- Report generation
- Edge cases (empty lists, duplicates, malformed data)

### Integration Tests (API Endpoints)

**API Endpoint Tests** (`test_api_endpoints.py`)
- Authentication endpoints (register, login, logout, refresh)
- User profile management
- Encounter CRUD operations
- File upload endpoints
- Report retrieval
- Admin endpoints (user management, audit logs, metrics)
- Email verification flow
- Password reset flow
- Pagination
- Authorization and access control

**Payment Webhook Tests** (`test_payment_webhooks.py`)
- Stripe webhook signature validation
- Subscription lifecycle events:
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
- Payment events:
  - `invoice.payment_succeeded`
  - `invoice.payment_failed`
- Trial period management
- Billing cycle handling (monthly/annual)
- Webhook idempotency
- Error handling
- Audit logging

## Test Fixtures

### Available Fixtures (from `conftest.py`)

**Database Fixtures**
- `db` - Prisma database connection with automatic cleanup

**Client Fixtures**
- `client` - Synchronous test client
- `async_client` - Asynchronous test client

**User Fixtures**
- `test_user` - Regular verified user
- `test_admin` - Admin user
- `unverified_user` - User with unverified email

**Authentication Fixtures**
- `user_token` - JWT access token for regular user
- `admin_token` - JWT access token for admin
- `auth_headers` - HTTP headers with user token
- `admin_headers` - HTTP headers with admin token

**Encounter Fixtures**
- `test_encounter` - Pending encounter
- `completed_encounter` - Completed encounter with report

**Data Fixtures**
- `sample_clinical_note` - Example clinical note text
- `sample_phi_text` - Text containing PHI entities
- `sample_billing_codes` - Example billing codes list

**Mock Service Fixtures**
- `mock_comprehend_response` - Mock AWS Comprehend Medical response
- `mock_gpt4_response` - Mock GPT-4 API response
- `mock_stripe_webhook_event` - Generic Stripe webhook event
- `mock_stripe_subscription_created` - Subscription created event
- `mock_stripe_payment_succeeded` - Payment succeeded event
- `mock_stripe_payment_failed` - Payment failed event

## Continuous Integration

### GitHub Actions Example

```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt

      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
        run: |
          cd backend
          pytest --cov=app --cov-report=xml --cov-report=term

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
```

## Best Practices

### Writing Tests

1. **Use descriptive test names**: Test names should clearly describe what is being tested
2. **One assertion focus**: Each test should focus on one behavior
3. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification
4. **Use fixtures**: Leverage fixtures for common setup and teardown
5. **Clean up**: Always clean up test data after tests complete
6. **Mock external services**: Mock AWS, OpenAI, Stripe, etc. to avoid API costs
7. **Test edge cases**: Include tests for error conditions, edge cases, and invalid inputs

### Test Isolation

- Tests should be independent and runnable in any order
- Use database transactions or cleanup fixtures
- Don't rely on test execution order
- Mock external dependencies

### Performance

- Keep unit tests fast (< 1 second each)
- Use `@pytest.mark.slow` for tests that take longer
- Run slow tests separately in CI/CD

## Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Check DATABASE_URL is set correctly
echo $DATABASE_URL

# Run Prisma migrations
npx prisma migrate dev
```

**Import Errors**
```bash
# Regenerate Prisma client
npx prisma generate

# Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Fixture Not Found**
- Ensure `conftest.py` is in the correct location
- Check fixture name spelling
- Verify fixture scope (function, class, module, session)

**Async Tests Failing**
- Use `@pytest.mark.asyncio` decorator
- Ensure `asyncio_mode = auto` in pytest.ini
- Check that pytest-asyncio is installed

## Coverage Goals by Module

- **Authentication**: 90%+ (critical security component)
- **PHI De-identification**: 85%+ (HIPAA compliance requirement)
- **File Validation**: 80%+
- **Code Comparison**: 80%+
- **API Endpoints**: 80%+
- **Payment Webhooks**: 75%+

## Reporting Issues

If tests are failing or coverage is below 80%:

1. Run tests with verbose output: `pytest -vv`
2. Check coverage report: `pytest --cov-report=html`
3. Review missing lines in `htmlcov/index.html`
4. Add tests for uncovered code paths
5. Ensure all edge cases are tested

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Prisma Testing Guide](https://www.prisma.io/docs/guides/testing)
