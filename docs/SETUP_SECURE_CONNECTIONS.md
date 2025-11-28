# Quick Setup: Secure Database Connections

## Installation

1. **Install the cryptography package:**

```bash
pip install cryptography
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

2. **Restart the backend** (if it's running):

```bash
# Stop the current backend (Ctrl+C)
# Then restart:
python run_app.py
```

3. **Start the UI:**

```bash
streamlit run ui/app.py
```

## First Time Use

### Save Your First Connection

1. Open the app in your browser
2. Go to **"Chat with Database"** tab
3. Select your database type (e.g., PostgreSQL)
4. Fill in your credentials:
   - Host: `localhost`
   - Port: `5432`
   - Username: `your_username`
   - Password: `your_password`
   - Database: `your_database`

5. ✅ Check **"💾 Save this connection"**
6. Enter a name: `My Database`
7. Click **"Connect"**

✅ **Done!** Your connection is now saved securely.

### Use Your Saved Connection

Next time you want to connect:

1. Go to **"Chat with Database"** tab
2. Look for **"📌 Saved Connections"**
3. Select `My Database` from dropdown
4. Credentials auto-fill
5. Click **"Connect"**

That's it! No need to type credentials again.

## What Happens Behind the Scenes

When you save a connection:

1. ✅ Password is encrypted using Fernet encryption
2. ✅ Encrypted data saved to `.db_connections/connections.json`
3. ✅ Encryption key stored in `.db_connections/.key`
4. ✅ Key file permissions set to read-only (600)

When you load a connection:

1. ✅ Encrypted password is read from file
2. ✅ Password is decrypted using your machine's key
3. ✅ Credentials auto-fill in the form
4. ✅ You click Connect and you're in!

## Security Notes

### ✅ Safe to Do

- Save multiple connections
- Share connection names (without passwords)
- Commit code to git (`.db_connections/` is ignored)
- Use on your local machine

### ⚠️ DO NOT

- Share the `.db_connections/` folder
- Commit `.db_connections/` to git
- Share the `.key` file
- Manually edit encrypted files

## File Structure

After saving your first connection:

```
your-project/
├── .db_connections/          # Created automatically
│   ├── .key                  # Encryption key (SECRET!)
│   └── connections.json      # Encrypted connections
├── .gitignore                # Already includes .db_connections/
├── app/
├── ui/
└── ...
```

## Verify It's Working

### Check Files Were Created

```bash
# On Windows
dir .db_connections

# On Mac/Linux
ls -la .db_connections
```

You should see:
- `.key` file
- `connections.json` file

### Check Encryption

Open `.db_connections/connections.json` in a text editor.

You should see something like:
```json
{
  "My Database": {
    "type": "postgresql",
    "host": "localhost",
    "port": "5432",
    "username": "myuser",
    "password": "gAAAAABl...",  ← Encrypted!
    "database": "mydb"
  }
}
```

The password field should be a long encrypted string, NOT your actual password.

## Troubleshooting

### "ModuleNotFoundError: No module named 'cryptography'"

Install the package:
```bash
pip install cryptography
```

### "Permission denied" when saving

On Mac/Linux, fix permissions:
```bash
chmod 700 .db_connections
```

### "Connection not found" after restart

This is normal if:
- You deleted `.db_connections/` folder
- You're on a different machine
- The encryption key was lost

Solution: Save the connection again.

### Want to start fresh?

Remove all saved connections:
```bash
# Backup first (optional)
cp -r .db_connections .db_connections.backup

# Remove
rm -rf .db_connections
```

Next save will create new encryption key.

## Example: Save Multiple Connections

### Local Development
```
Name: "Local Dev"
Type: SQLite
Path: ./dev.db
```

### Staging Server
```
Name: "Staging"
Type: PostgreSQL
Host: staging.example.com
Port: 5432
Username: staging_user
Password: ********
Database: staging_db
```

### Production (Read-Only)
```
Name: "Production (RO)"
Type: PostgreSQL
Host: prod.example.com
Port: 5432
Username: readonly_user
Password: ********
Database: prod_db
```

Now you can quickly switch between environments!

## Next Steps

1. ✅ Save your frequently used connections
2. ✅ Test loading and connecting
3. ✅ Start chatting with your databases
4. ✅ Enjoy not typing passwords every time!

## Need Help?

- Read the full guide: `SECURE_CONNECTIONS_GUIDE.md`
- Check the UI guide: `UI_DATABASE_CHAT_GUIDE.md`
- Review error logs: `errorlog.txt`
