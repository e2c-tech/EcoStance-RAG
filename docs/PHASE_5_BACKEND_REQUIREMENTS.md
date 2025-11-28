# Phase 5: Backend Requirements for UI Support

**Date:** November 17, 2025  
**Status:** Requirements Document

---

## Overview

Phase 5 is primarily frontend work, but requires some additional backend endpoints and features to support the UI. This document outlines what backend work is needed.

---

## What's Already Complete ✅

From previous phases, we already have:

### Authentication & Authorization
- ✅ JWT token generation and validation
- ✅ API key authentication
- ✅ Permission-based access control
- ✅ Auth middleware with tenant context
- ✅ Login endpoint (`POST /api/v1/auth/login`)
- ✅ Token validation

### Tenant Management
- ✅ Tenant CRUD endpoints
- ✅ Tenant creation, read, update, delete
- ✅ Tenant listing with filters

### Resource Management
- ✅ Quota status endpoints
- ✅ Metrics and monitoring endpoints
- ✅ Usage tracking
- ✅ Alert history

### API Key Management
- ✅ API key creation, listing, revocation
- ✅ API key rotation

---

## What Needs to Be Added 🔨

### 1. Session Management (Optional)

**If using server-side sessions:**

```python
# app/routers/auth_router.py additions

@router.post("/auth/refresh")
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """Refresh an expired access token."""
    # Validate refresh token
    # Generate new access token
    # Return new token
    pass

@router.post("/auth/logout")
async def logout(
    token: str = Depends(get_current_token),
    db: Session = Depends(get_db)
):
    """Revoke token on logout."""
    # Add token to blacklist or delete session
    # Return success
    pass

@router.get("/auth/session")
async def get_session_info(
    tenant_id: str = Depends(get_current_tenant),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current session information."""
    # Return session details
    pass
```

**Files to create:**
- `app/services/session_service.py` (if using server-side sessions)
- Add session table to database (if needed)

**Estimated effort:** 2-3 hours

---

### 2. Password Reset Flow

**Endpoints needed:**

```python
# app/routers/auth_router.py additions

@router.post("/auth/forgot-password")
async def forgot_password(
    email: str,
    db: Session = Depends(get_db)
):
    """Request password reset."""
    # Generate reset token
    # Send email with reset link
    # Return success
    pass

@router.post("/auth/reset-password")
async def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """Reset password with token."""
    # Validate token
    # Update password
    # Return success
    pass

@router.post("/auth/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Change password (authenticated)."""
    # Verify current password
    # Update to new password
    # Return success
    pass
```

**Files to create:**
- Add password reset token table to database
- Email service for sending reset links (or use existing)

**Estimated effort:** 3-4 hours

---

### 3. Tenant Profile Management

**Endpoints needed:**

```python
# app/routers/tenant_router.py additions

@router.patch("/tenants/me/profile")
async def update_tenant_profile(
    profile: TenantProfileUpdate,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Update tenant profile (name, email, phone)."""
    pass

@router.post("/tenants/me/logo")
async def upload_tenant_logo(
    file: UploadFile,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Upload tenant logo."""
    # Save logo to storage
    # Update tenant record with logo URL
    pass

@router.get("/tenants/me/logo")
async def get_tenant_logo(
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get tenant logo."""
    # Return logo file or URL
    pass

@router.delete("/tenants/me/logo")
async def delete_tenant_logo(
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Delete tenant logo."""
    pass
```

**Pydantic models:**

```python
class TenantProfileUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
```

**Estimated effort:** 2-3 hours

---

### 4. Notification Preferences

**Endpoints needed:**

```python
# app/routers/tenant_router.py additions

@router.get("/tenants/me/preferences")
async def get_preferences(
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get notification preferences."""
    # Return preferences from tenant.settings
    pass

@router.put("/tenants/me/preferences")
async def update_preferences(
    preferences: NotificationPreferences,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Update notification preferences."""
    # Update tenant.settings JSON field
    pass
```

**Pydantic models:**

```python
class NotificationPreferences(BaseModel):
    email_alerts: bool = True
    quota_warnings: bool = True
    error_alerts: bool = True
    weekly_reports: bool = False
    webhook_url: str | None = None
```

**Estimated effort:** 1-2 hours

---

### 5. Multi-Tenant User Support

**For users who belong to multiple tenants:**

```python
# app/routers/user_router.py (new file)

@router.get("/users/me/tenants")
async def list_user_tenants(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all tenants the user has access to."""
    # Query tenant_users table
    # Return list of tenants with roles
    pass

@router.post("/users/me/tenants/{tenant_id}/switch")
async def switch_tenant(
    tenant_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Switch active tenant context."""
    # Verify user has access to tenant
    # Generate new token with new tenant_id
    # Return new token
    pass

@router.get("/users/me/profile")
async def get_user_profile(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user profile."""
    pass
```

**Files to create:**
- `app/routers/user_router.py`
- Update auth middleware to support multi-tenant users

**Estimated effort:** 3-4 hours

---

### 6. Enhanced Admin Endpoints

**Additional admin functionality:**

```python
# app/routers/admin_router.py additions

@router.get("/admin/dashboard/summary")
async def get_dashboard_summary(
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get admin dashboard summary statistics."""
    return {
        "total_tenants": ...,
        "active_tenants": ...,
        "total_users": ...,
        "total_storage_gb": ...,
        "total_queries_today": ...,
        "total_api_calls_today": ...,
        "system_health": "healthy",
        "recent_alerts": [...]
    }

@router.get("/admin/tenants/search")
async def search_tenants(
    q: str,
    limit: int = 20,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Search tenants by name, email, or slug."""
    # Search tenants
    # Return matching tenants
    pass

@router.patch("/admin/tenants/{tenant_id}/tier")
async def update_tenant_tier(
    tenant_id: str,
    tier: str,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update tenant billing tier."""
    # Update tenant.billing_tier
    # Update quotas based on new tier
    pass

@router.post("/admin/tenants/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: str,
    reason: str,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Suspend a tenant."""
    # Set tenant.is_active = False
    # Set tenant.billing_status = "suspended"
    # Log audit event
    pass

@router.post("/admin/tenants/{tenant_id}/reactivate")
async def reactivate_tenant(
    tenant_id: str,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Reactivate a suspended tenant."""
    # Set tenant.is_active = True
    # Set tenant.billing_status = "active"
    # Log audit event
    pass

@router.get("/admin/tenants/{tenant_id}/activity")
async def get_tenant_activity(
    tenant_id: str,
    days: int = 7,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get tenant activity log."""
    # Query audit_logs
    # Return recent activity
    pass
```

**Estimated effort:** 3-4 hours

---

### 7. Tenant Logo Storage

**Add logo field to tenant model:**

```python
# app/models/tenant.py addition

class Tenant(Base):
    # ... existing fields ...
    logo_url = Column(String(500), nullable=True)
    logo_filename = Column(String(255), nullable=True)
```

**Migration needed:**
```sql
-- migrations/007_add_tenant_logo.sql
ALTER TABLE tenants ADD COLUMN logo_url VARCHAR(500);
ALTER TABLE tenants ADD COLUMN logo_filename VARCHAR(255);
```

**Estimated effort:** 1 hour

---

## Summary of Backend Work Needed

### Required (Core Functionality)
1. ✅ **Tenant Profile Management** - 2-3 hours
2. ✅ **Notification Preferences** - 1-2 hours
3. ✅ **Enhanced Admin Endpoints** - 3-4 hours
4. ✅ **Tenant Logo Storage** - 1 hour

**Total Required: 7-10 hours**

### Optional (Enhanced Features)
5. **Session Management** - 2-3 hours (if using server-side sessions)
6. **Password Reset Flow** - 3-4 hours (if needed)
7. **Multi-Tenant User Support** - 3-4 hours (if users can belong to multiple tenants)

**Total Optional: 8-11 hours**

---

## Implementation Priority

### High Priority (Do First)
1. Tenant profile management endpoints
2. Enhanced admin dashboard endpoints
3. Tenant logo upload/storage

### Medium Priority
4. Notification preferences
5. Admin tenant search and filtering

### Low Priority (Optional)
6. Password reset flow (if not using external auth)
7. Session management (if using stateless JWT)
8. Multi-tenant user support (if not needed initially)

---

## What Frontend Needs from Backend

### For Login/Auth
- ✅ `POST /api/v1/auth/login` - Already exists
- ✅ `POST /api/v1/auth/register` - Already exists
- ⏳ `POST /api/v1/auth/logout` - Optional (token revocation)
- ⏳ `POST /api/v1/auth/forgot-password` - Optional
- ⏳ `POST /api/v1/auth/reset-password` - Optional

### For Tenant Settings
- ✅ `GET /api/v1/tenants/me` - Already exists
- ⏳ `PATCH /api/v1/tenants/me/profile` - Needed
- ⏳ `POST /api/v1/tenants/me/logo` - Needed
- ⏳ `GET /api/v1/tenants/me/preferences` - Needed
- ⏳ `PUT /api/v1/tenants/me/preferences` - Needed

### For Usage Dashboard
- ✅ `GET /api/v1/quota/status` - Already exists
- ✅ `GET /api/v1/metrics/storage` - Already exists
- ✅ `GET /api/v1/metrics/queries` - Already exists
- ✅ `GET /api/v1/metrics/export` - Already exists

### For Admin Dashboard
- ✅ `GET /api/v1/admin/health/system` - Already exists
- ⏳ `GET /api/v1/admin/dashboard/summary` - Needed
- ⏳ `GET /api/v1/admin/tenants/search` - Needed
- ⏳ `PATCH /api/v1/admin/tenants/{id}/tier` - Needed
- ⏳ `POST /api/v1/admin/tenants/{id}/suspend` - Needed

### For API Key Management
- ✅ `GET /api/v1/api-keys/` - Already exists
- ✅ `POST /api/v1/api-keys/` - Already exists
- ✅ `DELETE /api/v1/api-keys/{id}` - Already exists

---

## Recommendation

**For Phase 5 Backend Work:**

Focus on the **Required** items (7-10 hours):
1. Tenant profile management
2. Notification preferences
3. Enhanced admin endpoints
4. Tenant logo storage

The **Optional** items can be added later based on actual frontend needs:
- Password reset (if not using OAuth/external auth)
- Session management (if JWT isn't sufficient)
- Multi-tenant users (if that use case exists)

**Most of Phase 5 is frontend work** - the backend is already 80% ready!

---

## Next Steps

1. Review this document with frontend team
2. Confirm which optional features are needed
3. Implement required backend endpoints (7-10 hours)
4. Frontend team can start building UI in parallel
5. Test integration between frontend and backend

---

## Files to Create/Modify

### New Files (4-5)
- `app/routers/user_router.py` (if multi-tenant users needed)
- `app/services/session_service.py` (if server-side sessions)
- `migrations/007_add_tenant_logo.sql`
- `migrations/008_add_password_reset_tokens.sql` (if password reset needed)

### Files to Modify (3-4)
- `app/routers/tenant_router.py` (add profile, logo, preferences endpoints)
- `app/routers/admin_router.py` (add dashboard, search, suspend endpoints)
- `app/routers/auth_router.py` (add logout, password reset if needed)
- `app/models/tenant.py` (add logo fields)

**Total: 7-9 files**

---

## Conclusion

**Phase 5 backend work is minimal** - most endpoints already exist from Phases 1-4. The main additions needed are:
- Tenant profile/logo management
- Enhanced admin dashboard
- Notification preferences

Everything else is frontend work that can use existing APIs.

**Estimated backend effort: 7-10 hours for required features**
