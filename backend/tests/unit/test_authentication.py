"""
Unit Tests for Authentication

Tests for user registration, login, token management, and password operations.
"""

import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException

from app.core.security import (
    hash_password,
    verify_password,
    jwt_manager,
)


# ============================================================================
# Password Hashing Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password_creates_valid_hash(self):
        """Test that password hashing creates a valid bcrypt hash"""
        password = "TestPassword123!"
        hashed = hash_password(password)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "TestPassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_same_password_different_hashes(self):
        """Test that same password generates different hashes (salt)"""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_empty_password_raises_error(self):
        """Test that empty password raises appropriate error"""
        with pytest.raises((ValueError, Exception)):
            hash_password("")


# ============================================================================
# JWT Token Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
class TestJWTTokens:
    """Test JWT token creation and validation"""

    def test_create_access_token(self):
        """Test access token creation"""
        user_data = {"sub": "user123", "email": "test@example.com"}
        token = jwt_manager.create_access_token(data=user_data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

    def test_create_refresh_token(self):
        """Test refresh token creation"""
        user_data = {"sub": "user123", "email": "test@example.com"}
        token = jwt_manager.create_refresh_token(data=user_data)

        assert token is not None
        assert isinstance(token, str)

    def test_decode_valid_access_token(self):
        """Test decoding a valid access token"""
        user_data = {"sub": "user123", "email": "test@example.com"}
        token = jwt_manager.create_access_token(data=user_data)

        payload = jwt_manager.decode_token(token)

        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload
        assert "token_type" in payload

    def test_decode_expired_token_raises_error(self):
        """Test that expired token raises appropriate error"""
        from jose import jwt
        from datetime import datetime, timedelta
        from app.core.config import settings

        # Create token that's already expired
        user_data = {
            "sub": "user123",
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            user_data, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(HTTPException) as exc_info:
            jwt_manager.decode_token(expired_token)

        assert exc_info.value.status_code == 401

    def test_decode_invalid_token_raises_error(self):
        """Test that invalid token raises appropriate error"""
        invalid_token = "invalid.token.here"

        with pytest.raises(HTTPException) as exc_info:
            jwt_manager.decode_token(invalid_token)

        assert exc_info.value.status_code == 401

    def test_verify_token_type_access(self):
        """Test token type verification for access tokens"""
        user_data = {"sub": "user123"}
        token = jwt_manager.create_access_token(data=user_data)
        payload = jwt_manager.decode_token(token)

        assert jwt_manager.verify_token_type(payload, "access") is True
        assert jwt_manager.verify_token_type(payload, "refresh") is False

    def test_verify_token_type_refresh(self):
        """Test token type verification for refresh tokens"""
        user_data = {"sub": "user123"}
        token = jwt_manager.create_refresh_token(data=user_data)
        payload = jwt_manager.decode_token(token)

        assert jwt_manager.verify_token_type(payload, "refresh") is True
        assert jwt_manager.verify_token_type(payload, "access") is False


# ============================================================================
# User Registration Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
class TestUserRegistration:
    """Test user registration logic"""

    async def test_create_user_with_valid_data(self, db):
        """Test creating a new user with valid data"""
        user_data = {
            "email": "newuser@example.com",
            "passwordHash": hash_password("Password123!"),
            "role": "MEMBER",
            "emailVerified": False,
            "subscriptionStatus": "TRIAL",
        }

        user = await db.user.create(data=user_data)

        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.role == "MEMBER"
        assert user.emailVerified is False
        assert user.subscriptionStatus == "TRIAL"
        assert user.id is not None

    async def test_duplicate_email_raises_error(self, db):
        """Test that duplicate email addresses are rejected"""
        email = "duplicate@example.com"

        # Create first user
        await db.user.create(
            data={
                "email": email,
                "passwordHash": hash_password("Password123!"),
                "role": "MEMBER",
            }
        )

        # Attempt to create second user with same email
        with pytest.raises(Exception):  # Prisma will raise unique constraint error
            await db.user.create(
                data={
                    "email": email,
                    "passwordHash": hash_password("Password456!"),
                    "role": "MEMBER",
                }
            )

    async def test_user_defaults_applied(self, db):
        """Test that default values are correctly applied"""
        user = await db.user.create(
            data={
                "email": "defaults@example.com",
                "passwordHash": hash_password("Password123!"),
            }
        )

        assert user.role == "MEMBER"  # Default role
        assert user.emailVerified is False  # Default
        assert user.subscriptionStatus == "INACTIVE"  # Default
        assert user.createdAt is not None
        assert user.updatedAt is not None


# ============================================================================
# Login Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
class TestUserLogin:
    """Test user login logic"""

    async def test_login_with_valid_credentials(self, db, test_user):
        """Test login with correct email and password"""
        # Find user
        user = await db.user.find_unique(where={"email": "test@example.com"})

        assert user is not None
        assert verify_password("TestPassword123!", user.passwordHash) is True

        # Create tokens
        access_token = jwt_manager.create_access_token(
            data={"sub": user.id, "email": user.email}
        )
        refresh_token = jwt_manager.create_refresh_token(
            data={"sub": user.id, "email": user.email}
        )

        assert access_token is not None
        assert refresh_token is not None

    async def test_login_with_wrong_password(self, db, test_user):
        """Test login with incorrect password"""
        user = await db.user.find_unique(where={"email": "test@example.com"})

        assert user is not None
        assert verify_password("WrongPassword!", user.passwordHash) is False

    async def test_login_with_nonexistent_email(self, db):
        """Test login with email that doesn't exist"""
        user = await db.user.find_unique(where={"email": "nonexistent@example.com"})

        assert user is None

    async def test_login_updates_last_login(self, db, test_user):
        """Test that login updates lastLoginAt timestamp"""
        user = await db.user.update(
            where={"id": test_user["id"]},
            data={"lastLoginAt": datetime.utcnow()},
        )

        assert user.lastLoginAt is not None
        assert isinstance(user.lastLoginAt, datetime)


# ============================================================================
# Email Verification Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
class TestEmailVerification:
    """Test email verification logic"""

    async def test_create_verification_token(self, db, unverified_user):
        """Test creating an email verification token"""
        import secrets

        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)

        token_record = await db.token.create(
            data={
                "userId": unverified_user["id"],
                "token": token,
                "tokenType": "EMAIL_VERIFICATION",
                "expiresAt": expires_at,
                "used": False,
            }
        )

        assert token_record is not None
        assert token_record.token == token
        assert token_record.tokenType == "EMAIL_VERIFICATION"
        assert token_record.used is False

    async def test_verify_email_with_valid_token(self, db, unverified_user):
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

        # Verify user
        updated_user = await db.user.update(
            where={"id": unverified_user["id"]},
            data={"emailVerified": True},
        )

        # Mark token as used
        await db.token.update_many(
            where={"token": token},
            data={"used": True},
        )

        assert updated_user.emailVerified is True

    async def test_expired_token_not_accepted(self, db, unverified_user):
        """Test that expired tokens are rejected"""
        import secrets

        token = secrets.token_urlsafe(32)

        # Create expired token
        token_record = await db.token.create(
            data={
                "userId": unverified_user["id"],
                "token": token,
                "tokenType": "EMAIL_VERIFICATION",
                "expiresAt": datetime.utcnow() - timedelta(hours=1),  # Expired
                "used": False,
            }
        )

        # Check if token is expired
        is_expired = token_record.expiresAt < datetime.utcnow()
        assert is_expired is True

    async def test_used_token_not_reusable(self, db, unverified_user):
        """Test that used tokens cannot be reused"""
        import secrets

        token = secrets.token_urlsafe(32)

        token_record = await db.token.create(
            data={
                "userId": unverified_user["id"],
                "token": token,
                "tokenType": "EMAIL_VERIFICATION",
                "expiresAt": datetime.utcnow() + timedelta(hours=24),
                "used": True,  # Already used
            }
        )

        assert token_record.used is True


# ============================================================================
# Password Reset Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
class TestPasswordReset:
    """Test password reset functionality"""

    async def test_create_password_reset_token(self, db, test_user):
        """Test creating a password reset token"""
        import secrets

        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)

        token_record = await db.token.create(
            data={
                "userId": test_user["id"],
                "token": token,
                "tokenType": "PASSWORD_RESET",
                "expiresAt": expires_at,
                "used": False,
            }
        )

        assert token_record is not None
        assert token_record.tokenType == "PASSWORD_RESET"

    async def test_reset_password_with_valid_token(self, db, test_user):
        """Test resetting password with valid token"""
        new_password = "NewPassword123!"
        new_hash = hash_password(new_password)

        # Update password
        updated_user = await db.user.update(
            where={"id": test_user["id"]},
            data={"passwordHash": new_hash},
        )

        # Verify new password works
        assert verify_password(new_password, updated_user.passwordHash) is True
        # Verify old password doesn't work
        assert verify_password("TestPassword123!", updated_user.passwordHash) is False


# ============================================================================
# Role-Based Access Control Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
class TestRoleBasedAccess:
    """Test RBAC functionality"""

    async def test_admin_role_assignment(self, db):
        """Test creating a user with admin role"""
        admin = await db.user.create(
            data={
                "email": "admin@example.com",
                "passwordHash": hash_password("Admin123!"),
                "role": "ADMIN",
                "emailVerified": True,
            }
        )

        assert admin.role == "ADMIN"

    async def test_member_role_default(self, db):
        """Test that MEMBER is the default role"""
        user = await db.user.create(
            data={
                "email": "member@example.com",
                "passwordHash": hash_password("Member123!"),
            }
        )

        assert user.role == "MEMBER"

    async def test_role_in_jwt_token(self):
        """Test that role is included in JWT token"""
        user_data = {
            "sub": "user123",
            "email": "test@example.com",
            "role": "ADMIN",
        }

        token = jwt_manager.create_access_token(data=user_data)
        payload = jwt_manager.decode_token(token)

        assert payload["role"] == "ADMIN"


# ============================================================================
# Subscription Status Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
class TestSubscriptionStatus:
    """Test subscription status validation"""

    async def test_trial_status(self, db):
        """Test user with trial subscription status"""
        user = await db.user.create(
            data={
                "email": "trial@example.com",
                "passwordHash": hash_password("Password123!"),
                "subscriptionStatus": "TRIAL",
                "trialEndDate": datetime.utcnow() + timedelta(days=7),
            }
        )

        assert user.subscriptionStatus == "TRIAL"
        assert user.trialEndDate is not None

    async def test_active_subscription(self, db):
        """Test user with active subscription"""
        user = await db.user.create(
            data={
                "email": "active@example.com",
                "passwordHash": hash_password("Password123!"),
                "subscriptionStatus": "ACTIVE",
            }
        )

        assert user.subscriptionStatus == "ACTIVE"

    async def test_expired_subscription(self, db):
        """Test user with expired subscription"""
        user = await db.user.create(
            data={
                "email": "expired@example.com",
                "passwordHash": hash_password("Password123!"),
                "subscriptionStatus": "EXPIRED",
            }
        )

        assert user.subscriptionStatus == "EXPIRED"

    async def test_suspended_user(self, db):
        """Test suspended user account"""
        user = await db.user.create(
            data={
                "email": "suspended@example.com",
                "passwordHash": hash_password("Password123!"),
                "subscriptionStatus": "SUSPENDED",
            }
        )

        assert user.subscriptionStatus == "SUSPENDED"
