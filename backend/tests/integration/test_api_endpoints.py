"""
Integration Tests for API Endpoints

Tests for authentication, user management, encounters, and file upload endpoints.
"""

import pytest
from fastapi import status
from datetime import datetime, timedelta


# ============================================================================
# Authentication Endpoint Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestAuthenticationEndpoints:
    """Test authentication API endpoints"""

    async def test_register_new_user(self, async_client, db):
        """Test user registration endpoint"""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["email"] == "newuser@example.com"

    async def test_register_duplicate_email(self, async_client, test_user):
        """Test registration with duplicate email fails"""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",  # Already exists
                "password": "SecurePassword123!",
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_register_invalid_email(self, async_client):
        """Test registration with invalid email format"""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "SecurePassword123!",
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_register_weak_password(self, async_client):
        """Test registration with weak password"""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "weak",
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_login_success(self, async_client, test_user):
        """Test successful login"""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, async_client, test_user):
        """Test login with wrong password"""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPassword123!",
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_login_nonexistent_user(self, async_client):
        """Test login with nonexistent email"""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "Password123!",
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_login_unverified_email(self, async_client, unverified_user):
        """Test login with unverified email"""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "unverified@example.com",
                "password": "TestPassword123!",
            }
        )

        # Should either block login or return special flag
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
        ]

    async def test_refresh_token(self, async_client, test_user, user_token):
        """Test token refresh endpoint"""
        # Create refresh token
        from app.core.security import jwt_manager
        refresh_token = jwt_manager.create_refresh_token(
            data={"sub": test_user["id"], "email": test_user["email"]}
        )

        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data

    async def test_logout(self, async_client, auth_headers):
        """Test logout endpoint"""
        response = await async_client.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK


# ============================================================================
# User Profile Endpoint Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestUserProfileEndpoints:
    """Test user profile management endpoints"""

    async def test_get_current_user(self, async_client, auth_headers, test_user):
        """Test getting current user profile"""
        response = await async_client.get(
            "/api/v1/users/me",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_user["id"]
        assert data["email"] == test_user["email"]

    async def test_get_current_user_unauthorized(self, async_client):
        """Test getting profile without auth"""
        response = await async_client.get("/api/v1/users/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_update_user_profile(self, async_client, auth_headers):
        """Test updating user profile"""
        response = await async_client.patch(
            "/api/v1/users/me",
            headers=auth_headers,
            json={
                "profileComplete": True,
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["profileComplete"] is True

    async def test_change_password(self, async_client, auth_headers):
        """Test password change endpoint"""
        response = await async_client.post(
            "/api/v1/users/me/password",
            headers=auth_headers,
            json={
                "current_password": "TestPassword123!",
                "new_password": "NewPassword123!",
            }
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_delete_user_account(self, async_client, auth_headers):
        """Test account deletion"""
        response = await async_client.delete(
            "/api/v1/users/me",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK


# ============================================================================
# Encounter Endpoint Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestEncounterEndpoints:
    """Test encounter management endpoints"""

    async def test_create_encounter(self, async_client, auth_headers, test_user):
        """Test creating new encounter"""
        response = await async_client.post(
            "/api/v1/encounters",
            headers=auth_headers,
            json={
                "patientAge": 45,
                "patientSex": "M",
                "visitDate": datetime.utcnow().isoformat(),
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["userId"] == test_user["id"]
        assert data["status"] == "PENDING"

    async def test_list_encounters(self, async_client, auth_headers, test_encounter):
        """Test listing user encounters"""
        response = await async_client.get(
            "/api/v1/encounters",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0

    async def test_get_encounter_by_id(self, async_client, auth_headers, test_encounter):
        """Test getting specific encounter"""
        response = await async_client.get(
            f"/api/v1/encounters/{test_encounter['id']}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_encounter["id"]

    async def test_get_nonexistent_encounter(self, async_client, auth_headers):
        """Test getting encounter that doesn't exist"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await async_client.get(
            f"/api/v1/encounters/{fake_id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_other_user_encounter(self, async_client, auth_headers, db, test_admin):
        """Test accessing another user's encounter"""
        # Create encounter for admin user
        admin_encounter = await db.encounter.create(
            data={
                "userId": test_admin["id"],
                "status": "PENDING",
            }
        )

        # Try to access with regular user auth
        response = await async_client.get(
            f"/api/v1/encounters/{admin_encounter.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_delete_encounter(self, async_client, auth_headers, test_encounter):
        """Test deleting encounter"""
        response = await async_client.delete(
            f"/api/v1/encounters/{test_encounter['id']}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK


# ============================================================================
# File Upload Endpoint Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestFileUploadEndpoints:
    """Test file upload endpoints"""

    async def test_upload_clinical_note_txt(self, async_client, auth_headers, test_encounter):
        """Test uploading TXT clinical note"""
        from io import BytesIO

        file_content = b"Patient presents with hypertension. BP 140/90."
        files = {
            "file": ("clinical_note.txt", BytesIO(file_content), "text/plain")
        }

        response = await async_client.post(
            f"/api/v1/encounters/{test_encounter['id']}/files",
            headers=auth_headers,
            files=files,
            data={"file_type": "CLINICAL_NOTE_TXT"}
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["fileName"] == "clinical_note.txt"
        assert data["fileType"] == "CLINICAL_NOTE_TXT"

    async def test_upload_billing_codes_csv(self, async_client, auth_headers, test_encounter):
        """Test uploading CSV billing codes"""
        from io import BytesIO

        csv_content = b"code,description\n99213,Office Visit\nZ00.00,General Exam"
        files = {
            "file": ("billing_codes.csv", BytesIO(csv_content), "text/csv")
        }

        response = await async_client.post(
            f"/api/v1/encounters/{test_encounter['id']}/files",
            headers=auth_headers,
            files=files,
            data={"file_type": "BILLING_CODES_CSV"}
        )

        assert response.status_code == status.HTTP_201_CREATED

    async def test_upload_file_too_large(self, async_client, auth_headers, test_encounter):
        """Test uploading file exceeding size limit"""
        from io import BytesIO

        # Create 6MB file (exceeds 5MB limit)
        large_content = b"x" * (6 * 1024 * 1024)
        files = {
            "file": ("large_note.txt", BytesIO(large_content), "text/plain")
        }

        response = await async_client.post(
            f"/api/v1/encounters/{test_encounter['id']}/files",
            headers=auth_headers,
            files=files,
            data={"file_type": "CLINICAL_NOTE_TXT"}
        )

        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

    async def test_upload_invalid_file_type(self, async_client, auth_headers, test_encounter):
        """Test uploading unsupported file type"""
        from io import BytesIO

        files = {
            "file": ("malicious.exe", BytesIO(b"fake exe"), "application/x-msdownload")
        }

        response = await async_client.post(
            f"/api/v1/encounters/{test_encounter['id']}/files",
            headers=auth_headers,
            files=files,
            data={"file_type": "CLINICAL_NOTE_TXT"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_list_encounter_files(self, async_client, auth_headers, test_encounter, db):
        """Test listing files for encounter"""
        # Create a file
        await db.uploadedfile.create(
            data={
                "encounterId": test_encounter["id"],
                "fileType": "CLINICAL_NOTE_TXT",
                "fileName": "note.txt",
                "filePath": "test/note.txt",
                "fileSize": 1024,
                "mimeType": "text/plain",
                "scanStatus": "CLEAN",
            }
        )

        response = await async_client.get(
            f"/api/v1/encounters/{test_encounter['id']}/files",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) > 0


# ============================================================================
# Report Endpoint Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestReportEndpoints:
    """Test report retrieval endpoints"""

    async def test_get_encounter_report(self, async_client, auth_headers, completed_encounter, db):
        """Test getting report for completed encounter"""
        # Create report
        report = await db.report.create(
            data={
                "encounterId": completed_encounter["id"],
                "billedCodes": [{"code": "99213"}],
                "suggestedCodes": [{"code": "99214"}],
                "incrementalRevenue": 42.00,
                "aiModel": "gpt-4",
            }
        )

        response = await async_client.get(
            f"/api/v1/encounters/{completed_encounter['id']}/report",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == report.id
        assert data["incrementalRevenue"] == 42.00

    async def test_get_report_for_pending_encounter(self, async_client, auth_headers, test_encounter):
        """Test getting report for encounter without report"""
        response = await async_client.get(
            f"/api/v1/encounters/{test_encounter['id']}/report",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Admin Endpoint Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.admin
@pytest.mark.asyncio
class TestAdminEndpoints:
    """Test admin-only endpoints"""

    async def test_list_all_users_as_admin(self, async_client, admin_headers):
        """Test admin listing all users"""
        response = await async_client.get(
            "/api/v1/admin/users",
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_list_users_as_regular_user(self, async_client, auth_headers):
        """Test regular user cannot access admin endpoints"""
        response = await async_client.get(
            "/api/v1/admin/users",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_view_audit_logs(self, async_client, admin_headers):
        """Test admin viewing audit logs"""
        response = await async_client.get(
            "/api/v1/admin/audit-logs",
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data

    async def test_get_system_metrics(self, async_client, admin_headers):
        """Test admin getting system metrics"""
        response = await async_client.get(
            "/api/v1/admin/metrics",
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "totalUsers" in data
        assert "totalEncounters" in data

    async def test_suspend_user(self, async_client, admin_headers, test_user):
        """Test admin suspending user"""
        response = await async_client.post(
            f"/api/v1/admin/users/{test_user['id']}/suspend",
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_activate_user(self, async_client, admin_headers, test_user):
        """Test admin activating user"""
        response = await async_client.post(
            f"/api/v1/admin/users/{test_user['id']}/activate",
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_200_OK


# ============================================================================
# Email Verification Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestEmailVerificationEndpoints:
    """Test email verification endpoints"""

    async def test_request_verification_email(self, async_client, unverified_user):
        """Test requesting verification email"""
        response = await async_client.post(
            "/api/v1/auth/request-verification",
            json={"email": "unverified@example.com"}
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_verify_email_with_valid_token(self, async_client, db, unverified_user):
        """Test email verification with valid token"""
        import secrets

        token = secrets.token_urlsafe(32)

        # Create token
        await db.token.create(
            data={
                "userId": unverified_user["id"],
                "token": token,
                "tokenType": "EMAIL_VERIFICATION",
                "expiresAt": datetime.utcnow() + timedelta(hours=24),
                "used": False,
            }
        )

        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": token}
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_verify_email_with_expired_token(self, async_client, db, unverified_user):
        """Test email verification with expired token"""
        import secrets

        token = secrets.token_urlsafe(32)

        # Create expired token
        await db.token.create(
            data={
                "userId": unverified_user["id"],
                "token": token,
                "tokenType": "EMAIL_VERIFICATION",
                "expiresAt": datetime.utcnow() - timedelta(hours=1),
                "used": False,
            }
        )

        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": token}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# Password Reset Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestPasswordResetEndpoints:
    """Test password reset endpoints"""

    async def test_request_password_reset(self, async_client, test_user):
        """Test requesting password reset"""
        response = await async_client.post(
            "/api/v1/auth/request-password-reset",
            json={"email": "test@example.com"}
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_reset_password_with_valid_token(self, async_client, db, test_user):
        """Test resetting password with valid token"""
        import secrets

        token = secrets.token_urlsafe(32)

        # Create reset token
        await db.token.create(
            data={
                "userId": test_user["id"],
                "token": token,
                "tokenType": "PASSWORD_RESET",
                "expiresAt": datetime.utcnow() + timedelta(hours=1),
                "used": False,
            }
        )

        response = await async_client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": token,
                "new_password": "NewSecurePassword123!"
            }
        )

        assert response.status_code == status.HTTP_200_OK


# ============================================================================
# Pagination Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestPaginationEndpoints:
    """Test pagination in list endpoints"""

    async def test_encounters_pagination(self, async_client, auth_headers, db, test_user):
        """Test encounter list pagination"""
        # Create multiple encounters
        for i in range(5):
            await db.encounter.create(
                data={
                    "userId": test_user["id"],
                    "status": "PENDING",
                }
            )

        response = await async_client.get(
            "/api/v1/encounters?page=1&limit=3",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) <= 3
        assert "total" in data
        assert "page" in data

    async def test_pagination_invalid_page(self, async_client, auth_headers):
        """Test pagination with invalid page number"""
        response = await async_client.get(
            "/api/v1/encounters?page=0&limit=10",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
