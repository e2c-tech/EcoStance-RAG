# Phase 5 Backend - Quick Reference

**Date:** November 17, 2025  
**Status:** ✅ Complete

---

## New Endpoints

### Tenant Profile Management

#### Update Profile
```http
PATCH /api/v1/tenants/me/profile
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "New Company Name",
  "email": "newemail@example.com",
  "phone": "+1-555-0123"
}
```

#### Upload Logo
```http
POST /api/v1/tenants/me/logo
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: [binary data]
```

**Constraints:**
- Max size: 5MB
- Allowed types: PNG, JPG, JPEG, GIF, SVG

#### Get Logo
```http
GET /api/v1/tenants/me/logo
Authorization: Bearer {token}
```

Returns: Image file (binary)

#### Delete Logo
```http
DELETE /api/v1/tenants/me/logo
Authorization: Bearer {token}
```

---

### Notification Preferences

#### Get Preferences
```http
GET /api/v1/tenants/me/preferences
Authorization: Bearer {token}
```

**Response:**
```json
{
  "email_alerts": true,
  "quota_warnings": true,
  "error_alerts": true,
  "weekly_reports": false,
  "webhook_url": null
}
```

#### Update Preferences
```http
PUT /api/v1/tenants/me/preferences
Authorization: Bearer {token}
Content-Type: application/json

{
  "email_alerts": true,
  "quota_warnings": true,
  "error_alerts": false,
  "weekly_reports": true,
  "webhook_url": "https://example.com/webhook"
}
```

---

### Admin Dashboard

#### Dashboard Summary
```http
GET /api/v1/admin/dashboard/summary
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_tenants": 10,
    "active_tenants": 8,
    "total_users": 50,
    "total_storage_gb": 125.5,
    "total_queries_today": 1500,
    "total_api_calls_today": 5000,
    "system_health": "healthy",
    "recent_alerts": [],
    "timestamp": "2025-11-17T10:00:00Z"
  }
}
```

#### Search Tenants
```http
GET /api/v1/admin/tenants/search?q=acme&limit=20
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "query": "acme",
    "count": 2,
    "tenants": [
      {
        "id": "tenant-id",
        "name": "Acme Corp",
        "slug": "acme-corp",
        "email": "admin@acme.com",
        "is_active": true,
        "billing_tier": "professional",
        "billing_status": "active",
        "created_at": "2025-01-01T00:00:00Z"
      }
    ]
  }
}
```

#### Update Tenant Tier
```http
PATCH /api/v1/admin/tenants/{tenant_id}/tier?tier=professional
Authorization: Bearer {admin_token}
```

**Valid tiers:** free, starter, professional, enterprise

**Response:**
```json
{
  "success": true,
  "message": "Tenant tier updated from free to professional",
  "data": {
    "tenant_id": "tenant-id",
    "old_tier": "free",
    "new_tier": "professional",
    "quotas": {
      "max_storage_bytes": 214748364800,
      "max_queries_per_day": 20000,
      "max_queries_per_month": 600000,
      "max_documents": 200000,
      "max_db_connections": 25
    }
  }
}
```

#### Suspend Tenant
```http
POST /api/v1/admin/tenants/{tenant_id}/suspend
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "reason": "Payment overdue"
}
```

#### Reactivate Tenant
```http
POST /api/v1/admin/tenants/{tenant_id}/reactivate
Authorization: Bearer {admin_token}
```

#### Get Tenant Activity
```http
GET /api/v1/admin/tenants/{tenant_id}/activity?days=7
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "tenant_id": "tenant-id",
    "period_days": 7,
    "summary": {
      "total_api_calls": 1500,
      "total_errors": 10,
      "error_rate": 0.67
    },
    "recent_activity": [
      {
        "endpoint": "/api/v1/rag/query",
        "method": "POST",
        "status_code": 200,
        "timestamp": "2025-11-17T10:00:00Z"
      }
    ]
  }
}
```

---

## Tier Quotas

### Free Tier
- Storage: 10GB
- Queries: 1,000/day, 30,000/month
- Documents: 10,000
- DB Connections: 5

### Starter Tier
- Storage: 50GB
- Queries: 5,000/day, 150,000/month
- Documents: 50,000
- DB Connections: 10

### Professional Tier
- Storage: 200GB
- Queries: 20,000/day, 600,000/month
- Documents: 200,000
- DB Connections: 25

### Enterprise Tier
- Storage: 1TB
- Queries: 100,000/day, 3,000,000/month
- Documents: 1,000,000
- DB Connections: 100

---

## Configuration

### Logo Upload
```python
LOGO_UPLOAD_DIR = "uploads/logos"
ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg"}
MAX_LOGO_SIZE = 5 * 1024 * 1024  # 5MB
```

### Notification Preferences
Stored in `tenant.settings.preferences`:
```json
{
  "preferences": {
    "email_alerts": true,
    "quota_warnings": true,
    "error_alerts": true,
    "weekly_reports": false,
    "webhook_url": "https://example.com/webhook"
  }
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid file type. Allowed: .png, .jpg, .jpeg, .gif, .svg"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Admin access required"
}
```

### 404 Not Found
```json
{
  "detail": "Tenant not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to update tenant tier: [error message]"
}
```

---

## Testing Examples

### cURL Examples

```bash
# Update profile
curl -X PATCH http://localhost:8000/api/v1/tenants/me/profile \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Name", "phone": "+1-555-0123"}'

# Upload logo
curl -X POST http://localhost:8000/api/v1/tenants/me/logo \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@logo.png"

# Get preferences
curl http://localhost:8000/api/v1/tenants/me/preferences \
  -H "Authorization: Bearer YOUR_TOKEN"

# Update preferences
curl -X PUT http://localhost:8000/api/v1/tenants/me/preferences \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email_alerts": true, "quota_warnings": true}'

# Admin dashboard
curl http://localhost:8000/api/v1/admin/dashboard/summary \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Search tenants
curl "http://localhost:8000/api/v1/admin/tenants/search?q=acme" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Update tier
curl -X PATCH "http://localhost:8000/api/v1/admin/tenants/TENANT_ID/tier?tier=professional" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Suspend tenant
curl -X POST http://localhost:8000/api/v1/admin/tenants/TENANT_ID/suspend \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Payment overdue"}'
```

### Python Examples

```python
import requests

# Get token
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "user@example.com", "password": "password"}
)
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Update profile
requests.patch(
    "http://localhost:8000/api/v1/tenants/me/profile",
    headers=headers,
    json={"name": "New Name"}
)

# Upload logo
with open("logo.png", "rb") as f:
    files = {"file": ("logo.png", f, "image/png")}
    requests.post(
        "http://localhost:8000/api/v1/tenants/me/logo",
        headers=headers,
        files=files
    )

# Get preferences
response = requests.get(
    "http://localhost:8000/api/v1/tenants/me/preferences",
    headers=headers
)
preferences = response.json()

# Admin dashboard
response = requests.get(
    "http://localhost:8000/api/v1/admin/dashboard/summary",
    headers=admin_headers
)
dashboard = response.json()
```

---

## Database Schema

### Tenant Model Updates

```sql
-- New columns
ALTER TABLE tenants ADD COLUMN logo_url VARCHAR(500);
ALTER TABLE tenants ADD COLUMN logo_filename VARCHAR(255);
CREATE INDEX idx_tenants_logo_filename ON tenants(logo_filename);
```

### Settings JSON Structure

```json
{
  "max_storage_bytes": 10737418240,
  "max_queries_per_day": 1000,
  "max_queries_per_month": 30000,
  "max_documents": 10000,
  "max_db_connections": 5,
  "features": ["rag", "db_chat"],
  "region": "default",
  "preferences": {
    "email_alerts": true,
    "quota_warnings": true,
    "error_alerts": true,
    "weekly_reports": false,
    "webhook_url": null
  }
}
```

---

## Security Notes

### Authentication
- All endpoints require valid JWT token
- Admin endpoints require admin role
- Token must be in Authorization header

### File Upload Security
- File extension whitelist
- File size limit (5MB)
- Unique filename generation
- Isolated storage directory
- Old file cleanup on replacement

### Data Validation
- Email format validation
- Tier validation (enum check)
- Phone number optional
- Webhook URL optional

---

## Frontend Integration Checklist

- [ ] Implement login/registration UI
- [ ] Create tenant settings page
- [ ] Add profile update form
- [ ] Implement logo upload component
- [ ] Build notification preferences UI
- [ ] Create usage dashboard
- [ ] Build admin dashboard
- [ ] Add tenant search functionality
- [ ] Implement tier management UI
- [ ] Add suspension/reactivation controls
- [ ] Create activity log viewer

---

## Support

For issues or questions:
1. Check `docs/PHASE_5_BACKEND_SUMMARY.md` for detailed documentation
2. Review `docs/PHASE_5_BACKEND_REQUIREMENTS.md` for requirements
3. Run `python tests/test_phase5_backend.py` to test endpoints
4. Check API logs for error details

---

**Phase 5 Backend: Ready for Frontend Integration** ✅
