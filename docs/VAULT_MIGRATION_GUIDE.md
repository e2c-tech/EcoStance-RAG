# Migrating to Vault - Step by Step Guide

This guide helps you migrate from storing encryption keys in `.env` files to using HashiCorp Vault.

## Why Migrate?

**Before (Current):**
- Encryption key stored in plain text in `.env` file
- Risk of accidental exposure (git commits, logs, etc.)
- Manual key rotation is complex
- No audit trail of key access

**After (With Vault):**
- Encryption key stored securely in Vault
- Encrypted at rest
- Easy key rotation with scripts
- Audit logging (production)
- Centralized secrets management

## Migration Steps

### Step 1: Backup Current Setup

Before making any changes, backup your current configuration:

```bash
# Backup your .env file
copy .env .env.backup

# Backup your database
# (Use your database's backup tool)
```

### Step 2: Install Vault

**Windows:**
```powershell
choco install vault
```

**macOS:**
```bash
brew install vault
```

**Linux:**
Download from https://www.vaultproject.io/downloads

Verify installation:
```bash
vault --version
```

### Step 3: Start Vault (Development)

Open a new terminal and start Vault in dev mode:

```bash
vault server -dev
```

**Important:** Keep this terminal open! Note the output:
```
Root Token: root
Unseal Key: ...
```

### Step 4: Install Vault Client Library

```bash
pip install hvac
```

### Step 5: Configure Environment Variables

Add these to your `.env` file (keep existing variables):

```env
# Enable Vault
VAULT_ENABLED=true
VAULT_ADDR=http://127.0.0.1:8200
VAULT_TOKEN=root

# Keep ENCRYPTION_KEY for now (fallback)
ENCRYPTION_KEY=your-existing-key
```

### Step 6: Run Setup Script

This will migrate your encryption key to Vault:

```bash
python scripts/setup_vault_dev.py
```

The script will:
1. Connect to Vault
2. Generate a new encryption key (or use existing)
3. Store it in Vault
4. Test the integration

### Step 7: Test Your Application

Start your application and verify it works:

```bash
python run_app.py
```

The application should:
- Connect to Vault successfully
- Load the encryption key from Vault
- Work exactly as before

Check the logs for:
```
INFO: Encryption key loaded from Vault
INFO: Credential service initialized
```

### Step 8: Verify Vault Integration

Test that Vault is actually being used:

1. Stop your application
2. Temporarily disable Vault:
   ```env
   VAULT_ENABLED=false
   ```
3. Start your application - it should use `ENCRYPTION_KEY` from `.env`
4. Re-enable Vault:
   ```env
   VAULT_ENABLED=true
   ```
5. Start your application - it should use Vault again

### Step 9: Remove Encryption Key from .env (Optional)

Once you're confident Vault is working, you can remove the encryption key from `.env`:

```env
# Remove or comment out:
# ENCRYPTION_KEY=your-key-here

# Keep Vault config:
VAULT_ENABLED=true
VAULT_ADDR=http://127.0.0.1:8200
VAULT_TOKEN=root
```

**Note:** Keep `ENCRYPTION_KEY` as a fallback during initial testing.

### Step 10: Update Your Team

If working in a team, inform everyone about the change:

1. Share the Vault setup instructions
2. Update your project README
3. Ensure everyone has Vault installed
4. Provide the Vault token (securely!)

## Rollback Plan

If something goes wrong, you can easily rollback:

1. Stop your application
2. Disable Vault in `.env`:
   ```env
   VAULT_ENABLED=false
   ```
3. Ensure `ENCRYPTION_KEY` is set in `.env`
4. Restart your application

Your application will work exactly as before.

## Production Migration

For production environments:

### 1. Plan the Migration

- Schedule during low-traffic period
- Notify users of potential downtime
- Prepare rollback plan
- Test in staging first

### 2. Set Up Production Vault

Don't use dev mode! Use a proper Vault setup:

```bash
# Create vault config
cat > vault.hcl <<EOF
storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_cert_file = "/vault/certs/vault.crt"
  tls_key_file  = "/vault/certs/vault.key"
}

ui = true
EOF

# Start Vault
vault server -config=vault.hcl
```

### 3. Initialize and Unseal Vault

```bash
# Initialize (first time only)
vault operator init

# Save the unseal keys and root token securely!

# Unseal Vault (required after every restart)
vault operator unseal <unseal-key-1>
vault operator unseal <unseal-key-2>
vault operator unseal <unseal-key-3>
```

### 4. Configure Production Environment

```env
VAULT_ENABLED=true
VAULT_ADDR=https://vault.yourcompany.com:8200
VAULT_TOKEN=<production-token>
```

### 5. Migrate Encryption Key

```bash
# Run setup script in production
python scripts/setup_vault_dev.py
```

### 6. Deploy and Monitor

- Deploy application updates
- Monitor logs for Vault connection issues
- Check application functionality
- Monitor performance metrics

## Troubleshooting

### "Connection refused" Error

**Problem:** Can't connect to Vault

**Solution:**
1. Check if Vault is running: `vault status`
2. Verify `VAULT_ADDR` is correct
3. Check firewall settings

### "Authentication failed" Error

**Problem:** Invalid Vault token

**Solution:**
1. In dev mode, use `VAULT_TOKEN=root`
2. In production, verify token is valid: `vault token lookup`
3. Generate new token if needed: `vault token create`

### "Vault is not enabled" Warning

**Problem:** Application not using Vault

**Solution:**
1. Check `.env` file: `VAULT_ENABLED=true`
2. Restart application
3. Check logs for Vault initialization

### Application Won't Start

**Problem:** Missing encryption key

**Solution:**
1. Temporarily disable Vault: `VAULT_ENABLED=false`
2. Add `ENCRYPTION_KEY` to `.env`
3. Start application
4. Debug Vault issue
5. Re-enable Vault

## Best Practices

1. **Always backup** before migrating
2. **Test in development** before production
3. **Keep fallback** (ENCRYPTION_KEY) during initial testing
4. **Monitor logs** after migration
5. **Document changes** for your team
6. **Secure Vault tokens** - never commit to git
7. **Use TLS** in production
8. **Regular backups** of Vault data
9. **Test rollback** procedure
10. **Rotate keys** regularly

## Next Steps

After successful migration:

- [ ] Set up key rotation schedule
- [ ] Configure Vault backups
- [ ] Set up monitoring and alerts
- [ ] Document Vault access procedures
- [ ] Train team on Vault usage
- [ ] Plan production Vault deployment
- [ ] Implement audit logging
- [ ] Set up high availability (production)

## Support

For help:
1. Check [VAULT_SETUP.md](VAULT_SETUP.md) for detailed setup
2. Check [VAULT_QUICKSTART.md](VAULT_QUICKSTART.md) for quick reference
3. Review [Vault documentation](https://www.vaultproject.io/docs)
4. Run tests: `pytest tests/test_vault_integration.py -v`

## Summary

✅ Vault provides secure, centralized secrets management  
✅ Migration is straightforward with provided scripts  
✅ Easy rollback if needed  
✅ Works in both development and production  
✅ Free and open-source  

Happy migrating! 🚀
