"""
Vault Service for managing secrets with HashiCorp Vault.
Provides a simple interface for storing and retrieving secrets.
"""
import os
import logging
from typing import Optional, Dict, Any
import hvac
from hvac.exceptions import VaultError

logger = logging.getLogger(__name__)


class VaultService:
    """
    Service for interacting with HashiCorp Vault.
    Supports both development (dev server) and production modes.
    """
    
    def __init__(
        self,
        vault_url: Optional[str] = None,
        vault_token: Optional[str] = None,
        mount_point: str = "secret"
    ):
        """
        Initialize Vault service.
        
        Args:
            vault_url: Vault server URL (default: from VAULT_ADDR env var or http://127.0.0.1:8200)
            vault_token: Vault authentication token (default: from VAULT_TOKEN env var)
            mount_point: KV secrets engine mount point (default: "secret")
        """
        self.vault_url = vault_url or os.getenv("VAULT_ADDR", "http://127.0.0.1:8200")
        self.vault_token = vault_token or os.getenv("VAULT_TOKEN")
        self.mount_point = mount_point
        self.client: Optional[hvac.Client] = None
        self.enabled = os.getenv("VAULT_ENABLED", "false").lower() == "true"
        
        if self.enabled:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize and authenticate Vault client."""
        try:
            if not self.vault_token:
                logger.warning("VAULT_TOKEN not set. Vault integration disabled.")
                self.enabled = False
                return
            
            self.client = hvac.Client(url=self.vault_url, token=self.vault_token)
            
            # Verify authentication
            if not self.client.is_authenticated():
                logger.error("Vault authentication failed. Check VAULT_TOKEN.")
                self.enabled = False
                return
            
            logger.info(f"Vault service initialized successfully at {self.vault_url}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vault client: {e}")
            self.enabled = False
    
    def is_enabled(self) -> bool:
        """Check if Vault is enabled and ready."""
        return self.enabled and self.client is not None
    
    def write_secret(self, path: str, secret_data: Dict[str, Any]) -> bool:
        """
        Write a secret to Vault.
        
        Args:
            path: Secret path (e.g., "app/encryption-key")
            secret_data: Dictionary of secret key-value pairs
            
        Returns:
            True if successful, False otherwise
            
        Example:
            >>> vault.write_secret("app/db-password", {"password": "secret123"})
        """
        if not self.is_enabled():
            logger.warning("Vault is not enabled. Secret not written.")
            return False
        
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=secret_data,
                mount_point=self.mount_point
            )
            logger.info(f"Secret written to Vault: {path}")
            return True
            
        except VaultError as e:
            logger.error(f"Failed to write secret to Vault: {e}")
            return False
    
    def read_secret(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Read a secret from Vault.
        
        Args:
            path: Secret path (e.g., "app/encryption-key")
            
        Returns:
            Dictionary of secret data, or None if not found
            
        Example:
            >>> data = vault.read_secret("app/db-password")
            >>> password = data.get("password")
        """
        if not self.is_enabled():
            logger.warning("Vault is not enabled. Cannot read secret.")
            return None
        
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=self.mount_point
            )
            secret_data = response['data']['data']
            logger.debug(f"Secret read from Vault: {path}")
            return secret_data
            
        except VaultError as e:
            logger.error(f"Failed to read secret from Vault: {e}")
            return None
    
    def delete_secret(self, path: str) -> bool:
        """
        Delete a secret from Vault.
        
        Args:
            path: Secret path to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Vault is not enabled. Cannot delete secret.")
            return False
        
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path,
                mount_point=self.mount_point
            )
            logger.info(f"Secret deleted from Vault: {path}")
            return True
            
        except VaultError as e:
            logger.error(f"Failed to delete secret from Vault: {e}")
            return False
    
    def list_secrets(self, path: str = "") -> Optional[list]:
        """
        List secrets at a given path.
        
        Args:
            path: Path to list (empty for root)
            
        Returns:
            List of secret names, or None if error
        """
        if not self.is_enabled():
            logger.warning("Vault is not enabled. Cannot list secrets.")
            return None
        
        try:
            response = self.client.secrets.kv.v2.list_secrets(
                path=path,
                mount_point=self.mount_point
            )
            return response['data']['keys']
            
        except VaultError as e:
            logger.error(f"Failed to list secrets from Vault: {e}")
            return None
    
    def rotate_secret(self, path: str, new_secret_data: Dict[str, Any]) -> bool:
        """
        Rotate a secret by writing a new version.
        
        Args:
            path: Secret path
            new_secret_data: New secret data
            
        Returns:
            True if successful, False otherwise
        """
        return self.write_secret(path, new_secret_data)


# Global instance
_vault_service: Optional[VaultService] = None


def get_vault_service() -> VaultService:
    """
    Get or create global Vault service instance.
    
    Returns:
        VaultService instance
    """
    global _vault_service
    
    if _vault_service is None:
        _vault_service = VaultService()
    
    return _vault_service
