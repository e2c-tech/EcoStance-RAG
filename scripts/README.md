# Scripts Directory

Utility scripts for managing the application.

## Vault Management Scripts

### setup_vault_dev.py

Sets up HashiCorp Vault for development use.

**Usage:**
```bash
python scripts/setup_vault_dev.py
```

**What it does:**
- Connects to your local Vault server
- Generates a new encryption key
- Stores it securely in Vault
- Tests the integration

**Prerequisites:**
- Vault server running (`vault server -dev`)
- Environment variables set:
  - `VAULT_ENABLED=true`
  - `VAULT_ADDR=http://127.0.0.1:8200`
  - `VAULT_TOKEN=root`

### rotate_encryption_key.py

Rotates the encryption key stored in Vault.

**Usage:**
```bash
python scripts/rotate_encryption_key.py
```

**What it does:**
- Connects to Vault
- Shows current key (for backup)
- Generates a new encryption key
- Stores the new key in Vault
- Provides next steps

**⚠️ Warning:** This will invalidate all previously encrypted data. Make sure to:
1. Backup your database
2. Decrypt existing credentials
3. Re-encrypt with the new key

## Adding New Scripts

When adding new scripts:

1. Add a docstring at the top explaining what it does
2. Use `sys.path.insert(0, str(Path(__file__).parent.parent))` to import app modules
3. Add error handling and user-friendly messages
4. Document the script in this README
5. Add any required environment variables to `.env.example`

## Best Practices

- Always test scripts in development before running in production
- Use confirmation prompts for destructive operations
- Provide clear error messages
- Log important actions
- Include rollback instructions when applicable
