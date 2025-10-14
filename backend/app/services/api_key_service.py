"""
API Key Service
Handles API key generation, validation, and management
"""

import secrets
import hashlib
from datetime import datetime
from typing import Optional, Tuple
from prisma import models

from app.core.logging import get_logger

logger = get_logger(__name__)


class ApiKeyService:
    """Service for managing API keys"""

    # API key format: revx_<32 random hex chars>
    KEY_PREFIX = "revx_"
    KEY_LENGTH = 32

    @classmethod
    def generate_api_key(cls) -> Tuple[str, str, str]:
        """
        Generate a new API key

        Returns:
            Tuple of (full_key, key_hash, key_prefix)
            - full_key: The actual API key to give to user
            - key_hash: Hash to store in database
            - key_prefix: First 8 chars for identification
        """
        # Generate random key
        random_part = secrets.token_hex(cls.KEY_LENGTH)
        full_key = f"{cls.KEY_PREFIX}{random_part}"

        # Create hash for storage
        key_hash = cls._hash_key(full_key)

        # Extract prefix for identification
        key_prefix = full_key[:8]

        return full_key, key_hash, key_prefix

    @classmethod
    def _hash_key(cls, api_key: str) -> str:
        """Hash an API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    @classmethod
    async def validate_api_key(cls, api_key: str, db) -> Optional[models.ApiKey]:
        """
        Validate an API key and return the ApiKey record if valid

        Args:
            api_key: The API key to validate
            db: Database connection

        Returns:
            ApiKey model if valid, None otherwise
        """
        if not api_key or not api_key.startswith(cls.KEY_PREFIX):
            return None

        # Hash the provided key
        key_hash = cls._hash_key(api_key)

        # Look up in database
        try:
            api_key_record = await db.apikey.find_first(
                where={
                    "keyHash": key_hash,
                    "isActive": True,
                },
                include={"user": True},
            )

            if not api_key_record:
                return None

            # Check expiration
            if api_key_record.expiresAt and api_key_record.expiresAt < datetime.utcnow():
                logger.warning(
                    f"API key expired",
                    key_id=api_key_record.id,
                    expired_at=api_key_record.expiresAt,
                )
                return None

            # Update usage stats
            await db.apikey.update(
                where={"id": api_key_record.id},
                data={
                    "lastUsedAt": datetime.utcnow(),
                    "usageCount": {"increment": 1},
                },
            )

            return api_key_record

        except Exception as e:
            logger.error(f"Error validating API key", error=str(e))
            return None

    @classmethod
    async def create_api_key(
        cls,
        db,
        user_id: str,
        name: str,
        rate_limit: int = 100,
        expires_at: Optional[datetime] = None,
    ) -> Tuple[str, models.ApiKey]:
        """
        Create a new API key

        Args:
            db: Database connection
            user_id: User ID who owns the key
            name: Name for the API key
            rate_limit: Rate limit per minute
            expires_at: Optional expiration date

        Returns:
            Tuple of (api_key, api_key_record)
        """
        # Generate API key
        full_key, key_hash, key_prefix = cls.generate_api_key()

        # Create database record
        api_key_record = await db.apikey.create(
            data={
                "userId": user_id,
                "name": name,
                "keyHash": key_hash,
                "keyPrefix": key_prefix,
                "rateLimit": rate_limit,
                "expiresAt": expires_at,
            }
        )

        logger.info(
            f"API key created",
            key_id=api_key_record.id,
            user_id=user_id,
            name=name,
        )

        return full_key, api_key_record

    @classmethod
    async def revoke_api_key(cls, db, key_id: str, user_id: str) -> bool:
        """
        Revoke (deactivate) an API key

        Args:
            db: Database connection
            key_id: API key ID
            user_id: User ID (for authorization)

        Returns:
            True if revoked, False if not found or unauthorized
        """
        try:
            # Verify ownership
            api_key = await db.apikey.find_first(
                where={"id": key_id, "userId": user_id}
            )

            if not api_key:
                return False

            # Deactivate
            await db.apikey.update(
                where={"id": key_id},
                data={"isActive": False},
            )

            logger.info(f"API key revoked", key_id=key_id, user_id=user_id)
            return True

        except Exception as e:
            logger.error(f"Error revoking API key", error=str(e), key_id=key_id)
            return False
