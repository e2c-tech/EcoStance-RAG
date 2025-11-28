# CORS Configuration Guide

## ✅ CORS is Now Enabled!

CORS (Cross-Origin Resource Sharing) has been configured to allow your frontend applications to communicate with the API.

## Allowed Origins

The following origins are pre-configured:

### Development
- `http://localhost:3000` - React (Create React App)
- `http://localhost:3001` - React (alternative port)
- `http://localhost:5173` - Vite (React/Vue)
- `http://localhost:8501` - Streamlit
- `http://127.0.0.1:3000` - React (IP address)
- `http://127.0.0.1:3001` - React (alternative port)
- `http://127.0.0.1:5173` - Vite
- `http://127.0.0.1:8501` - Streamlit

### Production
To add production domains, edit `app/main.py` and add your domains to the `allow_origins` list:

```python
allow_origins=[
    # ... existing origins ...
    "https://yourdomain.com",
    "https://www.yourdomain.com",
    "https://app.yourdomain.com",
]
```

## CORS Settings

### Current Configuration:
- ✅ **Credentials**: Enabled (allows cookies and authentication headers)
- ✅ **Methods**: All methods allowed (GET, POST, PUT, DELETE, PATCH, OPTIONS)
- ✅ **Headers**: All headers allowed (including Authorization, Content-Type, etc.)
- ✅ **Exposed Headers**: All headers exposed to client

## Testing CORS

### From Browser Console:
```javascript
fetch('http://127.0.0.1:8000/health')
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));
```

### From React:
```javascript
// Login example
const login = async (email, password) => {
  const response = await fetch('http://127.0.0.1:8000/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });
  
  if (!response.ok) {
    throw new Error('Login failed');
  }
  
  return response.json();
};
```

### With Credentials (Cookies):
```javascript
fetch('http://127.0.0.1:8000/api/v1/tenants/me', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
  },
  credentials: 'include', // Important for cookies
})
```

## Common CORS Issues

### Issue: "No 'Access-Control-Allow-Origin' header"
**Solution**: Make sure your frontend URL is in the `allow_origins` list.

### Issue: "Credentials flag is true, but Access-Control-Allow-Credentials is not"
**Solution**: Already fixed - `allow_credentials=True` is set.

### Issue: "Method not allowed"
**Solution**: Already fixed - all methods are allowed.

### Issue: "Header not allowed"
**Solution**: Already fixed - all headers are allowed.

## Security Considerations

### Development vs Production

**Development (Current):**
- Allows multiple localhost origins
- Allows all methods and headers
- Good for testing

**Production (Recommended):**
```python
# In production, be more restrictive:
allow_origins=[
    "https://yourdomain.com",  # Only your actual domain
],
allow_methods=["GET", "POST", "PUT", "DELETE"],  # Specific methods
allow_headers=["Authorization", "Content-Type"],  # Specific headers
```

### Environment-Based Configuration

For better security, use environment variables:

```python
import os

# In app/main.py
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # ... rest of config
)
```

Then in `.env`:
```bash
# Development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Production
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

## Restart Server

After making changes to CORS configuration, restart the server:

```bash
# Stop the server (Ctrl+C)
# Then restart:
uvicorn app.main:app --reload --port 8000
```

## Verify CORS is Working

### 1. Check Response Headers
Open browser DevTools → Network tab → Make a request → Check response headers:
- `Access-Control-Allow-Origin: http://localhost:3000`
- `Access-Control-Allow-Credentials: true`
- `Access-Control-Allow-Methods: *`
- `Access-Control-Allow-Headers: *`

### 2. Test from Frontend
```javascript
// Should work without CORS errors
fetch('http://127.0.0.1:8000/api/v1/tenants/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'Test Company',
    email: 'test@example.com',
    password: 'SecurePassword123!',
    billing_tier: 'free'
  })
})
.then(res => res.json())
.then(data => console.log('Success:', data))
.catch(err => console.error('Error:', err));
```

## CORS is Ready! 🎉

Your API now accepts requests from frontend applications without CORS errors!

---

**Last Updated:** November 20, 2024
**Status:** ✅ CORS Enabled and Configured
