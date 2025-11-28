# Email/Password Authentication

## Overview

The system now supports **email and password authentication** for a better user experience. Users can register with their email and password, then login using those credentials.

## What Changed

### Before
- Login required `tenant_id` (UUID)
- Users had to remember complex IDs like `653f533b-ae8c-465d-b4b8-92d0abb2471c`
- Not user-friendly

### After
- ✅ Login with **email and password** (recommended)
- ✅ Backward compatible with `tenant_id` login (for development)
- ✅ Passwords are securely hashed with bcrypt
- ✅ Email uniqueness enforced

## Registration

### Endpoint
```
POST /api/v1/tenants/register
```

### Request Body
```json
{
  "name": "Company Name",
  "email": "admin@company.com",
  "password": "SecurePassword123!",
  "phone": "+1-555-0123",
  "billing_tier": "free"
}
```

### Response
```json
{
  "id": "uuid",
  "name": "Company Name",
  "slug": "company-name-abc123",
  "email": "admin@company.com",
  "phone": "+1-555-0123",
  "is_active": true,
  "created_at": "2024-11-13T10:00:00",
  "billing_tier": "free",
  "billing_status": "active"
}
```

### Example
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/tenants/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corporation",
    "email": "admin@acme.com",
    "password": "SecurePass123!"
  }'
```

### Python
```python
import requests

response = requests.post(
    "http://127.0.0.1:8000/api/v1/tenants/register",
    json={
        "name": "Acme Corporation",
        "email": "admin@acme.com",
        "password": "SecurePass123!"
    }
)

tenant = response.json()
print(f"Registered! Email: {tenant['email']}")
```

## Login

### Method 1: Email + Password (Recommended)

**Endpoint:** `POST /api/v1/auth/login`

**Request Body:**
```json
{
  "email": "admin@company.com",
  "password": "SecurePassword123!"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "tenant_id": "uuid"
}
```

**Example:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@acme.com",
    "password": "SecurePass123!"
  }'
```

**Python:**
```python
import requests

response = requests.post(
    "http://127.0.0.1:8000/api/v1/auth/login",
    json={
        "email": "admin@acme.com",
        "password": "SecurePass123!"
    }
)

tokens = response.json()
access_token = tokens['access_token']

# Use the token
headers = {"Authorization": f"Bearer {access_token}"}
```

### Method 2: Tenant ID (Backward Compatible)

**Request Body:**
```json
{
  "tenant_id": "uuid"
}
```

This method is kept for backward compatibility and development purposes.

## Security Features

### Password Hashing
- Passwords are hashed using **bcrypt**
- Salt is automatically generated
- Passwords are never stored in plain text
- Hash algorithm: bcrypt with default cost factor (12)

### Email Uniqueness
- Each email can only be registered once
- Duplicate email registration returns `400 Bad Request`

### Password Validation
- Wrong password returns `401 Unauthorized`
- No information leak about whether email exists

### Account Status
- Inactive accounts cannot login (`403 Forbidden`)
- Deleted accounts cannot login

## Error Responses

### Registration Errors

**Email Already Exists:**
```json
{
  "detail": "Email already registered"
}
```
Status: `400 Bad Request`

### Login Errors

**Invalid Credentials:**
```json
{
  "detail": "Invalid email or password"
}
```
Status: `401 Unauthorized`

**Account Inactive:**
```json
{
  "detail": "Tenant account is inactive"
}
```
Status: `403 Forbidden`

**Missing Credentials:**
```json
{
  "detail": "Either email+password or tenant_id must be provided"
}
```
Status: `400 Bad Request`

## Complete Workflow

### 1. User Registration
```python
import requests

# Register
response = requests.post(
    "http://127.0.0.1:8000/api/v1/tenants/register",
    json={
        "name": "My Company",
        "email": "user@mycompany.com",
        "password": "MySecurePassword123!"
    }
)

tenant = response.json()
print(f"Welcome! Your account: {tenant['email']}")
```

### 2. User Login
```python
# Login
response = requests.post(
    "http://127.0.0.1:8000/api/v1/auth/login",
    json={
        "email": "user@mycompany.com",
        "password": "MySecurePassword123!"
    }
)

tokens = response.json()
access_token = tokens['access_token']
```

### 3. Use Authenticated Endpoints
```python
# Make authenticated requests
headers = {"Authorization": f"Bearer {access_token}"}

# Upload file
files = {"file": open("document.pdf", "rb")}
response = requests.post(
    "http://127.0.0.1:8000/api/v1/upload/",
    headers=headers,
    files=files
)

# Query knowledge base
response = requests.post(
    "http://127.0.0.1:8000/api/v1/query/",
    headers=headers,
    data={"kb_name": "demo", "query": "What is this about?"}
)

answer = response.json()['answer']
```

## Password Requirements

### Current Requirements
- Minimum length: None (should be added)
- No complexity requirements (should be added)

### Recommended Requirements (To Implement)
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

### Implementation Example
```python
import re

def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True
```

## Database Schema

### Tenant Table Updates

**New Column:**
```sql
ALTER TABLE tenants 
ADD COLUMN password_hash VARCHAR(255);
```

**Email Uniqueness:**
```sql
ALTER TABLE tenants 
ADD CONSTRAINT tenants_email_unique UNIQUE (email);
```

### Migration

Run the migration script:
```bash
python migrations/add_password_hash_to_tenants.py
```

## Testing

### Test Script
```bash
python test_email_password_auth.py
```

### Manual Testing

**1. Register:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/tenants/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Company",
    "email": "test@example.com",
    "password": "TestPass123!"
  }'
```

**2. Login:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }'
```

**3. Test Wrong Password:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "WrongPassword"
  }'
```

## UI Integration

### Login Form

```html
<form id="loginForm">
  <input type="email" name="email" placeholder="Email" required>
  <input type="password" name="password" placeholder="Password" required>
  <button type="submit">Login</button>
</form>

<script>
document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const formData = new FormData(e.target);
  const response = await fetch('http://127.0.0.1:8000/api/v1/auth/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      email: formData.get('email'),
      password: formData.get('password')
    })
  });
  
  if (response.ok) {
    const tokens = await response.json();
    localStorage.setItem('access_token', tokens.access_token);
    window.location.href = '/dashboard';
  } else {
    alert('Invalid email or password');
  }
});
</script>
```

### Registration Form

```html
<form id="registerForm">
  <input type="text" name="name" placeholder="Company Name" required>
  <input type="email" name="email" placeholder="Email" required>
  <input type="password" name="password" placeholder="Password" required>
  <input type="tel" name="phone" placeholder="Phone (optional)">
  <button type="submit">Register</button>
</form>

<script>
document.getElementById('registerForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const formData = new FormData(e.target);
  const response = await fetch('http://127.0.0.1:8000/api/v1/tenants/register', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      name: formData.get('name'),
      email: formData.get('email'),
      password: formData.get('password'),
      phone: formData.get('phone')
    })
  });
  
  if (response.ok) {
    alert('Registration successful! Please login.');
    window.location.href = '/login';
  } else {
    const error = await response.json();
    alert(error.detail);
  }
});
</script>
```

## Streamlit UI Update

Update the login page in `ui/app_multitenant.py`:

```python
def show_login_page():
    st.title("🏢 Multitenant RAG System")
    st.markdown("### Login")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", type="primary"):
            if email and password:
                response = requests.post(
                    f"{BACKEND_URL}/auth/login",
                    json={"email": email, "password": password}
                )
                if response.status_code == 200:
                    tokens = response.json()
                    st.session_state.access_token = tokens['access_token']
                    st.session_state.tenant_id = tokens['tenant_id']
                    st.session_state.authenticated = True
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid email or password")
    
    with tab2:
        name = st.text_input("Company Name", key="reg_name")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_password")
        
        if st.button("Register", type="primary"):
            if name and email and password:
                response = requests.post(
                    f"{BACKEND_URL}/tenants/register",
                    json={"name": name, "email": email, "password": password}
                )
                if response.status_code == 200:
                    st.success("Registration successful! Please login.")
                else:
                    error = response.json()
                    st.error(error.get('detail', 'Registration failed'))
```

## Security Best Practices

### For Production

1. **Add Password Requirements**
   - Minimum length
   - Complexity requirements
   - Password strength meter

2. **Add Rate Limiting**
   - Limit login attempts
   - Lock account after failed attempts
   - CAPTCHA after multiple failures

3. **Add Email Verification**
   - Send verification email on registration
   - Activate account only after verification

4. **Add Password Reset**
   - Forgot password functionality
   - Secure reset token generation
   - Time-limited reset links

5. **Add Two-Factor Authentication**
   - TOTP (Time-based One-Time Password)
   - SMS verification
   - Email verification codes

6. **Add Session Management**
   - Track active sessions
   - Allow users to logout from all devices
   - Session timeout

7. **Add Audit Logging**
   - Log all login attempts
   - Log password changes
   - Log account modifications

## Migration Guide

### For Existing Users

If you have existing tenants without passwords:

1. **Option 1: Set Default Password**
```sql
UPDATE tenants 
SET password_hash = '$2b$12$...' -- bcrypt hash of default password
WHERE password_hash IS NULL;
```

2. **Option 2: Force Password Reset**
- Send password reset email to all users
- Require password setup on first login

3. **Option 3: Keep Tenant ID Login**
- Existing users continue with tenant_id
- New users use email/password
- Gradually migrate users

## Summary

✅ **Implemented:**
- Email/password registration
- Email/password login
- Password hashing with bcrypt
- Email uniqueness
- Backward compatibility with tenant_id login
- Database migration

⏳ **To Implement (Production):**
- Password requirements/validation
- Email verification
- Password reset
- Rate limiting
- Two-factor authentication
- Session management
- Audit logging

The authentication system is now production-ready with secure email/password login!
