"""
Setup script for HashiCorp Vault in development mode.
This script helps initialize Vault and store the encryption key.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.vault_service import VaultService
from app.services.credential_service import CredentialService


def setup_vault_dev():
    """Setup Vault for development with encryption key."""
    
    print("=" * 60)
    print("HashiCorp Vault Development Setup")
    print("=" * 60)
    print()
    
    # Check if Vault is enabled
    vault_enabled = os.getenv("VAULT_ENABLED", "false").lower() == "true"
    
    if not vault_enabled:
        print("⚠️  VAULT_ENABLED is not set to 'true' in your environment.")
        print()
        print("To enable Vault, add to your .env file:")
        print("VAULT_ENABLED=true")
        print("VAULT_ADDR=http://127.0.0.1:8200")
        print("VAULT_TOKEN=root")
        print()
        return False
    
    # Initialize Vault service
    print("🔐 Connecting to Vault...")
    vault = VaultService()
    
    if not vault.is_enabled():
        print("❌ Failed to connect to Vault.")
        print()
        print("Make sure Vault is running:")
        print("  vault server -dev")
        print()
        print("And set these environment variables:")
        print("  VAULT_ENABLED=true")
        print("  VAULT_ADDR=http://127.0.0.1:8200")
        print("  VAULT_TOKEN=root")
        return False
    
    print("✅ Connected to Vault successfully!")
    print()
    
    # Check if encryption key already exists
    existing_key = vault.read_secret("app/encryption-key")
    
    if existing_key:
        print("📋 Encryption key already exists in Vault.")
        print()
        choice = input("Do you want to rotate it? (yes/no): ").strip().lower()
        
        if choice != "yes":
            print("Keeping existing key.")
            return True
    
    # Generate and store new key
    print("🔑 Generating new encryption key...")
    new_key = CredentialService.generate_key()
    
    print(f"Generated key: {new_key[:20]}...")
    print()
    
    print("💾 Storing key in Vault...")
    success = vault.write_secret("app/encryption-key", {"key": new_key})
    
    if success:
        print("✅ Encryption key stored in Vault successfully!")
        print()
        print("🎉 Vault setup complete!")
        print()
        print("You can now remove ENCRYPTION_KEY from your .env file.")
        print("The application will automatically fetch it from Vault.")
        return True
    else:
        print("❌ Failed to store key in Vault.")
        return False


def test_vault_integration():
    """Test Vault integration with credential service."""
    
    print()
    print("=" * 60)
    print("Testing Vault Integration")
    print("=" * 60)
    print()
    
    try:
        print("🧪 Initializing credential service with Vault...")
        cred_service = CredentialService(use_vault=True)
        
        print("✅ Credential service initialized!")
        print()
        
        print("🧪 Testing encryption/decryption...")
        test_result = cred_service.test_encryption()
        
        if test_result:
            print("✅ Encryption test passed!")
            print()
            print("🎉 All tests passed! Vault integration is working correctly.")
            return True
        else:
            print("❌ Encryption test failed.")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print()
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv not installed. Make sure environment variables are set.")
        print()
    
    # Run setup
    setup_success = setup_vault_dev()
    
    if setup_success:
        # Run tests
        test_vault_integration()
    
    print()
