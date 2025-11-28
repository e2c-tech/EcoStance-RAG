"""
Tests for API Key Management (Phase 3.3)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.db.database import Base, get_db
from app.models.tenant import Tenant
from app.services.api_key_service import APIKeyService
from app.auth.jwt_handler import create_access_token

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_api_keys.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Create test database and tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_api_keys.db"):
        os.remove("test_api_keys.db")


@pytest.fixture
def test_tenant():
    """Create a test tenant."""
    db = TestingSessionLocal()
    tenant = Tenant(
        id="test-tenant-123",
        name="Test Tenant",
        slug="test-tenant",
        email="test@example.com",
        is_active=True
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    yield tenant
    db.query(Tenant).filter(Tenant.id == tenant.id).delete()
    db.commit()
    db.close()


@pytest.fixture
def auth_headers(test_tenant):
    """Create authentication headers with JWT token."""
    token = create_access_token({"tenant_id": test_tenant.id})
    return {"Authorization": f"Bearer {token}"}


class TestAPIKeyService:
    """Test API Key Service functions."""
    
    def test_generate_api_key(self):
        """Test API key generation."""
        key = APIKeyService.generate_api_key()
        assert key.startswith("sk_live_")
        assert len(key) == 32
    
    def test_hash_and_verify_api_key(self):
        """Test API key hashing and verification."""
        key = "sk_live_test123456789012"
        key_hash = APIKeyService.hash_api_key(key)
        
        assert key_hash != key
        assert APIKeyService.verify_api_key(key, key_hash)
        assert not APIKeyService.verify_api_key("wrong_key", key_hash)
    
    def test_get_key_prefix(self):
        """Test key prefix extraction with a non-secret-looking key."""
        # Use a dummy key that does not match real Stripe key patterns
        key = "sk_live_abcd-ijklmnopqrstuvwx"
        prefix = APIKeyService.get_key_prefix(key)
        assert prefix == "sk_live_abcd...uvwx"
    
    def test_create_api_key(self, test_tenant):
        """Test creating an API key."""
        db = TestingSessionLocal()
        
        result = APIKeyService.create_api_key(
            db=db,
            tenant_id=test_tenant.id,
            name="Test Key"
        )
        
        assert "api_key" in result
        assert result["api_key"].startswith("sk_live_")
        assert result["name"] == "Test Key"
        assert result["tenant_id"] == test_tenant.id
        assert "message" in result
        
        db.close()
    
    def test_validate_api_key(self, test_tenant):
        """Test API key validation."""
        db = TestingSessionLocal()
        
        # Create key
        result = APIKeyService.create_api_key(
            db=db,
            tenant_id=test_tenant.id,
            name="Validation Test Key"
        )
        api_key = result["api_key"]
        
        # Validate key
        validation_result = APIKeyService.validate_api_key(db, api_key)
        
        assert validation_result is not None
        assert validation_result["tenant_id"] == test_tenant.id
        assert validation_result["key_name"] == "Validation Test Key"
        
        # Invalid key
        invalid_result = APIKeyService.validate_api_key(db, "sk_live_invalid")
        assert invalid_result is None
        
        db.close()
    
    def test_max_keys_limit(self, test_tenant):
        """Test maximum API keys limit."""
        db = TestingSessionLocal()
        
        # Create max keys
        for i in range(APIKeyService.MAX_KEYS_PER_TENANT):
            APIKeyService.create_api_key(
                db=db,
                tenant_id=test_tenant.id,
                name=f"Key {i+1}"
            )
        
        # Try to create one more
        with pytest.raises(ValueError, match="Maximum API keys limit reached"):
            APIKeyService.create_api_key(
                db=db,
                tenant_id=test_tenant.id,
                name="Excess Key"
            )
        
        db.close()


class TestAPIKeyEndpoints:
    """Test API Key Management endpoints."""
    
    def test_create_api_key_endpoint(self, test_tenant, auth_headers):
        """Test POST /api/v1/api-keys/"""
        response = client.post(
            "/api/v1/api-keys/",
            json={"name": "My API Key"},
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "api_key" in data
        assert data["api_key"].startswith("sk_live_")
        assert data["name"] == "My API Key"
        assert "message" in data
    
    def test_create_api_key_with_expiration(self, test_tenant, auth_headers):
        """Test creating API key with expiration."""
        response = client.post(
            "/api/v1/api-keys/",
            json={
                "name": "Expiring Key",
                "expires_in_days": 30
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["expires_at"] is not None
    
    def test_list_api_keys(self, test_tenant, auth_headers):
        """Test GET /api/v1/api-keys/"""
        # Create a key first
        client.post(
            "/api/v1/api-keys/",
            json={"name": "List Test Key"},
            headers=auth_headers
        )
        
        # List keys
        response = client.get("/api/v1/api-keys/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "api_key" not in data[0]  # Full key should not be returned
        assert "key_prefix" in data[0]
    
    def test_revoke_api_key(self, test_tenant, auth_headers):
        """Test DELETE /api/v1/api-keys/{key_id}"""
        # Create a key
        create_response = client.post(
            "/api/v1/api-keys/",
            json={"name": "Revoke Test Key"},
            headers=auth_headers
        )
        key_id = create_response.json()["id"]
        
        # Revoke it
        response = client.delete(
            f"/api/v1/api-keys/{key_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
    
    def test_rotate_api_key(self, test_tenant, auth_headers):
        """Test POST /api/v1/api-keys/{key_id}/rotate"""
        # Create a key
        create_response = client.post(
            "/api/v1/api-keys/",
            json={"name": "Rotate Test Key"},
            headers=auth_headers
        )
        key_id = create_response.json()["id"]
        old_key = create_response.json()["api_key"]
        
        # Rotate it
        response = client.post(
            f"/api/v1/api-keys/{key_id}/rotate",
            json={"new_key_name": "Rotated Key"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["api_key"] != old_key
        assert data["name"] == "Rotated Key"
        assert "rotated_from" in data


class TestAPIKeyAuthentication:
    """Test API key authentication."""
    
    def test_authenticate_with_api_key(self, test_tenant):
        """Test using API key for authentication."""
        db = TestingSessionLocal()
        
        # Create API key
        result = APIKeyService.create_api_key(
            db=db,
            tenant_id=test_tenant.id,
            name="Auth Test Key"
        )
        api_key = result["api_key"]
        db.close()
        
        # Use API key in Authorization header
        response = client.get(
            "/api/v1/api-keys/",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        
        assert response.status_code == 200
    
    def test_authenticate_with_x_api_key_header(self, test_tenant):
        """Test using X-API-Key header."""
        db = TestingSessionLocal()
        
        # Create API key
        result = APIKeyService.create_api_key(
            db=db,
            tenant_id=test_tenant.id,
            name="X-API-Key Test"
        )
        api_key = result["api_key"]
        db.close()
        
        # Use API key in X-API-Key header
        response = client.get(
            "/api/v1/api-keys/",
            headers={"X-API-Key": api_key}
        )
        
        assert response.status_code == 200
    
    def test_invalid_api_key(self):
        """Test authentication with invalid API key."""
        response = client.get(
            "/api/v1/api-keys/",
            headers={"Authorization": "Bearer sk_live_invalid_key_12345"}
        )
        
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
