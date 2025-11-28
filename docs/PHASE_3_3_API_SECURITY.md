# Phase 3.3: API Security Implementation

**Status:** ✅ COMPLETE  
**Date:** November 17, 2025

## Overview

Phase 3.3 implements comprehensive API security features including API key management, request validation, and usage tracking. This enables secure programmatic access to the API and provides visibility into usage patterns.

---

## 1. API Key Management

### Features Implemented

✅ **API Key Generation**
- Format: `sk_live_<24_random_chars>` (32 chars total)
- Cryptographically secure random generation
- Keys shown only once at creation

✅ **Secure Storage**
- Keys hashed with bcrypt (12 rounds)
- Only hash stored in database
- Prefix stored for display (e.g., `sk_live_abc...xyz`)

✅ **Key Management**
- Create new API keys
- List all keys (without full key values)
- Revoke keys (immediate deactivation)
- Rotate keys (create new, revoke old)
- Maximum 10 keys per tenant

✅ **Expiration Support**
- Optional expiration dates
- Automatic expiration checking
- Configurable per key

✅ **Usage Tracking**
- Last used timestamp
- Usage count per key
- Tracks which key was used for each request

### API Endpoints

#### Create API Key
```http
POST /api/v1/api-keys/
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "Production API Key",
  "expires_in_days": 90,  // optional
  "permissions": []        // optional, inherits tenant permissions
}
```

**Response:**
```json
{
  "id": "key-uuid",
  "api_key": "sk_live_abc123...",  // ONLY SHOWN ONCE!
  "key_prefix": "sk_live_abc...xyz",
  "name": "Production API Key",
  "tenant_id": "tenant-uuid",
  "permissions": [],
  "expires_at": "2026-02-15T00:00:00",
  "created_at": "2025-11-17T10:00:00",
  "message": "Save this API key securely. It will not be shown again."
}
```

#### List API Keys
```http
GET /api/v1/api-keys/
Authorization: Bearer <jwt_token>
```

**Response:**
```json
[
  {
    "id": "key-uuid",
    "tenant_id": "tenant-uuid",
    "name": "Production API Key",
    "key_prefix": "sk_live_abc...xyz",
    "permissions": [],
    "last_used_at": "2025-11-17T12:30:00",
    "usage_count": 1523,
    "is_active": true,
    "expires_at": "2026-02-15T00:00:00",
    "created_at": "2025-11-17T10:00:00"
  }
]
```

#### Revoke API Key
```http
DELETE /api/v1/api-keys/{key_id}
Authorization: Bearer <jwt_token>
```

**Response:** 204 No Content

#### Rotate API Key
```http
POST /api/v1/api-keys/{key_id}/rotate
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "new_key_name": "Production API Key (Rotated)"  // optional
}
```

**Response:** Same as Create API Key (includes new full key)

### Authentication Methods

The API now supports three authentication methods:

#### 1. JWT Token (Existing)
```http
Authorization: Bearer <jwt_token>
```

#### 2. API Key in Authorization Header
```http
Authorization: Bearer sk_live_abc123...
```

#### 3. API Key in X-API-Key Header
```http
X-API-Key: sk_live_abc123...
```

### Usage Example

```python
import requests

# Using API key
api_key = "sk_live_abc123..."
headers = {"Authorization": f"Bearer {api_key}"}

# Or using X-API-Key header
headers = {"X-API-Key": api_key}

# Make request
response = requests.get(
    "https://api.example.com/api/v1/query",
    headers=headers,
    json={"query": "What is RAG?"}
)
```

---

## 2. Request Validation

### Features Implemented

✅ **Input Sanitization**
- Removes null bytes
- Filters control characters
- Sanitizes text inputs

✅ **SQL Injection Prevention**
- Pattern detection for SQL injection attempts
- Blocks dangerous SQL keywords in query params
- Validates all text inputs

✅ **XSS Prevention**
- Detects script tags
- Blocks javascript: URLs
- Filters event handlers (onclick, onload, etc.)
- Blocks iframe, object, embed tags

✅ **Request Size Limits**
- Maximum request size: 100MB
- Maximum JSON payload: 10MB
- Maximum file size: 50MB per file

✅ **Tenant ID Validation**
- UUID format validation
- Validates in path, query, and headers
- Returns 400 for invalid formats

✅ **File Upload Validation**
- Whitelist of allowed extensions
- File size limits
- Type validation

### Validation Middleware

The `ValidationMiddleware` automatically validates all incoming requests:

```python
# Automatically applied to all requests
# Checks:
# - Request size
# - Tenant ID format
# - SQL injection patterns
# - XSS patterns
# - File uploads (in endpoints)
```

### Blocked Patterns

**SQL Injection:**
- `UNION SELECT`
- `DROP TABLE`
- `INSERT INTO`
- `DELETE FROM`
- `UPDATE SET`
- `-- comments`
- `; DROP`
- `EXEC()`

**XSS:**
- `<script>` tags
- `javascript:` URLs
- Event handlers (`onclick=`, `onload=`, etc.)
- `<iframe>`, `<object>`, `<embed>` tags

---

## 3. Usage Tracking

### Features Implemented

✅ **Automatic Request Logging**
- Every API request logged automatically
- No performance impact (async logging)
- Comprehensive metadata captured

✅ **Tracked Metrics**
- Request count per tenant
- Response times (avg, p50, p95, p99)
- Status codes distribution
- Error rates
- Top endpoints
- Authentication method used
- API key usage

✅ **Usage Analytics**
- View usage statistics
- Endpoint-specific stats
- Export usage data
- Time-based filtering

### Database Schema

```sql
CREATE TABLE api_usage (
    id INTEGER PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    auth_method VARCHAR(50),
    api_key_id VARCHAR(36),
    status_code INTEGER NOT NULL,
    response_time_ms REAL NOT NULL,
    error_type VARCHAR(100),
    error_message VARCHAR(500),
    user_agent VARCHAR(255),
    ip_address VARCHAR(50),
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,
    timestamp DATETIME NOT NULL
);
```

### API Endpoints

#### Get Usage Statistics
```http
GET /api/v1/usage/stats?days=7
Authorization: Bearer <token_or_api_key>
```

**Response:**
```json
{
  "total_requests": 15234,
  "status_codes": {
    "200": 14500,
    "400": 234,
    "401": 100,
    "500": 400
  },
  "avg_response_time_ms": 245.67,
  "error_count": 734,
  "error_rate_percent": 4.82,
  "top_endpoints": [
    {"endpoint": "/api/v1/query", "count": 8500},
    {"endpoint": "/api/v1/upload", "count": 3200},
    {"endpoint": "/api/v1/manage/kb", "count": 1500}
  ],
  "period": {
    "start": "2025-11-10T00:00:00",
    "end": "2025-11-17T00:00:00"
  }
}
```

#### Get Endpoint Statistics
```http
GET /api/v1/usage/endpoint/api/v1/query?days=7
Authorization: Bearer <token_or_api_key>
```

**Response:**
```json
{
  "endpoint": "/api/v1/query",
  "total_requests": 8500,
  "response_times": {
    "avg_ms": 245.67,
    "p50_ms": 180.00,
    "p95_ms": 450.00,
    "p99_ms": 890.00,
    "min_ms": 45.00,
    "max_ms": 2500.00
  }
}
```

#### Export Usage Data
```http
GET /api/v1/usage/export?days=30
Authorization: Bearer <token_or_api_key>
```

**Response:**
```json
{
  "tenant_id": "tenant-uuid",
  "period": {
    "start": "2025-10-18T00:00:00",
    "end": "2025-11-17T00:00:00"
  },
  "total_records": 45678,
  "data": [
    {
      "timestamp": "2025-11-17T12:30:00",
      "endpoint": "/api/v1/query",
      "method": "POST",
      "status_code": 200,
      "response_time_ms": 234.5,
      "auth_method": "api_key",
      "error_type": null,
      "error_message": null
    }
  ]
}
```

---

## 4. Middleware Stack

The middleware is applied in this order (first to last):

1. **ValidationMiddleware** - Validates and sanitizes requests
2. **RateLimitMiddleware** - Enforces rate limits
3. **AuthMiddleware** - Authenticates requests (JWT or API key)
4. **UsageTrackingMiddleware** - Logs requests and responses

```python
# In app/main.py
app.add_middleware(UsageTrackingMiddleware)  # Last (logs after response)
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ValidationMiddleware)  # First (validates before processing)
```

---

## 5. Security Best Practices

### API Key Security

✅ **Generation**
- Cryptographically secure random generation
- 24 random characters (144 bits of entropy)
- Prefix for easy identification

✅ **Storage**
- Never store plain keys
- Bcrypt hashing with 12 rounds
- Only hash stored in database

✅ **Display**
- Full key shown only once at creation
- Prefix shown for identification
- Clear warning to save securely

✅ **Validation**
- Constant-time comparison (bcrypt)
- Automatic expiration checking
- Usage tracking

### Request Validation

✅ **Defense in Depth**
- Multiple validation layers
- Pattern detection
- Input sanitization
- Size limits

✅ **SQL Injection Prevention**
- Pattern detection in query params
- Parameterized queries in database layer
- Input sanitization

✅ **XSS Prevention**
- Pattern detection
- HTML escaping (in Pydantic models)
- Content-Type validation

---

## 6. Testing

### Test Coverage

✅ **API Key Service Tests**
- Key generation
- Hashing and verification
- Key creation
- Key validation
- Max keys limit

✅ **API Key Endpoint Tests**
- Create key
- List keys
- Revoke key
- Rotate key
- Authentication with API key

✅ **Authentication Tests**
- JWT authentication
- API key in Authorization header
- API key in X-API-Key header
- Invalid key handling

### Running Tests

```bash
# Run all Phase 3.3 tests
pytest tests/test_api_key_management.py -v

# Run specific test
pytest tests/test_api_key_management.py::TestAPIKeyService::test_create_api_key -v
```

---

## 7. Configuration

### Environment Variables

```bash
# JWT Configuration (existing)
JWT_SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Key Configuration (defaults in code)
MAX_KEYS_PER_TENANT=10
BCRYPT_ROUNDS=12

# Request Limits (defaults in code)
MAX_REQUEST_SIZE=104857600  # 100MB
MAX_JSON_SIZE=10485760      # 10MB
MAX_FILE_SIZE=52428800      # 50MB
```

---

## 8. Migration

### Database Migration

```bash
# Migration already applied
# Table: api_usage
# Indexes: tenant_id, endpoint, status_code, timestamp
```

---

## 9. Monitoring & Alerts

### Key Metrics to Monitor

1. **API Key Usage**
   - Keys created per day
   - Keys revoked per day
   - Active keys per tenant
   - Expired keys

2. **Request Validation**
   - Blocked requests (SQL injection, XSS)
   - Invalid tenant IDs
   - Oversized requests

3. **Usage Tracking**
   - Requests per tenant
   - Error rates
   - Response times
   - Top endpoints

### Recommended Alerts

- High error rate (>5%)
- Slow response times (>1s avg)
- Many blocked requests (potential attack)
- API key approaching expiration
- Tenant approaching max keys limit

---

## 10. Next Steps

Phase 3.3 is complete! Next priorities:

1. **Phase 4.1: Quotas & Limits**
   - Implement quota service
   - Add quota enforcement
   - Create quota tracking

2. **Phase 4.2: Monitoring & Metrics**
   - Set up tenant metrics collection
   - Implement usage tracking
   - Create monitoring endpoints

3. **Phase 4.3: Cleanup & Maintenance**
   - Implement tenant deletion workflow
   - Add automated cleanup
   - Implement data retention policies

---

## 11. Summary

### What Was Implemented

✅ **API Key Management (11 tasks)**
- API key generation and storage
- CRUD endpoints for API keys
- Key rotation mechanism
- Expiration support
- Usage tracking

✅ **Request Validation (9 tasks)**
- Validation middleware
- Input sanitization
- SQL injection prevention
- XSS prevention
- Request size limits
- Tenant ID validation
- File upload validation

✅ **Usage Tracking (8 tasks)**
- API usage table and model
- Usage tracking service
- Automatic request logging
- Usage analytics endpoints
- Export functionality

### Total: 28 tasks completed

### Files Created

1. `app/services/api_key_service.py` - API key management logic
2. `app/routers/api_key_router.py` - API key endpoints
3. `app/middleware/validation_middleware.py` - Request validation
4. `app/services/usage_tracking_service.py` - Usage tracking logic
5. `app/middleware/usage_tracking_middleware.py` - Automatic logging
6. `app/routers/usage_router.py` - Usage analytics endpoints
7. `migrations/004_create_api_usage_table.sql` - Database migration
8. `tests/test_api_key_management.py` - Comprehensive tests
9. `docs/PHASE_3_3_API_SECURITY.md` - This documentation

### Files Modified

1. `app/main.py` - Added routers and middleware
2. `app/middleware/auth_middleware.py` - Added API key authentication

---

## 12. API Documentation

Full API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Look for:
- **2. API Keys** section
- **3. Usage Analytics** section
