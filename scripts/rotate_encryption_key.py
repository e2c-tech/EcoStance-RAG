"""
Script to rotate encryption keys in Vault.
WARNING: This will invalidate all previously encrypted data!
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.vault_service import VaultService
from app.services.credential_service import CredentialService


def rotate_key():
    """Rotate the encryption key stored in Vault."""
    
    print("=" * 60)
    print("Encryption Key Rotation")
    print("=" * 60)
    print()
    print("⚠️  WARNING: This will generate a new encryption key!")
    print("⚠️  All previously encrypted data will become unreadable!")
    print()
    print("Before rotating, you should:")
    print("  1. Backup your database")
    print("  2. Decrypt all existing credentials")
    print("  3. Re-encrypt them with the new key")
    print()
    
    confirm = input("Are you sure you want to continue? (type 'yes' to confirm): ").strip()
    
    if confirm.lower() != "yes":
        print("❌ Key rotation cancelled.")
        return False
    
    print()
    print("🔐 Connecting to Vault...")
    
    vault = VaultService()
    
    if not vault.is_enabled():
        print("❌ Vault is not enabled or not accessible.")
        return False
    
    print("✅ Connected to Vault")
    print()
    
    # Read current key for backup
    print("📋 Reading current key...")
    current_key_data = vault.read_secret("app/encryption-key")
    
    if current_key_data:
        current_key = current_key_data.get("key", "")
        print(f"Current key: {current_key[:20]}...")
        print()
    
    # Generate new key
    print("🔑 Generating new encryption key...")
    new_key = CredentialService.generate_key()
    print(f"New key: {new_key[:20]}...")
    print()
    
    # Store new key
    print("💾 Storing new key in Vault...")
    success = vault.rotate_secret("app/encryption-key", {"key": new_key})
    
    if success:
        print("✅ Key rotated successfully!")
        print()
        print("📝 Next steps:")
        print("  1. Restart your application to use the new key")
        print("  2. Re-encrypt all existing credentials")
        print("  3. Update any external systems using the old key")
        print()
        
        if current_key_data:
            print("💡 Old key (for reference):")
            print(f"   {current_key}")
            print()
        
        return True
    else:
        print("❌ Failed to rotate key.")
        return False


if __name__ == "__main__":
    print()
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv not installed.")
        print()
    
    # Check if Vault is enabled
    if os.getenv("VAULT_ENABLED", "false").lower() != "true":
        print("❌ VAULT_ENABLED is not set to 'true'")
        print()
        print("Set VAULT_ENABLED=true in your .env file first.")
        sys.exit(1)
    
    # Run rotation
    rotate_key()
    print()
