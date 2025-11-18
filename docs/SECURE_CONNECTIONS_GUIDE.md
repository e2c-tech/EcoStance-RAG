# Secure Database Connections Guide

## Overview

The application now includes a secure connection manager that allows you to save database credentials safely. Passwords are encrypted before storage using industry-standard encryption (Fernet symmetric encryption).

## Features

✅ **Encrypted Password Storage** - Passwords are encrypted before saving
✅ **Multiple Saved Connections** - Save as many database connections as you need
✅ **Quick Connect** - Load saved connections with one click
✅ **Easy Management** - View, load, and delete saved connections
✅ **Machine-Specific Encryption** - Encryption key is unique to your machine

## How It Works

### 1. Encryption

- Uses `cryptography` library with Fernet encryption
- Generates a unique encryption key for your machine
- Key is stored in `.db_connections/.key` (read-only file)
- Passwords are encrypted before saving to disk
- Decrypted only when loading a connection

### 2. Storage

- Connections saved in `.db_connections/connections.json`
- Only encrypted passwords are stored
- File structure:
  ```
  .db_connections/
  ├── .key              # Encryption key (DO NOT SHARE)
  └── connections.json  # Encrypted connections
  ```

### 3. Security Best Practices

- ✅ Encryption key is machine-specific
- ✅ Key file has restricted permissions (600)
- ✅ Passwords never stored in plain text
- ✅ `.db_connections/` should be in `.gitignore`
- ⚠️ **NEVER** commit `.db_connections/` to version control

## Using Saved Connections

### Save a New Connection

1. Go to "Chat with Database" tab
2. Select database type (SQLite, PostgreSQL, MySQL)
3. Fill in connection details
4. ✅ Check "💾 Save this connection"
5. Enter a name (e.g., "Production DB", "Local Dev")
6. Click "Connect"
7. Connection is saved and you're connected!

### Load a Saved Connection

1. Go to "Chat with Database" tab
2. Look for "📌 Saved Connections" section
3. Select a connection from the dropdown
4. Credentials auto-fill in the form
5. Click "Connect"
6. You're connected!

### Delete a Saved Connection

1. Select the connection from the dropdown
2. Click the "🗑️ Delete" button
3. Confirm deletion
4. Connection is removed

## UI Features

### Connection Form

**For SQLite:**
- Database File Path
- Option to save connection

**For PostgreSQL/MySQL:**
- Host, Port, Username, Password, Database Name
- Option to save connection
- Connection name field (when saving)

### Saved Connections Section

Shows all saved connections with:
- Connection name
- Database type
- Host and database name
- Quick load and delete buttons

### Buttons

- **Connect** (Primary) - Connect to database
- **Clear** - Clear loaded connection and reset form
- **Delete** - Remove saved connection

## API Endpoints

### Save Connection
```
POST /api/v1/db/connections/save
Body: {
  "name": "My Connection",
  "db_type": "postgresql",
  "host": "localhost",
  "port": "5432",
  "username": "user",
  "password": "pass",
  "database": "mydb"
}
```

### List Connections
```
GET /api/v1/db/connections/list
Returns: [
  {
    "name": "My Connection",
    "type": "postgresql",
    "host": "localhost",
    "database": "mydb",
    "username": "user"
  }
]
```

### Load Connection
```
GET /api/v1/db/connections/{name}
Returns: {
  "type": "postgresql",
  "host": "localhost",
  "port": "5432",
  "username": "user",
  "password": "decrypted_password",
  "database": "mydb"
}
```

### Delete Connection
```
DELETE /api/v1/db/connections/{name}
Returns: {"message": "Connection deleted successfully"}
```

## Security Considerations

### What's Protected

✅ Passwords are encrypted at rest
✅ Encryption key is machine-specific
✅ Key file has restricted permissions
✅ No plain text passwords in storage

### What's NOT Protected

⚠️ Passwords are decrypted in memory when used
⚠️ Passwords sent over HTTP to backend (use HTTPS in production)
⚠️ If someone has access to your machine AND the key file, they can decrypt

### Recommendations

1. **Use HTTPS** in production environments
2. **Restrict file permissions** on `.db_connections/`
3. **Don't share** the `.key` file
4. **Add to .gitignore**:
   ```
   .db_connections/
   ```
5. **Use environment variables** for production credentials
6. **Rotate passwords** regularly
7. **Use database-specific security** (SSL/TLS connections)

## Installation

Install the required package:

```bash
pip install cryptography
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

## Troubleshooting

### "Failed to save connection"
- Check write permissions on `.db_connections/` directory
- Ensure disk space is available
- Check backend logs for errors

### "Connection not found"
- Verify the connection name is correct
- Check if `.db_connections/connections.json` exists
- Try listing all connections first

### "Failed to decrypt"
- Encryption key may have been corrupted
- Don't manually edit `.db_connections/.key`
- If key is lost, saved connections cannot be recovered

### Starting Fresh

To reset all saved connections:

```bash
# Backup first (optional)
cp -r .db_connections .db_connections.backup

# Remove saved connections
rm -rf .db_connections
```

Next connection save will create new encryption key.

## Example Workflow

### Development Setup

```python
# 1. Save local development database
Name: "Local Dev"
Type: PostgreSQL
Host: localhost
Port: 5432
Username: dev_user
Password: dev_pass
Database: dev_db

# 2. Save staging database
Name: "Staging"
Type: PostgreSQL
Host: staging.example.com
Port: 5432
Username: staging_user
Password: staging_pass
Database: staging_db

# 3. Quick switch between environments
- Select "Local Dev" → Connect
- Chat with local database
- Disconnect
- Select "Staging" → Connect
- Chat with staging database
```

## Best Practices

1. **Name connections clearly**: "Production DB", "Local Dev", "Testing"
2. **Save frequently used connections**: Saves time and reduces errors
3. **Delete unused connections**: Keep the list clean
4. **Test connections**: Verify they work after saving
5. **Document connection purposes**: Add notes about what each connection is for
6. **Use read-only users**: When possible, use database users with read-only permissions
7. **Regular audits**: Review saved connections periodically

## Migration from Old Setup

If you were manually entering credentials:

1. Enter credentials as usual
2. Check "Save this connection"
3. Give it a name
4. Click Connect
5. Next time, just load from saved connections!

## Support

For issues or questions:
- Check the error log: `errorlog.txt`
- Review backend logs
- Verify `.db_connections/` permissions
- Ensure `cryptography` package is installed
