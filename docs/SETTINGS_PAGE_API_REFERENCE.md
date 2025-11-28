# Settings Page API Reference

Quick reference for frontend developers building the Settings page.

## Authentication

All endpoints require Bearer token authentication:

```javascript
headers: {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json'
}
```

---

## Quota Status

### Get Quota Status
**Endpoint:** `GET /api/v1/quota/status`

**Purpose:** Display tenant's resource usage and limits

**Response:**
```typescript
interface QuotaStatus {
  storage: {
    limit_bytes: number;
    used_bytes: number;
    available_bytes: number;
    usage_percent: number;
  };
  queries: {
    daily_limit: number;
    daily_used: number;
    monthly_limit: number;
    monthly_used: number;
    daily_percent: number;
    monthly_percent: number;
  };
  documents: {
    limit: number;
    used: number;
    available: number;
    usage_percent: number;
  };
  connections: {
    max_connections: number;
    active_connections: number;
  };
  api_calls: {
    hourly_limit: number;
    hourly_used: number;
    minute_limit: number;
    minute_used: number;
  };
}
```

**Example Usage:**
```javascript
const response = await fetch('http://localhost:8000/api/v1/quota/status', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const quotaStatus = await response.json();

// Display storage usage
console.log(`Storage: ${quotaStatus.storage.used_bytes} / ${quotaStatus.storage.limit_bytes} bytes`);
console.log(`Usage: ${quotaStatus.storage.usage_percent.toFixed(1)}%`);
```

---

## API Keys Management

### List API Keys
**Endpoint:** `GET /api/v1/api-keys/`

**Purpose:** Get all API keys for the tenant

**Response:**
```typescript
interface APIKey {
  id: string;
  tenant_id: string;
  name: string;
  key_prefix: string;  // e.g., "sk_live_abc...xyz"
  permissions: string[];
  last_used_at: string | null;
  usage_count: number;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
  updated_at: string | null;
}

type APIKeyList = APIKey[];
```

**Example Usage:**
```javascript
const response = await fetch('http://localhost:8000/api/v1/api-keys/', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const apiKeys = await response.json();

// Display keys in a table
apiKeys.forEach(key => {
  console.log(`${key.name}: ${key.key_prefix} (${key.is_active ? 'Active' : 'Inactive'})`);
});
```

---

### Create API Key
**Endpoint:** `POST /api/v1/api-keys/`

**Purpose:** Generate a new API key

**Request Body:**
```typescript
interface CreateAPIKeyRequest {
  name: string;                    // Required: Friendly name
  expires_in_days?: number;        // Optional: 1-365 days
  permissions?: string[];          // Optional: ["read", "write"]
}
```

**Response:**
```typescript
interface CreateAPIKeyResponse {
  id: string;
  api_key: string;                 // ⚠️ ONLY SHOWN ONCE!
  key_prefix: string;
  name: string;
  tenant_id: string;
  permissions: string[];
  expires_at: string | null;
  created_at: string;
  message: string;
}
```

**Example Usage:**
```javascript
const response = await fetch('http://localhost:8000/api/v1/api-keys/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'Production API Key',
    expires_in_days: 90,
    permissions: ['read', 'write']
  })
});

const newKey = await response.json();

// ⚠️ IMPORTANT: Display the full API key to user NOW
// It will never be shown again!
alert(`Save this key: ${newKey.api_key}`);
console.log(newKey.message);
```

---

### Revoke API Key
**Endpoint:** `DELETE /api/v1/api-keys/{key_id}`

**Purpose:** Deactivate an API key (cannot be undone)

**Response:**
```typescript
interface RevokeAPIKeyResponse {
  message: string;
  key_id: string;
}
```

**Example Usage:**
```javascript
const keyId = '550e8400-e29b-41d4-a716-446655440000';

const response = await fetch(`http://localhost:8000/api/v1/api-keys/${keyId}`, {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const result = await response.json();
console.log(result.message);  // "API key ... revoked successfully"
```

---

## Error Handling

All endpoints return standard error responses:

```typescript
interface ErrorResponse {
  detail: string;
}
```

**Common Status Codes:**
- `200` - Success
- `201` - Created (for POST requests)
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (tenant inactive or no permission)
- `404` - Not Found (resource doesn't exist)
- `500` - Internal Server Error

**Example Error Handling:**
```javascript
try {
  const response = await fetch(url, options);
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Request failed');
  }
  
  return await response.json();
} catch (error) {
  console.error('API Error:', error.message);
  // Show error to user
}
```

---

## UI Components Suggestions

### Quota Display Cards

```jsx
function QuotaCard({ title, used, limit, percent }) {
  return (
    <div className="quota-card">
      <h3>{title}</h3>
      <div className="progress-bar">
        <div style={{ width: `${percent}%` }} />
      </div>
      <p>{used} / {limit} ({percent.toFixed(1)}%)</p>
    </div>
  );
}

// Usage
<QuotaCard 
  title="Storage"
  used={formatBytes(quotaStatus.storage.used_bytes)}
  limit={formatBytes(quotaStatus.storage.limit_bytes)}
  percent={quotaStatus.storage.usage_percent}
/>
```

### API Keys Table

```jsx
function APIKeysTable({ keys, onRevoke }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Key Prefix</th>
          <th>Status</th>
          <th>Last Used</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {keys.map(key => (
          <tr key={key.id}>
            <td>{key.name}</td>
            <td><code>{key.key_prefix}</code></td>
            <td>{key.is_active ? '✓ Active' : '✗ Inactive'}</td>
            <td>{key.last_used_at ? formatDate(key.last_used_at) : 'Never'}</td>
            <td>
              <button onClick={() => onRevoke(key.id)}>Revoke</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

### Create API Key Modal

```jsx
function CreateAPIKeyModal({ onClose, onSuccess }) {
  const [name, setName] = useState('');
  const [expiresInDays, setExpiresInDays] = useState(90);
  const [newKey, setNewKey] = useState(null);
  
  const handleCreate = async () => {
    const response = await fetch('/api/v1/api-keys/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ name, expires_in_days: expiresInDays })
    });
    
    const result = await response.json();
    setNewKey(result);
  };
  
  if (newKey) {
    return (
      <div className="modal">
        <h2>⚠️ Save Your API Key</h2>
        <p>{newKey.message}</p>
        <code className="api-key">{newKey.api_key}</code>
        <button onClick={() => navigator.clipboard.writeText(newKey.api_key)}>
          Copy to Clipboard
        </button>
        <button onClick={() => { onSuccess(); onClose(); }}>
          Done
        </button>
      </div>
    );
  }
  
  return (
    <div className="modal">
      <h2>Create API Key</h2>
      <input 
        placeholder="Key Name"
        value={name}
        onChange={e => setName(e.target.value)}
      />
      <select value={expiresInDays} onChange={e => setExpiresInDays(e.target.value)}>
        <option value={30}>30 days</option>
        <option value={60}>60 days</option>
        <option value={90}>90 days</option>
        <option value={365}>1 year</option>
      </select>
      <button onClick={handleCreate}>Create</button>
      <button onClick={onClose}>Cancel</button>
    </div>
  );
}
```

---

## Helper Functions

```javascript
// Format bytes to human-readable
function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Format date
function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

// Calculate days until expiration
function daysUntilExpiration(expiresAt) {
  if (!expiresAt) return null;
  const now = new Date();
  const expiry = new Date(expiresAt);
  const days = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
  return days;
}
```

---

## Testing

Test the endpoints using the provided test script:

```bash
python test_quota_api_keys.py
```

Or test manually with curl:

```bash
# Get quota status
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/quota/status

# List API keys
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/api-keys/

# Create API key
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Key","expires_in_days":30}' \
  http://localhost:8000/api/v1/api-keys/

# Revoke API key
curl -X DELETE \
  -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/api-keys/KEY_ID
```

---

## Notes

1. **API Key Security**: The full API key is only returned once during creation. Make sure to display it prominently to the user with a warning to save it.

2. **Quota Limits**: Values of `-1` indicate unlimited quota. Handle this in the UI (e.g., show "Unlimited" instead of a percentage).

3. **Refresh Data**: After creating or revoking keys, refresh the list to show updated data.

4. **Error Messages**: Display user-friendly error messages from the `detail` field in error responses.

5. **Loading States**: Show loading indicators while fetching data or performing actions.
