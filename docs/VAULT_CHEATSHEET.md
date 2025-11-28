# Vault Cheat Sheet

Quick reference for common Vault operations.

## Installation

```bash
# Windows
choco install vault

# macOS
brew install vault

# Linux
# Download from https://www.vaultproject.io/downloads
```

## Development Mode

### Start Vault Dev Server
```bash
vault server -dev
```

### Environment Variables (.env)
```env
VAULT_ENABLED=true
VAULT_ADDR=http://127.0.0.1:8200
VAULT_TOKEN=root
```

### Setup
```bash
pip install hvac
python scripts/setup_vault_dev.py
```

## Vault CLI Commands

### Check Status
```bash
vault status
```

### List Secrets
```bash
vault kv list secret/
vault kv list secret/app/
```

### Read Secret
```bash
vault kv get secret/app/encryption-key
```

### Write Secret
```bash
vault kv put secret/app/encryption-key key="your-key-here"
```

### Delete Secret
```bash
vault kv delete secret/app/encryption-key
```

### Get Secret Value Only
```bash
vault kv get -field=key secret/app/encryption-key
```

## Python Usage

### Import Services
```python
from app.services.vault_service import get_vault_service
from app.services.credential_service import get_credential_service
```

### Use Vault Service
```python
vault = get_vault_service()

# Write secret
vault.write_secret("app/my-secret", {"password": "secret123"})

# Read secret
data = vault.read_secret("app/my-secret")
password = data.get("password")

# Delete secret
vault.delete_secret("app/my-secret")

# List secrets
secrets = vault.list_secrets("app/")
```

### Use Credential Service
```python
cred_service = get_credential_service()

# Encrypt
encrypted = cred_service.encrypt_credential("sensitive_data")

# Decrypt
decrypted = cred_service.decrypt_credential(encrypted)

# Rotate key
cred_service.rotate_encryption_key()
```

## Scripts

### Setup Vault
```bash
python scripts/setup_vault_dev.py
```

### Rotate Key
```bash
python scripts/rotate_encryption_key.py
```

## Testing

### Run Tests
```bash
pytest tests/test_vault_integration.py -v
```

### Test Specific Function
```bash
pytest tests/test_vault_integration.py::TestVaultService::test_vault_write_secret -v
```

## Troubleshooting

### Connection Issues
```bash
# Check if Vault is running
vault status

# Check connectivity
curl http://127.0.0.1:8200/v1/sys/health
```

### Authentication Issues
```bash
# Verify token
vault token lookup

# Create new token (dev mode)
vault token create
```

### Reset Dev Server
```bash
# Stop Vault (Ctrl+C)
# Restart
vault server -dev
# Re-run setup
python scripts/setup_vault_dev.py
```

## Production Commands

### Initialize Vault (First Time)
```bash
vault operator init
# Save unseal keys and root token!
```

### Unseal Vault
```bash
vault operator unseal <key1>
vault operator unseal <key2>
vault operator unseal <key3>
```

### Seal Vault
```bash
vault operator seal
```

### Create Token
```bash
vault token create -policy=app-policy
```

### Enable Audit Log
```bash
vault audit enable file file_path=/vault/logs/audit.log
```

## Environment Variables

### Development
```env
VAULT_ENABLED=true
VAULT_ADDR=http://127.0.0.1:8200
VAULT_TOKEN=root
```

### Production
```env
VAULT_ENABLED=true
VAULT_ADDR=https://vault.company.com:8200
VAULT_TOKEN=<secure-token>
```

### Disable Vault
```env
VAULT_ENABLED=false
ENCRYPTION_KEY=<fallback-key>
```

## Common Paths

### Application Secrets
- `secret/app/encryption-key` - Main encryption key
- `secret/app/db-password` - Database password
- `secret/app/api-key` - API keys

### Naming Convention
```
secret/
  app/
    encryption-key
    jwt-secret
    db-password
  tenant/
    {tenant-id}/
      api-key
      custom-config
```

## Quick Checks

### Is Vault Running?
```bash
vault status
```

### Is App Using Vault?
Check logs for:
```
INFO: Encryption key loaded from Vault
```

### Test Encryption
```python
from app.services.credential_service import get_credential_service

cred = get_credential_service()
assert cred.test_encryption()
```

## Emergency Procedures

### Vault Down - Use Fallback
```env
VAULT_ENABLED=false
ENCRYPTION_KEY=<backup-key>
```

### Lost Root Token
In dev mode: Restart Vault (data is lost)
In production: Use recovery keys to generate new token

### Corrupted Secret
```bash
# Delete corrupted secret
vault kv delete secret/app/encryption-key

# Recreate
python scripts/setup_vault_dev.py
```

## Best Practices

✅ Never commit `VAULT_TOKEN` to git  
✅ Use TLS in production  
✅ Rotate keys regularly  
✅ Backup Vault data  
✅ Monitor Vault health  
✅ Use least privilege tokens  
✅ Enable audit logging  
✅ Test disaster recovery  

## Resources

- [Full Setup Guide](VAULT_SETUP.md)
- [Quick Start](VAULT_QUICKSTART.md)
- [Migration Guide](VAULT_MIGRATION_GUIDE.md)
- [Vault Docs](https://www.vaultproject.io/docs)
