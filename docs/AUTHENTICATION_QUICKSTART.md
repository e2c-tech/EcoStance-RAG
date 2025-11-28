# Authentication Quick Start

Get started with the authentication system in 5 minutes.

## 1. Set Environment Variables

Create or update your `.env` file:

```bash
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=sqlite:///./tenant_system.db
```

## 2. Install Dependencies

```bash
pip install python-jose[cryptography] passlib[bcrypt] pytest
```

## 3. Start the Server

```bash
uvicorn app.main:app --reload
```

## 4. Test Authentication

### Get a Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test-tenant-123",
    "user_id": "test-user-456"
  }'
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "tenant_id": "test-tenant-123"
}
```

### Use the Token

```bash
curl -X GET http://localhost:8000/api/v1/auth/verify \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response:**

```json
{
  "valid": true,
  "message": "Token is valid"
}
```

### Alternative: Use X-Tenant-ID Header

```bash
curl -X GET http://localhost:8000/api/v1/some-endpoint \
  -H "X-Tenant-ID: test-tenant-123"
```

## 5. View API Documentation

Open your browser and go to:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Look for the "0. Authentication" section.

## 6. Run Tests

```bash
python -m pytest tests/test_authentication.py -v
```

Expected output:

```
tests/test_authentication.py::test_create_access_token PASSED
tests/test_authentication.py::test_create_refresh_token PASSED
tests/test_authentication.py::test_verify_valid_token PASSED
tests/test_authentication.py::test_verify_invalid_token PASSED
tests/test_authentication.py::test_verify_wrong_token_type PASSED
tests/test_authentication.py::test_refresh_access_token PASSED
tests/test_authentication.py::test_token_expiration PASSED
tests/test_authentication.py::test_token_without_tenant_id PASSED

8 passed
```

## 7. Use in Your Code

### In a FastAPI Endpoint

```python
from fastapi import APIRouter, Depends
from app.auth.dependencies import get_tenant_id

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint(tenant_id: str = Depends(get_tenant_id)):
    return {
        "message": "Hello from authenticated endpoint",
        "tenant_id": tenant_id
    }
```

### In Python Code

```python
from app.auth.jwt_handler import create_access_token, verify_token

# Create token
token_data = {
    "tenant_id": "tenant-123",
    "user_id": "user-456"
}
token = create_access_token(token_data)

# Verify token
payload = verify_token(token)
print(f"Tenant ID: {payload['tenant_id']}")
```

## Common Issues

### Issue: "Could not validate credentials"

**Solution:** Check that your token is valid and not expired. Generate a new token.

### Issue: "Tenant not found"

**Solution:** Make sure the tenant exists in the database. Create a tenant first.

### Issue: "Tenant account is inactive"

**Solution:** Activate the tenant in the database by setting `is_active = True`.

## Next Steps

- Read the [Authentication Guide](AUTHENTICATION_GUIDE.md) for detailed documentation
- Check [Migration Examples](AUTHENTICATION_MIGRATION_EXAMPLE.md) to update existing endpoints
- Review [Implementation Summary](TASK_1.2_IMPLEMENTATION_SUMMARY.md) for technical details

## Need Help?

- Check the logs for detailed error messages
- Review the test cases in `tests/test_authentication.py`
- Consult the API documentation at http://localhost:8000/docs
