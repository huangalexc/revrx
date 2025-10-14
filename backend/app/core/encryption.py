"""
Encryption utilities for PHI data
Implements AES-256-GCM encryption for HIPAA compliance
"""

import base64
import json
from typing import Any, Dict
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.exceptions import InvalidTag
import structlog
import secrets

from app.core.config import settings


logger = structlog.get_logger(__name__)


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive PHI data
    Uses AES-256-GCM for authenticated encryption
    """

    def __init__(self, encryption_key: str = None):
        """
        Initialize encryption service

        Args:
            encryption_key: Base64-encoded 32-byte key (default: from settings)
        """
        if encryption_key is None:
            encryption_key = settings.PHI_ENCRYPTION_KEY

        # Decode the base64 key
        try:
            self.key = base64.b64decode(encryption_key)
            if len(self.key) != 32:
                raise ValueError(f"Encryption key must be 32 bytes, got {len(self.key)}")
        except Exception as e:
            logger.error("Invalid encryption key", error=str(e))
            raise ValueError(f"Invalid encryption key: {str(e)}")

        self.aesgcm = AESGCM(self.key)
        logger.info("Encryption service initialized")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext using AES-256-GCM

        Args:
            plaintext: Text to encrypt

        Returns:
            Base64-encoded encrypted data (includes nonce)

        Format: nonce (12 bytes) + ciphertext + tag (16 bytes)
        """
        if not plaintext:
            raise ValueError("Plaintext cannot be empty")

        try:
            # Generate a random 12-byte nonce
            nonce = secrets.token_bytes(12)

            # Encrypt the plaintext
            plaintext_bytes = plaintext.encode('utf-8')
            ciphertext = self.aesgcm.encrypt(nonce, plaintext_bytes, None)

            # Combine nonce and ciphertext
            encrypted_data = nonce + ciphertext

            # Encode as base64 for storage
            encoded = base64.b64encode(encrypted_data).decode('utf-8')

            logger.debug("Data encrypted", plaintext_length=len(plaintext))
            return encoded

        except Exception as e:
            logger.error("Encryption failed", error=str(e))
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt data encrypted with encrypt()

        Args:
            encrypted_data: Base64-encoded encrypted data

        Returns:
            Decrypted plaintext

        Raises:
            InvalidTag: If data has been tampered with
            ValueError: If data format is invalid
        """
        if not encrypted_data:
            raise ValueError("Encrypted data cannot be empty")

        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data)

            # Extract nonce (first 12 bytes) and ciphertext (rest)
            if len(encrypted_bytes) < 28:  # 12 (nonce) + 16 (min tag)
                raise ValueError("Encrypted data too short")

            nonce = encrypted_bytes[:12]
            ciphertext = encrypted_bytes[12:]

            # Decrypt
            plaintext_bytes = self.aesgcm.decrypt(nonce, ciphertext, None)
            plaintext = plaintext_bytes.decode('utf-8')

            logger.debug("Data decrypted")
            return plaintext

        except InvalidTag:
            logger.error("Decryption failed - data has been tampered with or key is incorrect")
            raise ValueError("Decryption failed - data integrity check failed")

        except Exception as e:
            logger.error("Decryption failed", error=str(e))
            raise

    def encrypt_json(self, data: Dict[str, Any]) -> str:
        """
        Encrypt a dictionary as JSON

        Args:
            data: Dictionary to encrypt

        Returns:
            Base64-encoded encrypted JSON
        """
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            return self.encrypt(json_str)
        except Exception as e:
            logger.error("JSON encryption failed", error=str(e))
            raise

    def decrypt_json(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt JSON-encoded data

        Args:
            encrypted_data: Base64-encoded encrypted JSON

        Returns:
            Decrypted dictionary
        """
        try:
            json_str = self.decrypt(encrypted_data)
            return json.loads(json_str)
        except Exception as e:
            logger.error("JSON decryption failed", error=str(e))
            raise

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new 32-byte encryption key

        Returns:
            Base64-encoded 32-byte key suitable for AES-256
        """
        key = secrets.token_bytes(32)
        encoded_key = base64.b64encode(key).decode('utf-8')
        return encoded_key

    def rotate_key(self, new_key: str, encrypted_data: str) -> str:
        """
        Re-encrypt data with a new key (for key rotation)

        Args:
            new_key: New base64-encoded 32-byte key
            encrypted_data: Data encrypted with current key

        Returns:
            Data re-encrypted with new key
        """
        # Decrypt with current key
        plaintext = self.decrypt(encrypted_data)

        # Create new encryption service with new key
        new_service = EncryptionService(new_key)

        # Re-encrypt with new key
        return new_service.encrypt(plaintext)


# Export singleton instance
encryption_service = EncryptionService()


def generate_encryption_key() -> str:
    """
    Utility function to generate a new encryption key
    Use this when setting up a new environment
    """
    return EncryptionService.generate_key()


if __name__ == "__main__":
    # Generate a new key for environment setup
    print("Generated PHI Encryption Key (save to .env as PHI_ENCRYPTION_KEY):")
    print(generate_encryption_key())
