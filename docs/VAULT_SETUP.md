# HashiCorp Vault Setup Guide

This guide explains how to set up HashiCorp Vault for secure secrets management in development and production.

## What is Vault?

HashiCorp Vault is a free, open-source tool for securely storing and accessing secrets like:
- Encryption keys
- Database passwords
- API keys
- Tokens

Instead of storing these in your code or `.env` files, Vault keeps them secure and provides features like:
- Automatic key rotation
- Access control
- Audit logging
- Encryption at rest

## Development Setup (Free & Local)

### 1. Install Vault

**Windows:**
```powershell
# Using Chocolatey
choco install vault

# Or download from: https://www.vaultproject.io/downloads
```

**macOS:**
```bash
brew install vault
```

**Linux:**
```bash
# Download and install from https://www.vaultproject.io/downloads
```

### 2. Start Vault in Development Mode

Development mode runs Vault in-memory (no persistence) with a root token. Perfect for testing!

```bash
vault server -dev
```

You'll see output like:
```
WARNING! dev mode is enabled!
...
Root Token: hvs.xxxxxxxxxxxxx
...
Unseal Key: xxxxxxxxxxxxx
```

**Important:** Keep this terminal window open! Vault runs in the foreground.

### 3. Configure Environment Variables

Add these to your `.env` file:

```env
# Enable Vault integration
VAULT_ENABLED=true

# Vault server address (dev mode default)
VAULT_ADDR=http://127.0.0.1:8200

# Root token from vault server output
VAULT_TOKEN=root
```

**Note:** In dev mode, the token is always `root`. In production, you'll use proper authentication.

### 4. Run Setup Script

```bash
python scripts/setup_vault_dev.py
```

This script will:
- Connect to Vault
- Generate a new encryption key
- Store it securely in Vault
- Test the integration

### 5. Update Your Application

Once Vault is set up, you can remove `ENCRYPTION_KEY` from your `.env` file. The application will automatically fetch it from Vault.

## How It Works

### Before (Without Vault)
```
.env file:
ENCRYPTION_KEY=abc123xyz...  ← Visible in plain text!
```

### After (With Vault)
```
.env file:
VAULT_ENABLED=true
VAULT_ADDR=http://127.0.0.1:8200
VAULT_TOKEN=root

Vault (secure storage):
app/encryption-key → abc123xyz...  ← Encrypted and secure!
```

## Key Rotation

Rotating keys regularly improves security. Here's how:

### Manual Rotation

```python
from app.services.credential_service import get_credential_service

cred_service = get_credential_service()
cred_service.rotate_encryption_key()
```

### Using the Setup Script

```bash
python scripts/setup_vault_dev.py
# Choose "yes" when asked to rotate the key
```

**Warning:** Rotating the encryption key will invalidate all previously encrypted data. You'll need to re-encrypt existing credentials.

## Vault CLI Commands

### View Stored Secrets

```bash
# List all secrets
vault kv list secret/

# Read a specific secret
vault kv get secret/app/encryption-key
```

### Manually Store a Secret

```bash
vault kv put secret/app/encryption-key key="your-key-here"
```

### Delete a Secret

```bash
vault kv delete secret/app/encryption-key
```

## Production Setup

For production, you'll want:

1. **Persistent Storage:** Don't use dev mode
2. **Proper Authentication:** Use AppRole, Kubernetes auth, or cloud IAM
3. **TLS/HTTPS:** Secure communication
4. **High Availability:** Multiple Vault servers
5. **Backup Strategy:** Regular backups of Vault data

### Production Configuration Example

```hcl
# vault.hcl
storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 0
  tls_cert_file = "/vault/certs/vault.crt"
  tls_key_file  = "/vault/certs/vault.key"
}

ui = true
```

Start production Vault:
```bash
vault server -config=vault.hcl
```

## Troubleshooting

### "Vault is not enabled"

Make sure `VAULT_ENABLED=true` in your `.env` file.

### "Failed to connect to Vault"

1. Check if Vault is running: `vault status`
2. Verify `VAULT_ADDR` is correct
3. Check if `VAULT_TOKEN` is valid

### "Authentication failed"

In dev mode, use `VAULT_TOKEN=root`. In production, use proper tokens.

### Vault server stopped

If you close the terminal running `vault server -dev`, all data is lost (it's in-memory). Just restart it and run the setup script again.

## Security Best Practices

1. **Never commit tokens:** Don't put `VAULT_TOKEN` in version control
2. **Use least privilege:** Give applications only the permissions they need
3. **Enable audit logging:** Track who accesses what
4. **Rotate keys regularly:** Automate key rotation
5. **Use TLS in production:** Always encrypt communication with Vault

## Alternative: Cloud-Managed Vault

If you don't want to manage Vault yourself, consider:

- **HashiCorp Cloud Platform (HCP) Vault:** Managed Vault service (paid)
- **AWS Secrets Manager:** AWS-native alternative (paid)
- **Azure Key Vault:** Azure-native alternative (paid)
- **Google Secret Manager:** GCP-native alternative (paid)

For development, the free local Vault is perfect!

## Next Steps

- [ ] Set up Vault in development
- [ ] Test encryption/decryption
- [ ] Implement key rotation schedule
- [ ] Plan production Vault deployment
- [ ] Set up monitoring and alerts

## Resources

- [Vault Documentation](https://www.vaultproject.io/docs)
- [Vault Getting Started](https://learn.hashicorp.com/vault)
- [Vault API Reference](https://www.vaultproject.io/api-docs)
