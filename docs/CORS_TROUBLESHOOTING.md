# CORS Troubleshooting Guide

## Good News! 🎉

Looking at your error logs, **CORS is actually working!** 

The error progression shows:
1. ❌ First: CORS error (No 'Access-Control-Allow-Origin' header)
2. ✅ Then: 422 Unprocessable Entity

The 422 error means the request **got through** CORS and reached the server, but there's a **validation error** with the request data.

## The Real Issue: 422 Unprocessable Entity

This means your request format doesn't match what the API expects.

### Check Your Request Format

The registration endpoint expects:
```json
{
  "name": "Company Name",
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "phone": "+1-555-0123",  // Optional
  "billing_tier": "free"    // Optional, defaults to "free"
}
```

### Common Issues:

#### 1. Missing Required Fields
Make sure you're sending `name`, `email`, and `password`:
```javascript
// ❌ Wrong
{
  username: "test",  // Should be "name"
  email: "test@example.com"
  // Missing password!
}

// ✅ Correct
{
  name: "Test Company",
  email: "test@example.com",
  password: "SecurePassword123!"
}
```

#### 2. Wrong Field Names
```javascript
// ❌ Wrong
{
  company_name: "Test",  // Should be "name"
  user_email: "test@example.com",  // Should be "email"
  pass: "password123"  // Should be "password"
}

// ✅ Correct
{
  name: "Test Company",
  email: "test@example.com",
  password: "SecurePassword123!"
}
```

#### 3. Invalid Email Format
```javascript
// ❌ Wrong
{
  name: "Test",
  email: "notanemail",  // Invalid email
  password: "pass123"
}

// ✅ Correct
{
  name: "Test",
  email: "test@example.com",  // Valid email
  password: "pass123"
}
```

## Restart Server

After updating CORS configuration:
```bash
# Stop server (Ctrl+C)
# Restart:
uvicorn app.main:app --reload --port 8000
```

## Test with cURL

Test the exact request format:
```bash
curl -X POST "http://localhost:8000/api/v1/tenants/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Company",
    "email": "test@example.com",
    "password": "SecurePassword123!",
    "billing_tier": "free"
  }'
```

## Check Your Frontend Code

### Example Correct Implementation:

```javascript
// api.ts or similar
export const register = async (name: string, email: string, password: string) => {
  const response = await fetch('http://localhost:8000/api/v1/tenants/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name,           // ✅ Correct field name
      email,          // ✅ Correct field name
      password,       // ✅ Correct field name
      billing_tier: 'free'  // ✅ Optional but good to include
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    console.error('Registration error:', error);  // Log the actual error
    throw new Error(JSON.stringify(error));
  }

  return response.json();
};
```

## Debug the Actual Error

Update your error handling to see the actual validation error:

```javascript
// In your catch block
catch (error) {
  if (error.response) {
    // The request was made and the server responded with an error
    console.error('Server error:', error.response.data);
    console.error('Status:', error.response.status);
  } else if (error.request) {
    // The request was made but no response was received
    console.error('No response:', error.request);
  } else {
    // Something else happened
    console.error('Error:', error.message);
  }
}
```

## Check Server Logs

Look at your FastAPI server console output. It will show the validation error details:

```
INFO:     127.0.0.1:xxxxx - "POST /api/v1/tenants/register HTTP/1.1" 422 Unprocessable Entity
```

The server logs will tell you exactly which field is missing or invalid.

## Verify CORS is Working

Open browser DevTools → Network tab → Look for the OPTIONS request (preflight):
- Should return 200 OK
- Should have `Access-Control-Allow-Origin` header

Then look at the POST request:
- Should have `Access-Control-Allow-Origin` header
- If you see 422, CORS is working! Fix the request data.

## Common Frontend Mistakes

### 1. Using FormData instead of JSON
```javascript
// ❌ Wrong for this API
const formData = new FormData();
formData.append('name', name);
// ...

// ✅ Correct
const body = JSON.stringify({ name, email, password });
```

### 2. Not Setting Content-Type
```javascript
// ❌ Wrong
fetch(url, {
  method: 'POST',
  body: JSON.stringify(data)
  // Missing Content-Type header!
})

// ✅ Correct
fetch(url, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'  // ✅ Required!
  },
  body: JSON.stringify(data)
})
```

### 3. Sending Extra Fields
```javascript
// ❌ Might cause issues
{
  name: "Test",
  email: "test@example.com",
  password: "pass123",
  confirmPassword: "pass123",  // Extra field not in schema
  agreeToTerms: true  // Extra field not in schema
}

// ✅ Only send what the API expects
{
  name: "Test",
  email: "test@example.com",
  password: "pass123"
}
```

## Still Having Issues?

1. **Check the exact error message** in the server logs
2. **Use browser DevTools** Network tab to see the actual request/response
3. **Test with cURL** to verify the API works
4. **Compare your request** with the working cURL example

## Summary

✅ **CORS is working** - The 422 error proves the request reached the server
❌ **Request validation failed** - Check your request data format

Fix the request data format and it should work!

---

**Last Updated:** November 20, 2024
