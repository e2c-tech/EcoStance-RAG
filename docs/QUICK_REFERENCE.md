# Chat with Database - Quick Reference

## Installation

```bash
pip install -r requirements.txt
```

## Start Application

```bash
# Terminal 1 - Backend
python run_app.py

# Terminal 2 - UI
streamlit run ui/app.py
```

## Save Connection (First Time)

1. Select database type
2. Fill credentials
3. ✅ Check "Save this connection"
4. Name it (e.g., "My DB")
5. Click "Connect"

## Load Connection (Next Time)

1. Select from dropdown
2. Click "Connect"
3. Done!

## Ask Questions

```
"Show me all customers"
"What are the top 10 products?"
"How many orders today?"
"List users from California"
```

## Files Created

```
.db_connections/
├── .key              # Encryption key (SECRET!)
└── connections.json  # Encrypted connections
```

## Security

✅ Passwords encrypted
✅ Machine-specific key
✅ Auto-ignored by git
✅ Only SELECT queries run

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Fields don't appear | Refresh page |
| Connection fails | Check credentials |
| Can't save | Install `cryptography` |
| No saved connections | Save one first |

## Documentation

- Setup: `SETUP_SECURE_CONNECTIONS.md`
- Security: `SECURE_CONNECTIONS_GUIDE.md`
- UI Guide: `UI_DATABASE_CHAT_GUIDE.md`
- Complete: `CHAT_WITH_DB_COMPLETE_SUMMARY.md`

## Support

Check: `errorlog.txt` and backend logs
