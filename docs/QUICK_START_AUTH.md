# Quick Start - Authentication

## 🚀 Get Started in 5 Minutes

### Step 1: Start the Server
```bash
uvicorn app.main:app --reload
```

### Step 2: Register a Tenant
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/tenants/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Company",
    "email": "admin@mycompany.com",
    "password": "MySecurePassword123!",
    "billing_tier": "free"
  }'
```

### Step 3: Login
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@mycompany.com",
    "password": "MySecurePassword123!"
  }'
```

**Save the access_token from the response!**

### Step 4: Use the API
```bash
# Replace YOUR_TOKEN with the access_token from step 3
curl -X GET "http://127.0.0.1:8000/api/v1/tenants/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## ✅ That's it! You're authenticated!

---

## Test Script

Run the automated test:
```bash
python test_auth_flow.py
```

This will test all authentication flows automatically.

---

## Frontend Integration

### React Example

```javascript
// Register
const register = async (name, email, password) => {
  const response = await fetch('http://127.0.0.1:8000/api/v1/tenants/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password, billing_tier: 'free' })
  });
  return response.json();
};

// Login
const login = async (email, password) => {
  const response = await fetch('http://127.0.0.1:8000/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  const data = await response.json();
  // Store token
  localStorage.setItem('access_token', data.access_token);
  return data;
};

// Use API
const getTenant = async () => {
  const token = localStorage.getItem('access_token');
  const response = await fetch('http://127.0.0.1:8000/api/v1/tenants/me', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};
```

---

## Common Endpoints

| What | Method | Endpoint |
|------|--------|----------|
| Register | POST | `/api/v1/tenants/register` |
| Login | POST | `/api/v1/auth/login` |
| Refresh Token | POST | `/api/v1/auth/refresh` |
| Verify Token | GET | `/api/v1/auth/verify` |
| Get Profile | GET | `/api/v1/tenants/me` |
| Upload File | POST | `/api/v1/upload/` |
| Query KB | POST | `/api/v1/query/` |
| List KBs | GET | `/api/v1/manage/knowledge-bases/` |

All endpoints except register and login require:
```
Authorization: Bearer <your_access_token>
```

---

## Need Help?

- 📖 Full API Docs: http://127.0.0.1:8000/docs
- 📋 Detailed Auth Guide: `docs/AUTH_WORKING_STATUS.md`
- 🔐 Authentication Status: `docs/AUTHENTICATION_STATUS.md`
- 📚 Complete API Docs: `docs/API_DOCUMENTATION.md`
