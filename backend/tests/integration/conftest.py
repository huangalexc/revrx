"""
Pytest configuration for integration tests.

Provides fixtures for authentication, test users, and database setup.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Dict
from httpx import AsyncClient
from app.main import app
from app.models.prisma_client import prisma
from app.utils.auth import create_access_token


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_database():
    """Connect to database before tests and disconnect after."""
    await prisma.connect()
    yield
    await prisma.disconnect()


@pytest.fixture
async def test_user() -> Dict[str, str]:
    """
    Create a test user and return authentication details.

    Returns:
        Dict with user_id and access_token
    """
    # Create test user
    user = await prisma.user.create(
        data={
            "email": f"test_{asyncio.current_task().get_name()}@example.com",
            "firstName": "Test",
            "lastName": "User",
            "role": "MEMBER",
            "isVerified": True
        }
    )

    # Generate access token
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email}
    )

    yield {
        "user_id": user.id,
        "access_token": access_token,
        "email": user.email
    }

    # Cleanup: delete test user and related data
    await prisma.encounter.delete_many(where={"userId": user.id})
    await prisma.user.delete(where={"id": user.id})


@pytest.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def auth_headers(test_user: Dict[str, str]) -> Dict[str, str]:
    """Fixture to provide authentication headers."""
    return {"Authorization": f"Bearer {test_user['access_token']}"}


@pytest.fixture
async def second_test_user() -> Dict[str, str]:
    """
    Create a second test user for multi-user testing.

    Returns:
        Dict with user_id and access_token
    """
    # Create second test user
    user = await prisma.user.create(
        data={
            "email": f"test_user_2_{asyncio.current_task().get_name()}@example.com",
            "firstName": "Second",
            "lastName": "User",
            "role": "MEMBER",
            "isVerified": True
        }
    )

    # Generate access token
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email}
    )

    yield {
        "user_id": user.id,
        "access_token": access_token,
        "email": user.email
    }

    # Cleanup
    await prisma.encounter.delete_many(where={"userId": user.id})
    await prisma.user.delete(where={"id": user.id})


@pytest.fixture
def sample_clinical_note_1() -> bytes:
    """First sample clinical note for testing."""
    return b"""
Patient: John Doe
MRN: 12345
Date: 2024-01-15
Chief Complaint: Routine checkup

Assessment:
Patient presents for annual physical examination.
Blood pressure: 120/80 mmHg
Heart rate: 72 bpm
Temperature: 98.6°F
Weight: 180 lbs

Plan:
- Continue current medications
- Follow up in 6 months
- Lab work ordered: CBC, CMP, Lipid panel

Dr. Sarah Smith, MD
License: CA-123456
"""


@pytest.fixture
def sample_clinical_note_2() -> bytes:
    """Second sample clinical note for testing."""
    return b"""
Patient: Jane Smith
MRN: 67890
Date: 2024-01-16
Chief Complaint: Follow-up visit

Assessment:
Patient presents for diabetes follow-up.
Blood glucose: 110 mg/dL
HbA1c: 6.5%
Blood pressure: 128/82 mmHg

Plan:
- Adjust insulin dosage to 20 units QAM
- Dietary counseling scheduled
- Follow up in 3 months
- Diabetic retinopathy screening ordered

Dr. Michael Johnson, MD
License: CA-789012
"""


@pytest.fixture
def sample_clinical_note_3() -> bytes:
    """Third sample clinical note for testing."""
    return b"""
Patient: Robert Williams
MRN: 54321
Date: 2024-01-17
Chief Complaint: Chest pain

Assessment:
Patient presents with intermittent chest pain for 2 days.
Onset: 2 days ago, worse with exertion
Character: Pressure-like, substernal
EKG: Normal sinus rhythm, no ST changes
Troponin: Negative

Plan:
- Rule out cardiac etiology
- Stress test scheduled for tomorrow
- Started on aspirin 81mg daily
- Follow up with cardiology

Dr. Emily Chen, MD
License: CA-456789
"""


# Marker for slow tests
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
