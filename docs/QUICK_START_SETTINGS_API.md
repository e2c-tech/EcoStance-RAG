# Quick Start: Settings Page API

## 🚀 Get Started in 5 Minutes

### Step 1: Start the Server
```bash
python run_app.py
```

Server runs at: `http://localhost:8000`

---

### Step 2: Get an Auth Token

**Register a new account:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "company_name": "Test Company"
  }'
```

**Or login:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!"
  }'
```

**Save the token:**
```bash
export TOKEN="your_access_token_here"
```

---

### Step 3: Test Quota Status

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/quota/status
```

**Expected Response:**
```json
{
  "storage": {
    "limit_bytes": 1073741824,
    "used_bytes": 0,
    "available_bytes": 1073741824,
    "usage_percent": 0.0
  },
  "queries": {
    "daily_limit": 100,
    "daily_used": 0,
    "monthly_limit": 3000,
    "monthly_used": 0,
    "daily_percent": 0.0,
    "monthly_percent": 0.0
  },
  "documents": {
    "limit": 1000,
    "used": 0,
    "available": 1000,
    "usage_percent": 0.0
  },
  "connections": {
    "max_connections": 2,
    "active_connections": 0
  },
  "api_calls": {
    "hourly_limit": 600,
    "hourly_used": 0,
    "minute_limit": 10,
    "minute_used": 0
  }
}
```

---

### Step 4: Test API Keys

**List existing keys:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/api-keys/
```

**Create a new key:**
```bash
curl -X POST http://localhost:8000/api/v1/api-keys/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Test Key",
    "expires_in_days": 30,
    "permissions": ["read", "write"]
  }'
```

**⚠️ IMPORTANT:** Save the `api_key` from the response - it's only shown once!

**Revoke a key:**
```bash
curl -X DELETE http://localhost:8000/api/v1/api-keys/KEY_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

### Step 5: Run Automated Tests

```bash
python test_quota_api_keys.py
```

This will test all endpoints automatically.

---

## Frontend Integration (JavaScript/React)

### Setup
```javascript
const API_BASE = 'http://localhost:8000';
const token = localStorage.getItem('access_token');

const headers = {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
};
```

### Get Quota Status
```javascript
async function getQuotaStatus() {
  const response = await fetch(`${API_BASE}/api/v1/quota/status`, {
    headers
  });
  return await response.json();
}

// Usage
const quota = await getQuotaStatus();
console.log(`Storage: ${quota.storage.usage_percent}%`);
```

### List API Keys
```javascript
async function listAPIKeys() {
  const response = await fetch(`${API_BASE}/api/v1/api-keys/`, {
    headers
  });
  return await response.json();
}

// Usage
const keys = await listAPIKeys();
keys.forEach(key => {
  console.log(`${key.name}: ${key.key_prefix}`);
});
```

### Create API Key
```javascript
async function createAPIKey(name, expiresInDays = 90) {
  const response = await fetch(`${API_BASE}/api/v1/api-keys/`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      name,
      expires_in_days: expiresInDays,
      permissions: ['read', 'write']
    })
  });
  return await response.json();
}

// Usage
const newKey = await createAPIKey('Production Key', 90);
alert(`Save this key: ${newKey.api_key}`);
```

### Revoke API Key
```javascript
async function revokeAPIKey(keyId) {
  const response = await fetch(`${API_BASE}/api/v1/api-keys/${keyId}`, {
    method: 'DELETE',
    headers
  });
  return await response.json();
}

// Usage
await revokeAPIKey('550e8400-e29b-41d4-a716-446655440000');
console.log('Key revoked');
```

---

## React Component Example

```jsx
import { useState, useEffect } from 'react';

function SettingsPage() {
  const [quota, setQuota] = useState(null);
  const [apiKeys, setApiKeys] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [quotaData, keysData] = await Promise.all([
        getQuotaStatus(),
        listAPIKeys()
      ]);
      setQuota(quotaData);
      setApiKeys(keysData);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div>Loading...</div>;

  return (
    <div className="settings-page">
      <h1>Settings</h1>
      
      {/* Quota Section */}
      <section>
        <h2>Resource Usage</h2>
        <div className="quota-cards">
          <QuotaCard
            title="Storage"
            used={quota.storage.used_bytes}
            limit={quota.storage.limit_bytes}
            percent={quota.storage.usage_percent}
          />
          <QuotaCard
            title="Daily Queries"
            used={quota.queries.daily_used}
            limit={quota.queries.daily_limit}
            percent={quota.queries.daily_percent}
          />
          <QuotaCard
            title="Documents"
            used={quota.documents.used}
            limit={quota.documents.limit}
            percent={quota.documents.usage_percent}
          />
        </div>
      </section>

      {/* API Keys Section */}
      <section>
        <h2>API Keys</h2>
        <button onClick={handleCreateKey}>Create New Key</button>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Key</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {apiKeys.map(key => (
              <tr key={key.id}>
                <td>{key.name}</td>
                <td><code>{key.key_prefix}</code></td>
                <td>{key.is_active ? '✓' : '✗'}</td>
                <td>
                  <button onClick={() => handleRevoke(key.id)}>
                    Revoke
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
```

---

## Troubleshooting

### Error: 401 Unauthorized
- Check that your token is valid
- Token might be expired - login again
- Make sure Authorization header is set correctly

### Error: 500 Internal Server Error
- Check server logs: `tail -f errorlog.txt`
- Verify database is initialized
- Ensure all migrations are applied

### No data returned
- Check that tenant exists and is active
- Verify token contains valid tenant_id
- Check database has quota records

---

## API Documentation

Full documentation: `docs/SETTINGS_PAGE_API_REFERENCE.md`

---

## What's Next?

1. ✅ Backend is ready
2. Build Settings page UI
3. Add quota visualization (charts/progress bars)
4. Implement API key management interface
5. Add confirmation dialogs for destructive actions
6. Test end-to-end

---

## Need Help?

- **Bug Fix Details**: `QUOTA_API_KEYS_FIX.md`
- **Full API Reference**: `docs/SETTINGS_PAGE_API_REFERENCE.md`
- **Test Script**: `python test_quota_api_keys.py`
- **API Docs**: http://localhost:8000/docs (when server is running)

---

**Ready to build!** 🎉
