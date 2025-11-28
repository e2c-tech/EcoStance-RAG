# API Key Quick Start Guide

**For Developers:** Get started with API keys in 5 minutes

---

## What Are API Keys?

API keys let you access the API programmatically without logging in each time. Think of them as long-lived passwords for your applications.

**Format:** `sk_live_abc123...` (32 characters)

---

## Quick Start

### 1. Create an API Key

```bash
# Login first to get JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}'

# Response: {"access_token": "eyJ...", ...}

# Create API key
curl -X POST http://localhost:8000/api/v1/api-keys/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My First API Key"}'
```

**Response:**
```json
{
  "id": "key-uuid",
  "api_key": "sk_live_abc123...",  // ⚠️ SAVE THIS! Won't be shown again
  "key_prefix": "sk_live_abc...xyz",
  "name": "My First API Key",
  "message": "Save this API key securely. It will not be shown again."
}
```

**⚠️ IMPORTANT:** Copy the `api_key` value immediately. You won't see it again!

### 2. Use Your API Key

**Method 1: Bearer Token (Recommended)**
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer sk_live_abc123..." \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG?", "kb_id": "kb-123"}'
```

**Method 2: X-API-Key Header**
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "X-API-Key: sk_live_abc123..." \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG?", "kb_id": "kb-123"}'
```

### 3. Python Example

```python
import requests

# Your API key
API_KEY = "sk_live_abc123..."
BASE_URL = "http://localhost:8000"

# Make a request
response = requests.post(
    f"{BASE_URL}/api/v1/query",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "query": "What is RAG?",
        "kb_id": "kb-123"
    }
)

print(response.json())
```

### 4. JavaScript Example

```javascript
const API_KEY = "sk_live_abc123...";
const BASE_URL = "http://localhost:8000";

// Make a request
fetch(`${BASE_URL}/api/v1/query`, {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${API_KEY}`,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    query: "What is RAG?",
    kb_id: "kb-123"
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

---

## Managing API Keys

### List Your Keys

```bash
curl -X GET http://localhost:8000/api/v1/api-keys/ \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Response:**
```json
[
  {
    "id": "key-uuid",
    "name": "My First API Key",
    "key_prefix": "sk_live_abc...xyz",  // Only prefix shown
    "is_active": true,
    "usage_count": 1523,
    "last_used_at": "2025-11-17T12:30:00",
    "created_at": "2025-11-17T10:00:00"
  }
]
```

### Revoke a Key

```bash
curl -X DELETE http://localhost:8000/api/v1/api-keys/KEY_ID \
  -H "Authorization: Bearer YOUR_API_KEY"
```

The key stops working immediately.

### Rotate a Key

```bash
curl -X POST http://localhost:8000/api/v1/api-keys/KEY_ID/rotate \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"new_key_name": "Rotated Key"}'
```

This creates a new key and revokes the old one.

---

## Advanced Features

### Create Key with Expiration

```bash
curl -X POST http://localhost:8000/api/v1/api-keys/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Temporary Key",
    "expires_in_days": 30
  }'
```

The key will automatically stop working after 30 days.

### View Usage Statistics

```bash
# Overall stats (last 7 days)
curl -X GET http://localhost:8000/api/v1/usage/stats?days=7 \
  -H "Authorization: Bearer YOUR_API_KEY"

# Specific endpoint stats
curl -X GET http://localhost:8000/api/v1/usage/endpoint/api/v1/query?days=7 \
  -H "Authorization: Bearer YOUR_API_KEY"

# Export usage data
curl -X GET http://localhost:8000/api/v1/usage/export?days=30 \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Best Practices

### Security

✅ **DO:**
- Store API keys in environment variables
- Use different keys for dev/staging/production
- Rotate keys regularly (every 90 days)
- Revoke keys immediately if compromised
- Use HTTPS in production

❌ **DON'T:**
- Commit API keys to git
- Share keys between applications
- Use keys in client-side code (browsers)
- Store keys in plain text files

### Example: Environment Variables

```bash
# .env file (add to .gitignore!)
API_KEY=sk_live_abc123...
```

```python
# Python
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
```

```javascript
// Node.js
require('dotenv').config();
const API_KEY = process.env.API_KEY;
```

### Rate Limits

- Same rate limits as JWT authentication
- Shared across all your API keys
- Check response headers for limits:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`

### Limits

- Maximum 10 API keys per tenant
- Keys can be revoked and recreated
- No limit on requests per key

---

## Troubleshooting

### "Invalid API key" Error

**Causes:**
- Key was revoked
- Key has expired
- Typo in the key
- Key belongs to different tenant

**Solution:**
- Check if key is active: `GET /api/v1/api-keys/`
- Create a new key if needed

### "Maximum API keys limit reached"

**Cause:** You have 10 active keys (the maximum)

**Solution:**
- Revoke unused keys: `DELETE /api/v1/api-keys/{key_id}`
- Then create a new key

### Key Not Working After Creation

**Cause:** You might be using the wrong key

**Solution:**
- Make sure you copied the full key from the creation response
- The key starts with `sk_live_`
- It's 32 characters long

---

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/api-keys/` | Create new API key |
| GET | `/api/v1/api-keys/` | List all keys |
| DELETE | `/api/v1/api-keys/{key_id}` | Revoke key |
| POST | `/api/v1/api-keys/{key_id}/rotate` | Rotate key |
| GET | `/api/v1/usage/stats` | Usage statistics |
| GET | `/api/v1/usage/endpoint/{path}` | Endpoint stats |
| GET | `/api/v1/usage/export` | Export usage data |

### Full Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Detailed Guide:** `docs/PHASE_3_3_API_SECURITY.md`

---

## Support

**Questions?** Check the full documentation:
- `docs/PHASE_3_3_API_SECURITY.md` - Complete guide
- `docs/PHASE_3_3_SUMMARY.md` - Implementation summary
- http://localhost:8000/docs - Interactive API docs

**Issues?** Common problems:
1. Key not working → Check if active and not expired
2. Rate limited → Wait for rate limit reset
3. Max keys reached → Revoke unused keys first

---

## Summary

1. **Create key:** `POST /api/v1/api-keys/` (save the key!)
2. **Use key:** `Authorization: Bearer sk_live_...`
3. **Manage keys:** List, revoke, rotate as needed
4. **Monitor usage:** Check stats with `/api/v1/usage/stats`

That's it! You're ready to use API keys. 🚀
