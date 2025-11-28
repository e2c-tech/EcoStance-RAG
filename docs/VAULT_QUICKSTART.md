# Vault Quick Start (5 Minutes)

Get HashiCorp Vault running locally in 5 minutes!

## Step 1: Install Vault (2 minutes)

### Windows
Download from: https://www.vaultproject.io/downloads

Or use Chocolatey:
```powershell
choco install vault
```

### macOS
```bash
brew install vault
```

### Linux
```bash
# Download from https://www.vaultproject.io/downloads
# Or use your package manager
```

Verify installation:
```bash
vault --version
```

## Step 2: Start Vault Dev Server (30 seconds)

Open a terminal and run:
```bash
vault server -dev
```

**Keep this terminal open!** You should see:
```
Root Token: root
...
```

## Step 3: Configure Your App (1 minute)

Add to your `.env` file:
```env
VAULT_ENABLED=true
VAULT_ADDR=http://127.0.0.1:8200
VAULT_TOKEN=root
```

## Step 4: Setup Vault (1 minute)

Install the Vault client library:
```bash
pip install hvac
```

Run the setup script:
```bash
python scripts/setup_vault_dev.py
```

## Step 5: Test It! (30 seconds)

Start your app:
```bash
python run_app.py
```

Your app now fetches the encryption key from Vault instead of the `.env` file!

## What Just Happened?

1. ✅ Vault is running locally on your machine
2. ✅ Your encryption key is stored securely in Vault
3. ✅ Your app automatically fetches it when needed
4. ✅ You can remove `ENCRYPTION_KEY` from `.env`

## Next Steps

- Read the full [Vault Setup Guide](VAULT_SETUP.md)
- Learn about [key rotation](VAULT_SETUP.md#key-rotation)
- Plan your [production setup](VAULT_SETUP.md#production-setup)

## Troubleshooting

**"Connection refused"**
- Make sure `vault server -dev` is running
- Check `VAULT_ADDR=http://127.0.0.1:8200`

**"Authentication failed"**
- In dev mode, use `VAULT_TOKEN=root`

**"Vault is not enabled"**
- Set `VAULT_ENABLED=true` in `.env`

## Stop Vault

Press `Ctrl+C` in the terminal running Vault.

**Note:** Dev mode stores data in memory. When you stop Vault, all data is lost. Just restart and run the setup script again!
