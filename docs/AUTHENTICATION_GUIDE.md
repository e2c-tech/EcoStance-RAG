# Authentication & Context Guide

This guide explains the JWT-based authentication system implemented for multitenancy support.

## Overview

The authentication system provides:
- JWT token generation and validation
- Tenant context extraction from tokens or headers
- Authentication middleware for request logging
- Tenant validation service with caching

## Components

### 1. JWT Handler (`app/auth/jwt_handler.py`)

Handles JWT token creation and verification.

**Functions:**
- `create_access_token(data, expires_delta)` - Generate access token with tenant_id
- `create_refresh_token(data)` - Generate refresh token
- `verify_token(token, token_type)` - Verify and decode token
- `refresh_access_token(refresh_token)` - Get new access token from refresh token

**Environment Variables:**
```bash
JWT_SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 2. Dependencies (`app/auth/dependencies.py`)

FastAPI dependencies for extracting tenant context.

**Functions:**
- `get_tenant_id()` - Extract tenant_id from JWT or X-Tenant-ID header
- `get_tenant_from_token()` - Get tenant object from JWT token
- `get_current_tenant()` - Get tenant from either JWT or header
- `get_optional_tenant_id()` - Extract tenant_id without raising exception

### 3. Authentication Middleware (`app/middleware/auth_middleware.py`)

Validates tenant_id on every request and adds logging.

**Features:**
- Validates JWT tokens on all requests (except excluded paths)
- Supports X-Tenant-ID header fallback
- Logs requests with tenant context
- Adds X-Process-Time and X-Tenant-ID headers to responses

**Excluded Paths:**
- `/` (root)
- `/docs` (API documentation)
- `/redoc` (API documentation)
- `/openapi.json` (OpenAPI schema)
- `/health` (health check)

### 4. Tenant Validation Service (`app/services/tenant_validation.py`)

Validates tenant existence, status, and permissions with caching.

**Methods:**
- `validate_tenant_exists(tenant_id, db)` - Check if tenant exists
- `validate_tenant_active(tenant_id, db)` - Check if tenant is active
- `validate_tenant_permission(tenant_id, permission, db)` - Check permissions
- `check_tenant_feature_flag(tenant_id, feature, db)` - Check feature flags
- `invalidate_cache(tenant_id)` - Clear cache for tenant

## Usage Examples

### 1. Login and Get Tokens

```python
import requests

# Login to get tokens
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={
        "tenant_id": "tenant-123",
        "user_id": "user-456"
    }
)

tokens = response.json()
access_token = tokens["access_token"]
refresh_token = tokens["refresh_token"]
```

### 2. Make Authenticated Requests

**Option A: Using JWT Token (Recommended)**
```python
headers = {
    "Authorization": f"Bearer {access_token}"
}

response = requests.get(
    "http://localhost:8000/api/v1/some-endpoint",
    headers=headers
)
```

**Option B: Using X-Tenant-ID Header (Fallback)**
```python
headers = {
    "X-Tenant-ID": "tenant-123"
}

response = requests.get(
    "http://localhost:8000/api/v1/some-endpoint",
    headers=headers
)
```

### 3. Refresh Access Token

```python
response = requests.post(
    "http://localhost:8000/api/v1/auth/refresh",
    json={
        "refresh_token": refresh_token
    }
)

new_tokens = response.json()
new_access_token = new_tokens["access_token"]
```

### 4. Using Dependencies in Endpoints

```python
from fastapi import APIRouter, Depends
from app.auth.dependencies import get_tenant_id, get_current_tenant
from app.models.tenant import Tenant

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint(
    tenant_id: str = Depends(get_tenant_id)
):
    """Endpoint that requires tenant_id."""
    return {"tenant_id": tenant_id}

@router.get("/my-endpoint-with-tenant")
async def my_endpoint_with_tenant(
    tenant: Tenant = Depends(get_current_tenant)
):
    """Endpoint that requires full tenant object."""
    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "is_active": tenant.is_active
    }
```

### 5. Using Tenant Validation Service

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.services.tenant_validation import tenant_validation_service

router = APIRouter()

@router.get("/protected-endpoint")
async def protected_endpoint(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    # Validate tenant exists and is active
    tenant = tenant_validation_service.validate_tenant_active(tenant_id, db)
    
    # Check specific permission
    tenant_validation_service.validate_tenant_permission(
        tenant_id, "upload", db
    )
    
    # Check feature flag
    has_feature = tenant_validation_service.check_tenant_feature_flag(
        tenant_id, "advanced_analytics", db
    )
    
    return {"message": "Access granted"}
```

## Token Structure

### Access Token Payload
```json
{
  "tenant_id": "tenant-123",
  "user_id": "user-456",
  "type": "access",
  "exp": 1699999999,
  "iat": 1699999999
}
```

### Refresh Token Payload
```json
{
  "tenant_id": "tenant-123",
  "user_id": "user-456",
  "type": "refresh",
  "exp": 1699999999,
  "iat": 1699999999
}
```

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Tenant account is inactive"
}
```

### 404 Not Found
```json
{
  "detail": "Tenant not found"
}
```

## Security Best Practices

1. **Always use HTTPS in production** - JWT tokens should never be transmitted over HTTP
2. **Keep JWT_SECRET_KEY secure** - Store in environment variables, never commit to git
3. **Use short expiration times** - Default 30 minutes for access tokens
4. **Implement token refresh** - Use refresh tokens to get new access tokens
5. **Validate tenant on every request** - Middleware ensures tenant validation
6. **Cache tenant data** - Reduces database queries for better performance
7. **Log authentication events** - Middleware logs all requests with tenant context

## Testing

Run authentication tests:
```bash
python -m pytest tests/test_authentication.py -v
```

## Next Steps

After implementing authentication, you should:
1. Add API key authentication (task 3.3)
2. Implement RBAC system (task 3.1)
3. Add audit logging (task 3.2)
4. Update all existing endpoints to use tenant context
5. Add rate limiting per tenant (task 3.3)
