# UI Registration Update

## Overview
Updated the Streamlit UI to include a tenant registration page, allowing users to create accounts directly through the interface.

## Changes Made

### 1. Added Registration Functionality

**New Functions:**
- `register_tenant()` - Calls the tenant registration API
- `show_registration_form()` - Displays the registration form
- Updated `show_login_page()` - Now shows tabs for Login and Create Account

### 2. Registration Form Fields

**Required Fields:**
- Company/Organization Name
- Email Address

**Optional Fields:**
- Phone Number
- Billing Plan (free, starter, professional, enterprise)

### 3. User Experience Flow

```
Landing Page
├─ Tab 1: Login
│   ├─ Tenant ID input
│   ├─ User ID input (optional)
│   └─ Login button
│
└─ Tab 2: Create Account
    ├─ Company Name input *
    ├─ Email input *
    ├─ Phone input
    ├─ Plan selector
    ├─ Create Account button
    └─ Success screen with:
        ├─ Tenant ID display
        ├─ Slug display
        ├─ Warning to save credentials
        └─ Login Now button
```

## Features

### Registration Form

**Input Fields:**
1. **Company/Organization Name** (Required)
   - Placeholder: "e.g., Acme Corporation"
   - Used to generate tenant slug

2. **Email Address** (Required)
   - Placeholder: "e.g., admin@acme.com"
   - Basic validation (checks for @)

3. **Phone Number** (Optional)
   - Placeholder: "e.g., +1-555-0123"

4. **Billing Plan** (Dropdown)
   - Free: 10GB storage, 1000 queries/day
   - Starter: 50GB storage, 5000 queries/day
   - Professional: 200GB storage, 20000 queries/day
   - Enterprise: Unlimited storage & queries

### Success Screen

After successful registration, users see:

1. **Celebration** - Balloons animation
2. **Welcome Message** - "Welcome to the Multitenant RAG System!"
3. **Tenant Credentials**:
   - Tenant ID (UUID format)
   - Slug (URL-friendly identifier)
4. **Warning** - Reminder to save Tenant ID
5. **Quick Login** - "Login Now" button for immediate access

### Validation

**Client-Side Validation:**
- Required fields check
- Email format validation (basic)
- Error messages for invalid input

**Server-Side Validation:**
- Handled by backend API
- Returns appropriate error messages

## UI Layout

### Login Tab
```
┌─────────────────────────────────────┐
│  🔐 Login                           │
├─────────────────────────────────────┤
│                                     │
│  Tenant ID                          │
│  [acme-corp-abc123____________]     │
│                                     │
│  User ID (optional)                 │
│  [user_____________________]        │
│                                     │
│  [      🔐 Login      ]             │
│                                     │
│  ℹ️ Demo: Use `default-tenant`      │
└─────────────────────────────────────┘
```

### Registration Tab
```
┌─────────────────────────────────────┐
│  📝 Create Account                  │
├─────────────────────────────────────┤
│                                     │
│  Company/Organization Name *        │
│  [Acme Corporation_________]        │
│                                     │
│  Email Address *                    │
│  [admin@acme.com___________]        │
│                                     │
│  Phone Number (optional)            │
│  [+1-555-0123______________]        │
│                                     │
│  Plan: [free ▼]  ✅ 10GB, 1000/day │
│                                     │
│  [   📝 Create Account   ]          │
│                                     │
│  By creating an account, you agree  │
│  to our Terms of Service            │
└─────────────────────────────────────┘
```

### Success Screen
```
┌─────────────────────────────────────┐
│  ✅ Account created successfully!   │
│  🎈 🎈 🎈                           │
├─────────────────────────────────────┤
│  🎉 Welcome to the Multitenant      │
│     RAG System!                     │
│                                     │
│  ┌─────────────┬─────────────┐     │
│  │ Tenant ID   │ Slug        │     │
│  │ uuid-here   │ acme-abc123 │     │
│  └─────────────┴─────────────┘     │
│                                     │
│  ⚠️ Important: Save your Tenant ID! │
│     You'll need it to login.        │
│                                     │
│  [      🚀 Login Now      ]         │
└─────────────────────────────────────┘
```

## API Integration

### Registration Endpoint

**Request:**
```python
POST /api/v1/tenants/register
{
  "name": "Acme Corporation",
  "email": "admin@acme.com",
  "phone": "+1-555-0123",
  "billing_tier": "free"
}
```

**Response:**
```python
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Acme Corporation",
  "slug": "acme-corporation-a1b2c3",
  "email": "admin@acme.com",
  "phone": "+1-555-0123",
  "is_active": true,
  "created_at": "2024-11-13T10:00:00",
  "billing_tier": "free",
  "billing_status": "active"
}
```

### Auto-Login After Registration

After successful registration, users can click "Login Now" to automatically:
1. Use the returned tenant ID
2. Call the login API
3. Store JWT tokens
4. Redirect to dashboard

## Usage Examples

### New User Registration Flow

1. **User visits the UI**
   - Sees login page with two tabs

2. **User clicks "Create Account" tab**
   - Fills in company name: "Acme Corp"
   - Fills in email: "admin@acme.com"
   - Optionally adds phone
   - Selects plan: "free"

3. **User clicks "Create Account"**
   - System validates input
   - Calls registration API
   - Shows success screen

4. **User sees credentials**
   - Tenant ID: `550e8400-e29b-41d4-a716-446655440000`
   - Slug: `acme-corp-a1b2c3`
   - Warning to save credentials

5. **User clicks "Login Now"**
   - Automatically logs in
   - Redirected to dashboard

### Existing User Login Flow

1. **User visits the UI**
   - Stays on "Login" tab

2. **User enters Tenant ID**
   - Uses saved tenant ID from registration

3. **User clicks "Login"**
   - Authenticates
   - Redirected to dashboard

## Code Examples

### Registration Function
```python
def register_tenant(company_name: str, email: str, phone: str = "") -> Optional[dict]:
    """Register a new tenant."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/tenants/register",
            json={
                "name": company_name,
                "email": email,
                "phone": phone if phone else None,
                "billing_tier": "free"
            }
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Registration failed: {e}")
        return None
```

### Auto-Login After Registration
```python
if st.button("🚀 Login Now"):
    if login(result['id'], "admin"):
        st.success("✅ Logged in!")
        time.sleep(0.5)
        st.rerun()
```

## Benefits

### For Users
- **Easy Onboarding** - Self-service registration
- **No Manual Setup** - Automatic tenant creation
- **Immediate Access** - Login right after registration
- **Clear Credentials** - Tenant ID and slug displayed
- **Plan Selection** - Choose appropriate tier

### For Administrators
- **Reduced Support** - Users can register themselves
- **Automatic Provisioning** - Tenants created instantly
- **Tracking** - All registrations logged
- **Scalable** - No manual intervention needed

## Security Considerations

### Current Implementation
- ✅ Basic email validation
- ✅ Required field validation
- ✅ API error handling
- ⚠️ No email verification
- ⚠️ No CAPTCHA
- ⚠️ No rate limiting on UI

### Production Recommendations

1. **Add Email Verification**
   ```python
   # After registration
   send_verification_email(email, tenant_id)
   # Show: "Check your email to verify"
   ```

2. **Add CAPTCHA**
   ```python
   # Use reCAPTCHA or similar
   if not verify_captcha(captcha_response):
       st.error("Please complete the CAPTCHA")
   ```

3. **Add Password Field**
   ```python
   password = st.text_input("Password", type="password")
   confirm_password = st.text_input("Confirm Password", type="password")
   ```

4. **Add Terms Acceptance**
   ```python
   accept_terms = st.checkbox("I agree to the Terms of Service")
   if not accept_terms:
       st.error("You must accept the terms")
   ```

## Testing

### Manual Testing

1. **Test Registration**
   ```bash
   # Start UI
   python run_ui.py
   
   # Navigate to Create Account tab
   # Fill in form
   # Click Create Account
   # Verify success screen
   ```

2. **Test Validation**
   - Try submitting without company name
   - Try submitting without email
   - Try invalid email format
   - Verify error messages

3. **Test Auto-Login**
   - Complete registration
   - Click "Login Now"
   - Verify redirect to dashboard

### Automated Testing

```python
import requests

def test_ui_registration():
    # Test registration API
    response = requests.post(
        "http://127.0.0.1:8000/api/v1/tenants/register",
        json={
            "name": "Test Company",
            "email": "test@test.com"
        }
    )
    assert response.status_code == 200
    
    tenant = response.json()
    assert "id" in tenant
    assert "slug" in tenant
    
    # Test login with new tenant
    response = requests.post(
        "http://127.0.0.1:8000/api/v1/auth/login",
        json={"tenant_id": tenant['id']}
    )
    assert response.status_code == 200
```

## Files Modified

- ✅ `ui/app_multitenant.py` - Added registration functionality

## Next Steps

### Immediate
1. ✅ Add registration form
2. ✅ Add success screen
3. ✅ Add auto-login

### Short Term
1. ⏳ Add email verification
2. ⏳ Add password authentication
3. ⏳ Add CAPTCHA
4. ⏳ Add terms acceptance checkbox

### Medium Term
1. ⏳ Add "Forgot Tenant ID" feature
2. ⏳ Add email-based login
3. ⏳ Add profile management
4. ⏳ Add billing integration

## Troubleshooting

### Registration Fails
- Check backend is running
- Check API endpoint is accessible
- Check network connectivity
- View browser console for errors

### Auto-Login Doesn't Work
- Check tenant ID is valid
- Check login API is working
- Check JWT token generation

### Credentials Not Displayed
- Check API response format
- Check success condition
- View Streamlit logs

## Summary

The UI now includes:
- ✅ **Registration Tab** - Self-service account creation
- ✅ **Login Tab** - Existing user authentication
- ✅ **Success Screen** - Credential display and auto-login
- ✅ **Validation** - Client-side input validation
- ✅ **Error Handling** - User-friendly error messages
- ✅ **Plan Selection** - Choose billing tier
- ✅ **Auto-Login** - Immediate access after registration

Users can now create accounts and start using the system without any manual intervention!
