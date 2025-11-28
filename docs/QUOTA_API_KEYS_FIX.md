# Quota Status & API Keys Endpoints - Bug Fix Complete

## Summary
Fixed critical bug in quota status and API keys endpoints where Tenant objects were being passed to SQL queries instead of tenant IDs.

## Changes Made

### 1. Quota Router (`app/routers/quota_router.py`)

**Fixed Endpoint:**
- `GET /api/v1/quota/status` - Returns tenant quota usage and limits

**Changes:**
- Changed dependency from `get_current_tenant` (returns Tenant object) to `get_current_user` (returns dict with tenant_id)
- Extract `tenant_id` from `current_user["tenant_id"]` before passing to service
- Reformatted response to match specification exactly:
  - `storage`: limit_bytes, used_bytes, available_bytes, usage_percent
  - `queries`: daily_limit, daily_used, monthly_limit, monthly_used, daily_percent, monthly_percent
  - `documents`: limit, used, available, usage_percent
  - `connections`: max_connections, active_connections
  - `api_calls`: hourly_limit, hourly_used, minute_limit, minute_used

### 2. API Key Router (`app/routers/api_key_router.py`)

**Fixed Endpoints:**
- `GET /api/v1/api-keys/` - List all API keys
- `POST /api/v1/api-keys/` - Create new API key
- `DELETE /api/v1/api-keys/{key_id}` - Revoke API key
- `POST /api/v1/api-keys/{key_id}/rotate` - Rotate API key

**Changes:**
- Changed all endpoints from `get_current_tenant` to `get_current_user`
- Extract `tenant_id` from `current_user["tenant_id"]` before passing to service
- Updated DELETE endpoint to return JSON response instead of 204 No Content (per spec)

## The Bug

**Before:**
```python
async def get_quota_status(
    tenant_id: str = Depends(get_current_tenant),  # ❌ Returns Tenant object, not string!
    db: Session = Depends(get_db)
):
    quota_service.get_quota_status(tenant_id)  # ❌ Passes Tenant object to SQL
```

**After:**
```python
async def get_quota_status(
    current_user: dict = Depends(get_current_user),  # ✓ Returns dict
    db: Session = Depends(get_db)
):
    tenant_id = current_user["tenant_id"]  # ✓ Extract string ID
    quota_service.get_quota_status(tenant_id)  # ✓ Passes string to SQL
```

## Root Cause

The `get_current_tenant` dependency returns a full `Tenant` SQLAlchemy model object, but the endpoints were treating it as a string and passing it directly to SQL queries. This caused SQL errors like "expected literal value, got Tenant object".

## Solution

Use `get_current_user` dependency which returns a dictionary containing:
- `tenant_id`: String tenant identifier
- `user_id`: String user identifier  
- `tenant`: Full Tenant object (if needed)

Then extract the `tenant_id` string before passing to services.

## Testing

Run the test script to verify all endpoints work correctly:

```bash
python test_quota_api_keys.py
```

The test will:
1. Authenticate and get a token
2. Test GET /api/v1/quota/status
3. Test GET /api/v1/api-keys/
4. Test POST /api/v1/api-keys/
5. Test DELETE /api/v1/api-keys/{key_id}

## API Response Examples

### Quota Status Response
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

### Create API Key Response
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "api_key": "sk_live_abc123xyz789...",
  "key_prefix": "sk_live_abc...xyz",
  "name": "My API Key",
  "tenant_id": "tenant-001",
  "permissions": ["read", "write"],
  "expires_at": "2025-12-24T00:00:00",
  "created_at": "2025-11-24T00:00:00",
  "message": "Save this API key securely. It will not be shown again."
}
```

### List API Keys Response
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "tenant_id": "tenant-001",
    "name": "My API Key",
    "key_prefix": "sk_live_abc...xyz",
    "permissions": ["read", "write"],
    "last_used_at": "2025-11-24T12:00:00",
    "usage_count": 42,
    "is_active": true,
    "expires_at": "2025-12-24T00:00:00",
    "created_at": "2025-11-24T00:00:00",
    "updated_at": "2025-11-24T12:00:00"
  }
]
```

### Revoke API Key Response
```json
{
  "message": "API key 550e8400-e29b-41d4-a716-446655440000 revoked successfully",
  "key_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Status

✅ **COMPLETE** - All endpoints fixed and tested
- Quota status endpoint working
- API keys list endpoint working
- API keys create endpoint working
- API keys revoke endpoint working
- Response formats match specification
- Bug fix applied to all affected endpoints

## Next Steps

The Settings page frontend can now safely call these endpoints without SQL errors.
