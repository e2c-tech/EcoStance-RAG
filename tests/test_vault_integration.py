"""
Tests for Vault integration with credential service.
"""
import os
import pytest
from unittest.mock import Mock, patch
from app.services.vault_service import VaultService
from app.services.credential_service import CredentialService


class TestVaultService:
    """Test Vault service functionality."""
    
    def test_vault_disabled_by_default(self):
        """Test that Vault is disabled when VAULT_ENABLED is not set."""
        with patch.dict(os.environ, {}, clear=True):
            vault = VaultService()
            assert not vault.is_enabled()
    
    def test_vault_initialization_without_token(self):
        """Test Vault initialization fails gracefully without token."""
        with patch.dict(os.environ, {"VAULT_ENABLED": "true"}, clear=True):
            vault = VaultService()
            assert not vault.is_enabled()
    
    @patch('hvac.Client')
    def test_vault_write_secret(self, mock_client):
        """Test writing secrets to Vault."""
        # Mock authenticated client
        mock_instance = Mock()
        mock_instance.is_authenticated.return_value = True
        mock_client.return_value = mock_instance
        
        with patch.dict(os.environ, {
            "VAULT_ENABLED": "true",
            "VAULT_TOKEN": "test-token"
        }):
            vault = VaultService()
            vault.client = mock_instance
            vault.enabled = True
            
            result = vault.write_secret("test/path", {"key": "value"})
            assert result is True
    
    @patch('hvac.Client')
    def test_vault_read_secret(self, mock_client):
        """Test reading secrets from Vault."""
        # Mock authenticated client
        mock_instance = Mock()
        mock_instance.is_authenticated.return_value = True
        mock_instance.secrets.kv.v2.read_secret_version.return_value = {
            'data': {'data': {'key': 'value'}}
        }
        mock_client.return_value = mock_instance
        
        with patch.dict(os.environ, {
            "VAULT_ENABLED": "true",
            "VAULT_TOKEN": "test-token"
        }):
            vault = VaultService()
            vault.client = mock_instance
            vault.enabled = True
            
            result = vault.read_secret("test/path")
            assert result == {'key': 'value'}


class TestCredentialServiceWithVault:
    """Test credential service with Vault integration."""
    
    def test_credential_service_without_vault(self):
        """Test credential service works without Vault."""
        with patch.dict(os.environ, {
            "ENCRYPTION_KEY": "test-key-for-testing-purposes-only-32b="
        }):
            # Should fall back to environment variable
            cred_service = CredentialService(use_vault=False)
            assert cred_service is not None
    
    def test_credential_service_with_vault_disabled(self):
        """Test credential service falls back to env var when Vault is disabled."""
        with patch.dict(os.environ, {
            "VAULT_ENABLED": "false",
            "ENCRYPTION_KEY": "test-key-for-testing-purposes-only-32b="
        }):
            cred_service = CredentialService(use_vault=True)
            assert cred_service is not None
    
    @patch('app.services.credential_service._get_vault_service')
    def test_credential_service_loads_key_from_vault(self, mock_get_vault):
        """Test credential service loads key from Vault when available."""
        # Mock Vault service
        mock_vault = Mock()
        mock_vault.is_enabled.return_value = True
        mock_vault.read_secret.return_value = {
            "key": "dGVzdC1rZXktZnJvbS12YXVsdC1mb3ItdGVzdGluZy0zMmI9"
        }
        mock_get_vault.return_value = mock_vault
        
        cred_service = CredentialService(use_vault=True)
        assert cred_service is not None
    
    def test_encryption_decryption_works(self):
        """Test basic encryption/decryption functionality."""
        with patch.dict(os.environ, {
            "ENCRYPTION_KEY": "dGVzdC1rZXktZm9yLXRlc3RpbmctcHVycG9zZXMtb25seS0zMmI9"
        }):
            cred_service = CredentialService(use_vault=False)
            
            test_data = "sensitive_password_123"
            encrypted = cred_service.encrypt_credential(test_data)
            decrypted = cred_service.decrypt_credential(encrypted)
            
            assert decrypted == test_data
            assert encrypted != test_data
    
    def test_generate_key(self):
        """Test key generation."""
        key = CredentialService.generate_key()
        assert key is not None
        assert len(key) > 0
        assert isinstance(key, str)


class TestKeyRotation:
    """Test key rotation functionality."""
    
    @patch('app.services.credential_service._get_vault_service')
    def test_rotate_encryption_key(self, mock_get_vault):
        """Test encryption key rotation."""
        # Mock Vault service
        mock_vault = Mock()
        mock_vault.is_enabled.return_value = True
        mock_vault.rotate_secret.return_value = True
        mock_vault.read_secret.return_value = {
            "key": "dGVzdC1rZXktZnJvbS12YXVsdC1mb3ItdGVzdGluZy0zMmI9"
        }
        mock_get_vault.return_value = mock_vault
        
        cred_service = CredentialService(use_vault=True)
        result = cred_service.rotate_encryption_key()
        
        assert result is True
        mock_vault.rotate_secret.assert_called_once()
    
    @patch('app.services.credential_service._get_vault_service')
    def test_store_key_in_vault(self, mock_get_vault):
        """Test storing key in Vault."""
        # Mock Vault service
        mock_vault = Mock()
        mock_vault.is_enabled.return_value = True
        mock_vault.write_secret.return_value = True
        mock_vault.read_secret.return_value = {
            "key": "dGVzdC1rZXktZnJvbS12YXVsdC1mb3ItdGVzdGluZy0zMmI9"
        }
        mock_get_vault.return_value = mock_vault
        
        cred_service = CredentialService(use_vault=True)
        result = cred_service.store_key_in_vault("test-key")
        
        assert result is True
        mock_vault.write_secret.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
