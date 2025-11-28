# UI Password Authentication Update

## Summary

Updated the UI registration form to include password fields, matching the backend API requirements for email/password authentication.

## Changes Made

### 1. Added Password Fields to Registration Form

**New Fields:**

- Password (required, minimum 8 characters)
- Confirm Password (required, must match)

**Layout:**

```
Company Name *        [________________]
Email Address *       [________________]
Password *            [________]  Confirm Password * [________]
Phone (optional)      [________________]
Plan                  [free ▼]
```

### 2. Enhanced Validation

**Client-Side Validation:**

- ✅ All required fields check
- ✅ Email format validation
- ✅ Password minimum length (8 characters)
- ✅ Password confirmation match
- ✅ User-friendly error messages

**Validation Rules:**

```python
if not company_name or not email or not password or not confirm_password:
    error("Please fill in all required fields")
elif "@" not in email:
    error("Please enter a valid email address")
elif len(password) < 8:
    error("Password must be at least 8 characters long")
elif password != confirm_password:
    error("Passwords do not match")
```

### 3. Updated API Call

**Before:**

```python
{
  "name": company_name,
  "email": email,
  "phone": phone,
  "billing_tier": "free"
}
```

**After:**

```python
{
  "name": company_name,
  "email": email,
  "password": password,  # NEW
  "phone": phone,
  "billing_tier": "free"
}
```

### 4. Improved Error Handling

Added detailed error messages from API responses:

```python
except requests.exceptions.RequestException as e:
    st.error(f"Registration failed: {e}")
    if hasattr(e, 'response') and e.response is not None:
        try:
            error_detail = e.response.json()
            st.error(f"Details: {error_detail}")
        except:
            pass
```

## Registration Form Fields

### Required Fields (\*)

1. **Company/Organization Name**

   - Minimum: 1 character
   - Used to generate tenant slug

2. **Email Address**

   - Must contain @
   - Must be unique (checked by backend)

3. **Password**

   - Minimum: 8 characters
   - Type: password (hidden input)
   - Stored as bcrypt hash in database

4. **Confirm Password**
   - Must match Password field
   - Type: password (hidden input)

### Optional Fields

5. **Phone Number**

   - Format: Any (e.g., +1-555-0123)

6. **Billing Plan**
   - Options: free, starter, professional, enterprise
   - Default: free

## User Experience

### Registration Flow

1. **User fills form**

   ```
   Company: Acme Corp
   Email: admin@acme.com
   Password: ••••••••
   Confirm: ••••••••
   Phone: +1-555-0123
   Plan: free
   ```

2. **User clicks "Create Account"**

   - Client validates all fields
   - Shows errors if validation fails
   - Calls API if validation passes

3. **API processes request**

   - Validates email uniqueness
   - Hashes password with bcrypt
   - Creates tenant in database
   - Returns tenant info

4. **Success screen shows**

   - Tenant ID (for login)
   - Slug (URL-friendly identifier)
   - "Login Now" button

5. **User can login immediately**
   - Uses Tenant ID + Password
   - Or just Tenant ID (current implementation)

## Security Features

### Password Security

- ✅ Minimum 8 characters required
- ✅ Password confirmation required
- ✅ Passwords hidden in UI (type="password")
- ✅ Passwords hashed with bcrypt on backend
- ✅ Never stored in plain text
- ✅ Never returned in API responses

### Validation

- ✅ Client-side validation (immediate feedback)
- ✅ Server-side validation (security)
- ✅ Email uniqueness check
- ✅ Password strength requirement

### Error Messages

- ✅ User-friendly messages
- ✅ No sensitive information leaked
- ✅ Specific validation errors
- ✅ API error details when available

## Testing

### Test Registration with Password

**Via UI:**

1. Start UI: `python run_ui.py`
2. Click "Create Account" tab
3. Fill in all fields including password
4. Click "Create Account"
5. Verify success screen

**Via API:**

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/tenants/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Company",
    "email": "test@example.com",
    "password": "SecurePass123"
  }'
```

**Via Python:**

```python
import requests

response = requests.post(
    "http://127.0.0.1:8000/api/v1/tenants/register",
    json={
        "name": "Test Company",
        "email": "test@example.com",
        "password": "SecurePass123"
    }
)

print(response.status_code)  # 200
tenant = response.json()
print(tenant['id'])  # UUID
print(tenant['slug'])  # test-company-abc123
```

### Test Validation

**Test 1: Missing Password**

- Leave password blank
- Expected: "Please fill in all required fields"

**Test 2: Short Password**

- Enter "pass123" (7 chars)
- Expected: "Password must be at least 8 characters long"

**Test 3: Password Mismatch**

- Password: "SecurePass123"
- Confirm: "SecurePass124"
- Expected: "Passwords do not match"

**Test 4: Invalid Email**

- Email: "notanemail"
- Expected: "Please enter a valid email address"

**Test 5: Duplicate Email**

- Use already registered email
- Expected: "Email already registered"

## API Response

### Success Response (200 OK)

```json
{
  "id": "c419318e-d34f-4d38-a518-b86732f4e414",
  "name": "New Test Company",
  "slug": "new-test-company-aab5d5",
  "email": "newtest@example.com",
  "phone": null,
  "is_active": true,
  "created_at": "2024-11-13T12:14:32.067369",
  "billing_tier": "free",
  "billing_status": "active"
}
```

**Note:** Password is NOT included in response (security)

### Error Responses

**400 Bad Request - Duplicate Email:**

```json
{
  "detail": "Email already registered"
}
```

**422 Unprocessable Entity - Missing Field:**

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "password"],
      "msg": "Field required"
    }
  ]
}
```

## Files Modified

- ✅ `ui/app_multitenant.py` - Added password fields and validation

## Next Steps

### Immediate

1. ✅ Add password fields to registration
2. ✅ Add password validation
3. ✅ Update API call with password

### Short Term

1. ⏳ Add password strength indicator
2. ⏳ Add "Show Password" toggle
3. ⏳ Add password requirements tooltip
4. ⏳ Add email verification

### Medium Term

1. ⏳ Add "Forgot Password" feature
2. ⏳ Add password reset via email
3. ⏳ Add password change in profile
4. ⏳ Add 2FA support

## Password Requirements

### Current Requirements

- Minimum 8 characters
- No other restrictions

### Recommended for Production

- Minimum 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character
- Not in common password list

### Implementation Example

```python
import re

def validate_password_strength(password):
    if len(password) < 12:
        return False, "Password must be at least 12 characters"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain a number"
    if not re.search(r"[!@#$%^&*]", password):
        return False, "Password must contain special character"
    return True, "Password is strong"
```

## Summary

The UI registration form now includes:

- ✅ **Password Field** - Secure password input
- ✅ **Confirm Password** - Prevents typos
- ✅ **Validation** - Client-side checks
- ✅ **Error Handling** - User-friendly messages
- ✅ **Security** - Passwords hidden and hashed
- ✅ **API Integration** - Works with backend auth

Users can now create secure accounts with email and password authentication!
