"""
Credential Service for secure encryption/decryption of database credentials.
Uses Fernet symmetric encryption for storing sensitive connection strings.
Supports HashiCorp Vault for secure key storage.
"""
import os
import logging
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

logger = logging.getLogger(__name__)

# Import Vault service (lazy import to avoid circular dependencies)
def _get_vault_service():
    try:
        from app.services.vault_service import get_vault_service
        return get_vault_service()
    except ImportError:
        return None


class CredentialService:
    """
    Service for encrypting and decrypting database credentials.
    Uses Fernet symmetric encryption with a key derived from environment variable.
    """
    
    def __init__(self, encryption_key: Optional[str] = None, use_vault: bool = True):
        """
        Initialize credential service with encryption key.
        
        Args:
            encryption_key: Base64-encoded Fernet key or passphrase.
                          If None, attempts to read from Vault, then falls back to ENCRYPTION_KEY env var.
            use_vault: Whether to attempt using Vault for key storage (default: True)
        """
        self.vault_service = _get_vault_service() if use_vault else None
        
        # Try to get encryption key from Vault first
        if encryption_key is None and self.vault_service and self.vault_service.is_enabled():
            vault_data = self.vault_service.read_secret("app/encryption-key")
            if vault_data:
                encryption_key = vault_data.get("key")
                logger.info("Encryption key loaded from Vault")
        
        # Fall back to environment variable
        if encryption_key is None:
            encryption_key = os.getenv("ENCRYPTION_KEY")
        
        if not encryption_key:
            raise ValueError(
                "ENCRYPTION_KEY must be set in Vault or environment variable. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        try:
            # Try to use as Fernet key directly
            self.fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        except Exception:
            # If not a valid Fernet key, derive one from passphrase
            self.fernet = self._derive_key_from_passphrase(encryption_key)
        
        logger.info("Credential service initialized")
    
    def _derive_key_from_passphrase(self, passphrase: str) -> Fernet:
        """
        Derive a Fernet key from a passphrase using PBKDF2.
        
        Args:
            passphrase: User-provided passphrase
            
        Returns:
            Fernet instance with derived key
        """
        # Use a fixed salt (in production, store this securely)
        salt = b'tenant_multitenancy_salt_v1'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        return Fernet(key)
    
    def encrypt_credential(self, credential: str) -> str:
        """
        Encrypt a credential string (e.g., database URI, password).
        
        Args:
            credential: Plain text credential to encrypt
            
        Returns:
            Base64-encoded encrypted credential
            
        Example:
            >>> service = CredentialService()
            >>> encrypted = service.encrypt_credential("postgresql://user:pass@host/db")
            >>> print(encrypted)
            'gAAAAABh...'
        """
        try:
            encrypted_bytes = self.fernet.encrypt(credential.encode())
            encrypted_str = encrypted_bytes.decode()
            logger.debug("Credential encrypted successfully")
            return encrypted_str
        except Exception as e:
            logger.error(f"Failed to encrypt credential: {e}")
            raise
    
    def decrypt_credential(self, encrypted_credential: str) -> str:
        """
        Decrypt an encrypted credential string.
        
        Args:
            encrypted_credential: Base64-encoded encrypted credential
            
        Returns:
            Decrypted plain text credential
            
        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
            
        Example:
            >>> service = CredentialService()
            >>> decrypted = service.decrypt_credential(encrypted)
            >>> print(decrypted)
            'postgresql://user:pass@host/db'
        """
        try:
            decrypted_bytes = self.fernet.decrypt(encrypted_credential.encode())
            decrypted_str = decrypted_bytes.decode()
            logger.debug("Credential decrypted successfully")
            return decrypted_str
        except Exception as e:
            logger.error(f"Failed to decrypt credential: {e}")
            raise
    
    def encrypt_connection_config(self, config: dict) -> dict:
        """
        Encrypt sensitive fields in a connection configuration dictionary.
        
        Args:
            config: Connection configuration with sensitive fields
            
        Returns:
            Configuration with encrypted sensitive fields
            
        Example:
            >>> config = {
            ...     'type': 'postgresql',
            ...     'host': 'localhost',
            ...     'password': 'secret123',
            ...     'username': 'user'
            ... }
            >>> encrypted_config = service.encrypt_connection_config(config)
        """
        encrypted_config = config.copy()
        
        # Fields to encrypt
        sensitive_fields = ['password', 'api_key', 'secret', 'token']
        
        for field in sensitive_fields:
            if field in encrypted_config and encrypted_config[field]:
                encrypted_config[field] = self.encrypt_credential(str(encrypted_config[field]))
                encrypted_config[f'{field}_encrypted'] = True
        
        return encrypted_config
    
    def decrypt_connection_config(self, config: dict) -> dict:
        """
        Decrypt sensitive fields in a connection configuration dictionary.
        
        Args:
            config: Connection configuration with encrypted sensitive fields
            
        Returns:
            Configuration with decrypted sensitive fields
        """
        decrypted_config = config.copy()
        
        # Fields that might be encrypted
        sensitive_fields = ['password', 'api_key', 'secret', 'token']
        
        for field in sensitive_fields:
            if f'{field}_encrypted' in decrypted_config and decrypted_config.get(f'{field}_encrypted'):
                if field in decrypted_config and decrypted_config[field]:
                    decrypted_config[field] = self.decrypt_credential(decrypted_config[field])
                    del decrypted_config[f'{field}_encrypted']
        
        return decrypted_config
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.
        
        Returns:
            Base64-encoded Fernet key as string
            
        Example:
            >>> key = CredentialService.generate_key()
            >>> print(key)
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx='
        """
        key = Fernet.generate_key()
        return key.decode()
    
    def store_key_in_vault(self, key: Optional[str] = None) -> bool:
        """
        Store the encryption key in Vault.
        
        Args:
            key: Encryption key to store. If None, generates a new one.
            
        Returns:
            True if successful, False otherwise
        """
        if not self.vault_service or not self.vault_service.is_enabled():
            logger.warning("Vault is not enabled. Cannot store key.")
            return False
        
        if key is None:
            key = self.generate_key()
        
        return self.vault_service.write_secret("app/encryption-key", {"key": key})
    
    def rotate_encryption_key(self, new_key: Optional[str] = None) -> bool:
        """
        Rotate the encryption key in Vault.
        WARNING: This will invalidate all previously encrypted data.
        
        Args:
            new_key: New encryption key. If None, generates a new one.
            
        Returns:
            True if successful, False otherwise
        """
        if not self.vault_service or not self.vault_service.is_enabled():
            logger.warning("Vault is not enabled. Cannot rotate key.")
            return False
        
        if new_key is None:
            new_key = self.generate_key()
        
        success = self.vault_service.rotate_secret("app/encryption-key", {"key": new_key})
        
        if success:
            logger.info("Encryption key rotated successfully in Vault")
        
        return success
    
    def test_encryption(self) -> bool:
        """
        Test encryption/decryption functionality.
        
        Returns:
            True if test passes, False otherwise
        """
        try:
            test_string = "test_credential_12345"
            encrypted = self.encrypt_credential(test_string)
            decrypted = self.decrypt_credential(encrypted)
            
            if decrypted == test_string:
                logger.info("Encryption test passed")
                return True
            else:
                logger.error("Encryption test failed: decrypted value doesn't match")
                return False
        except Exception as e:
            logger.error(f"Encryption test failed: {e}")
            return False


# Global instance
_credential_service: Optional[CredentialService] = None


def get_credential_service() -> CredentialService:
    """
    Get or create global credential service instance.
    
    Returns:
        CredentialService instance
    """
    global _credential_service
    
    if _credential_service is None:
        _credential_service = CredentialService()
    
    return _credential_service


def generate_encryption_key() -> str:
    """
    Convenience function to generate a new encryption key.
    
    Returns:
        Base64-encoded Fernet key
    """
    return CredentialService.generate_key()


if __name__ == "__main__":
    # Generate a new key for setup
    print("Generated Encryption Key:")
    print(generate_encryption_key())
    print("\nAdd this to your .env file as:")
    print("ENCRYPTION_KEY=<generated_key>")
