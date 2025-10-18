"""
Pytest Configuration and Shared Fixtures

This file contains pytest fixtures and configuration shared across all tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.core.database import prisma
from app.core.security import jwt_manager


# ============================================================================
# Session-scoped fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database fixtures
# ============================================================================

@pytest.fixture(scope="function")
async def db() -> AsyncGenerator:
    """
    Database fixture that connects and disconnects for each test.
    Rolls back transactions to keep tests isolated.
    """
    await prisma.connect()
    yield prisma

    # Clean up test data (order matters for foreign key constraints)
    await prisma.auditlog.delete_many()
    await prisma.report.delete_many()
    await prisma.phimapping.delete_many()
    await prisma.uploadedfile.delete_many()
    await prisma.feeschedulerate.delete_many()
    await prisma.feeschedule.delete_many()
    await prisma.encounter.delete_many()
    await prisma.payer.delete_many()
    await prisma.subscription.delete_many()
    await prisma.token.delete_many()
    await prisma.user.delete_many()

    await prisma.disconnect()


# ============================================================================
# Client fixtures
# ============================================================================

@pytest.fixture
def client() -> TestClient:
    """Synchronous test client for FastAPI"""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async test client for FastAPI"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# ============================================================================
# User fixtures
# ============================================================================

@pytest.fixture
async def test_user(db) -> dict:
    """Create a test user"""
    from app.core.security import hash_password

    user = await prisma.user.create(
        data={
            "email": "test@example.com",
            "passwordHash": hash_password("TestPassword123!"),
            "role": "MEMBER",
            "emailVerified": True,
            "subscriptionStatus": "ACTIVE",
        }
    )

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "user": user,
    }


@pytest.fixture
async def test_admin(db) -> dict:
    """Create a test admin user"""
    from app.core.security import hash_password

    admin = await prisma.user.create(
        data={
            "email": "admin@example.com",
            "passwordHash": hash_password("AdminPassword123!"),
            "role": "ADMIN",
            "emailVerified": True,
            "subscriptionStatus": "ACTIVE",
        }
    )

    return {
        "id": admin.id,
        "email": admin.email,
        "role": admin.role,
        "user": admin,
    }


@pytest.fixture
async def unverified_user(db) -> dict:
    """Create a user with unverified email"""
    from app.core.security import hash_password

    user = await prisma.user.create(
        data={
            "email": "unverified@example.com",
            "passwordHash": hash_password("TestPassword123!"),
            "role": "MEMBER",
            "emailVerified": False,
            "subscriptionStatus": "TRIAL",
        }
    )

    return {
        "id": user.id,
        "email": user.email,
        "user": user,
    }


# ============================================================================
# Authentication fixtures
# ============================================================================

@pytest.fixture
def user_token(test_user) -> str:
    """Generate JWT access token for test user"""
    return jwt_manager.create_access_token(
        data={"sub": test_user["id"], "email": test_user["email"]}
    )


@pytest.fixture
def admin_token(test_admin) -> str:
    """Generate JWT access token for test admin"""
    return jwt_manager.create_access_token(
        data={"sub": test_admin["id"], "email": test_admin["email"]}
    )


@pytest.fixture
def auth_headers(user_token) -> dict:
    """Headers with user authentication"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token) -> dict:
    """Headers with admin authentication"""
    return {"Authorization": f"Bearer {admin_token}"}


# ============================================================================
# Encounter fixtures
# ============================================================================

@pytest.fixture
async def test_encounter(db, test_user) -> dict:
    """Create a test encounter"""
    encounter = await prisma.encounter.create(
        data={
            "userId": test_user["id"],
            "status": "PENDING",
            "patientAge": 45,
            "patientSex": "M",
        }
    )

    return {
        "id": encounter.id,
        "userId": encounter.userId,
        "status": encounter.status,
        "encounter": encounter,
    }


@pytest.fixture
async def completed_encounter(db, test_user) -> dict:
    """Create a completed encounter with report"""
    from datetime import datetime

    encounter = await prisma.encounter.create(
        data={
            "userId": test_user["id"],
            "status": "COMPLETED",
            "processingStartedAt": datetime.utcnow(),
            "processingCompletedAt": datetime.utcnow(),
            "processingTime": 15000,  # 15 seconds
            "patientAge": 45,
            "patientSex": "M",
        }
    )

    report = await prisma.report.create(
        data={
            "encounterId": encounter.id,
            "billedCodes": [
                {"code": "99214", "type": "CPT", "description": "Office visit"}
            ],
            "suggestedCodes": [
                {
                    "code": {"code": "99215", "type": "CPT", "description": "Complex visit"},
                    "justification": "Documentation supports high complexity",
                    "confidence": 0.92,
                    "estimatedRevenue": 75.0,
                }
            ],
            "incrementalRevenue": 75.0,
            "aiModel": "gpt-4",
            "confidenceScore": 0.92,
        }
    )

    return {
        "id": encounter.id,
        "userId": encounter.userId,
        "encounter": encounter,
        "report": report,
    }


# ============================================================================
# File fixtures
# ============================================================================

@pytest.fixture
def sample_clinical_note() -> str:
    """Sample clinical note text"""
    return """
    PATIENT: John Smith
    DOB: 01/15/1975
    MRN: 123456
    DATE OF SERVICE: 09/30/2025

    CHIEF COMPLAINT: Chest pain

    HISTORY OF PRESENT ILLNESS:
    Patient is a 50-year-old male presenting with intermittent chest pain
    for the past 2 days. Pain is substernal, non-radiating, 6/10 intensity.

    PAST MEDICAL HISTORY: Hypertension, hyperlipidemia

    MEDICATIONS: Lisinopril 10mg daily, Atorvastatin 20mg daily

    PHYSICAL EXAMINATION:
    Vital Signs: BP 145/90, HR 82, RR 16, T 98.6F
    Cardiovascular: Regular rate and rhythm, no murmurs
    Respiratory: Clear to auscultation bilaterally

    ASSESSMENT AND PLAN:
    1. Chest pain - likely musculoskeletal, will obtain EKG and troponin
    2. Hypertension - continue current medications
    3. Follow up in 1 week or sooner if symptoms worsen
    """


@pytest.fixture
def sample_phi_text() -> str:
    """Sample text with PHI for testing de-identification"""
    return """
    Patient John Smith was admitted on 04/15/2024 with chest pain.
    Phone: (555) 123-4567. Lives at 123 Main St, Anytown, CA 12345.
    MRN: 98765. SSN: 123-45-6789.
    """


@pytest.fixture
def sample_billing_codes() -> list:
    """Sample billing codes"""
    return [
        {"code": "99214", "type": "CPT", "description": "Office visit - established patient"},
        {"code": "I10", "type": "ICD10", "description": "Essential hypertension"},
        {"code": "E78.5", "type": "ICD10", "description": "Hyperlipidemia"},
    ]


# ============================================================================
# Payment fixtures
# ============================================================================

@pytest.fixture
def stripe_checkout_session_completed() -> dict:
    """Mock Stripe checkout.session.completed event"""
    return {
        "id": "evt_test_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "customer": "cus_test_123",
                "subscription": "sub_test_123",
                "amount_total": 10000,  # $100.00
                "currency": "usd",
                "metadata": {
                    "user_id": "test-user-id",
                },
            }
        },
    }


@pytest.fixture
def stripe_subscription_created() -> dict:
    """Mock Stripe subscription.created event"""
    return {
        "id": "evt_test_456",
        "type": "subscription.created",
        "data": {
            "object": {
                "id": "sub_test_123",
                "customer": "cus_test_123",
                "status": "active",
                "current_period_start": 1696089600,
                "current_period_end": 1698681600,
                "items": {
                    "data": [
                        {
                            "price": {
                                "id": "price_test_123",
                                "unit_amount": 10000,
                                "currency": "usd",
                            }
                        }
                    ]
                },
            }
        },
    }


@pytest.fixture
def stripe_payment_failed() -> dict:
    """Mock Stripe payment_intent.payment_failed event"""
    return {
        "id": "evt_test_789",
        "type": "payment_intent.payment_failed",
        "data": {
            "object": {
                "id": "pi_test_123",
                "customer": "cus_test_123",
                "amount": 10000,
                "currency": "usd",
                "last_payment_error": {
                    "message": "Your card was declined.",
                },
            }
        },
    }


# ============================================================================
# Mock fixtures
# ============================================================================

@pytest.fixture
def mock_comprehend_response() -> dict:
    """Mock Amazon Comprehend Medical DetectPHI response"""
    return {
        "Entities": [
            {
                "Type": "NAME",
                "Text": "John Smith",
                "BeginOffset": 8,
                "EndOffset": 18,
                "Score": 0.99,
            },
            {
                "Type": "DATE",
                "Text": "04/15/2024",
                "BeginOffset": 35,
                "EndOffset": 45,
                "Score": 0.98,
            },
            {
                "Type": "PHONE_OR_FAX",
                "Text": "(555) 123-4567",
                "BeginOffset": 70,
                "EndOffset": 84,
                "Score": 0.97,
            },
            {
                "Type": "ADDRESS",
                "Text": "123 Main St, Anytown, CA 12345",
                "BeginOffset": 95,
                "EndOffset": 125,
                "Score": 0.96,
            },
        ]
    }


@pytest.fixture
def mock_gpt4_response() -> dict:
    """Mock OpenAI GPT-4 response for code suggestions"""
    return {
        "choices": [
            {
                "message": {
                    "content": """
                    {
                        "suggested_codes": [
                            {
                                "code": "99215",
                                "type": "CPT",
                                "description": "Office visit - high complexity",
                                "justification": "Documentation supports comprehensive history, detailed examination, and high complexity medical decision making",
                                "confidence": 0.92,
                                "supporting_text": [
                                    "Comprehensive history taken",
                                    "Detailed examination performed"
                                ]
                            },
                            {
                                "code": "93000",
                                "type": "CPT",
                                "description": "Electrocardiogram",
                                "justification": "EKG mentioned in assessment and plan",
                                "confidence": 0.95,
                                "supporting_text": [
                                    "will obtain EKG"
                                ]
                            }
                        ]
                    }
                    """
                }
            }
        ]
    }


# ============================================================================
# Utility functions
# ============================================================================

@pytest.fixture
def assert_audit_log():
    """Helper to assert audit log was created"""
    async def _assert(action: str, user_id: str = None):
        log = await prisma.auditlog.find_first(
            where={"action": action, "userId": user_id} if user_id else {"action": action}
        )
        assert log is not None, f"Audit log for action '{action}' not found"
        return log

    return _assert


# ============================================================================
# Payer and Fee Schedule fixtures
# ============================================================================

@pytest.fixture
async def test_payer(db) -> dict:
    """Create a test payer"""
    from prisma.enums import PayerType

    payer = await prisma.payer.create(
        data={
            "name": "Blue Cross Blue Shield",
            "payerCode": "BCBS",
            "payerType": PayerType.COMMERCIAL,
            "website": "https://www.bcbs.com",
            "phone": "(800) 123-4567",
            "isActive": True,
        }
    )

    return {
        "payer_id": payer.id,
        "payer_name": payer.name,
        "payer_code": payer.payerCode,
        "payer": payer,
    }


@pytest.fixture
async def test_payer_with_schedule(db, test_user) -> dict:
    """Create a test payer with active fee schedule"""
    from prisma.enums import PayerType
    from datetime import datetime, timedelta

    payer = await prisma.payer.create(
        data={
            "name": "Blue Cross Blue Shield",
            "payerCode": "BCBS",
            "payerType": PayerType.COMMERCIAL,
            "isActive": True,
        }
    )

    fee_schedule = await prisma.feeschedule.create(
        data={
            "payerId": payer.id,
            "name": "2025 Q1 Fee Schedule",
            "description": "Test fee schedule for Q1 2025",
            "effectiveDate": datetime.now() - timedelta(days=30),
            "expirationDate": datetime.now() + timedelta(days=60),
            "isActive": True,
            "uploadedByUserId": test_user["id"],
            "uploadedFileName": "test_schedule.csv",
        }
    )

    # Create some sample rates
    rates_data = [
        {
            "feeScheduleId": fee_schedule.id,
            "cptCode": "99213",
            "cptDescription": "Office visit - established patient, low complexity",
            "allowedAmount": 75.50,
            "facilityRate": 70.00,
            "nonFacilityRate": 75.50,
            "requiresAuth": False,
            "workRVU": 1.3,
            "totalRVU": 2.1,
        },
        {
            "feeScheduleId": fee_schedule.id,
            "cptCode": "99214",
            "cptDescription": "Office visit - established patient, moderate complexity",
            "allowedAmount": 110.25,
            "facilityRate": 105.00,
            "nonFacilityRate": 110.25,
            "requiresAuth": False,
            "workRVU": 1.92,
            "totalRVU": 3.2,
        },
        {
            "feeScheduleId": fee_schedule.id,
            "cptCode": "99215",
            "cptDescription": "Office visit - established patient, high complexity",
            "allowedAmount": 148.33,
            "facilityRate": 140.00,
            "nonFacilityRate": 148.33,
            "requiresAuth": False,
            "workRVU": 2.8,
            "totalRVU": 4.5,
        },
        {
            "feeScheduleId": fee_schedule.id,
            "cptCode": "45378",
            "cptDescription": "Colonoscopy - diagnostic",
            "allowedAmount": 550.00,
            "facilityRate": 550.00,
            "nonFacilityRate": 550.00,
            "requiresAuth": True,
            "authCriteria": "Prior authorization required for all non-emergent procedures",
            "workRVU": 4.5,
            "totalRVU": 7.2,
        },
    ]

    await prisma.feeschedulerate.create_many(data=rates_data)

    return {
        "payer_id": payer.id,
        "payer_name": payer.name,
        "fee_schedule_id": fee_schedule.id,
        "payer": payer,
        "fee_schedule": fee_schedule,
    }


@pytest.fixture
async def test_payer_no_schedule(db) -> dict:
    """Create a test payer without fee schedule"""
    from prisma.enums import PayerType

    payer = await prisma.payer.create(
        data={
            "name": "Aetna",
            "payerCode": "AETNA",
            "payerType": PayerType.COMMERCIAL,
            "isActive": True,
        }
    )

    return {
        "payer_id": payer.id,
        "payer_name": payer.name,
        "payer": payer,
    }


@pytest.fixture
async def test_payer_expired_schedule(db, test_user) -> dict:
    """Create a test payer with expired fee schedule"""
    from prisma.enums import PayerType
    from datetime import datetime, timedelta

    payer = await prisma.payer.create(
        data={
            "name": "UnitedHealthcare",
            "payerCode": "UHC",
            "payerType": PayerType.COMMERCIAL,
            "isActive": True,
        }
    )

    # Create expired schedule
    fee_schedule = await prisma.feeschedule.create(
        data={
            "payerId": payer.id,
            "name": "2024 Expired Schedule",
            "effectiveDate": datetime.now() - timedelta(days=180),
            "expirationDate": datetime.now() - timedelta(days=30),
            "isActive": False,
            "uploadedByUserId": test_user["id"],
            "uploadedFileName": "expired_schedule.csv",
        }
    )

    return {
        "payer_id": payer.id,
        "payer_name": payer.name,
        "fee_schedule_id": fee_schedule.id,
        "payer": payer,
        "fee_schedule": fee_schedule,
    }


@pytest.fixture
def sample_fee_schedule_csv() -> str:
    """Sample fee schedule CSV content"""
    return """cpt_code,description,allowed_amount,facility_rate,non_facility_rate,requires_auth,auth_criteria,work_rvu,total_rvu
99213,Office visit - established patient low complexity,75.50,70.00,75.50,false,,1.3,2.1
99214,Office visit - established patient moderate complexity,110.25,105.00,110.25,false,,1.92,3.2
99215,Office visit - established patient high complexity,148.33,140.00,148.33,false,,2.8,4.5
45378,Colonoscopy diagnostic,550.00,550.00,550.00,true,Prior authorization required for all non-emergent procedures,4.5,7.2
93000,Electrocardiogram routine ECG with interpretation,12.50,12.50,12.50,false,,0.18,0.45
"""
