"""
Test authentication and JWT token functionality.
"""
import pytest
from datetime import datetime, timedelta
from app.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_token,
    refresh_access_token
)
from fastapi import HTTPException


def test_create_access_token():
    """Test access token creation."""
    token_data = {
        "tenant_id": "test-tenant-123",
        "user_id": "user-456"
    }
    
    token = create_access_token(token_data)
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_refresh_token():
    """Test refresh token creation."""
    token_data = {
        "tenant_id": "test-tenant-123",
        "user_id": "user-456"
    }
    
    token = create_refresh_token(token_data)
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_valid_token():
    """Test verification of valid token."""
    token_data = {
        "tenant_id": "test-tenant-123",
        "user_id": "user-456"
    }
    
    token = create_access_token(token_data)
    payload = verify_token(token, token_type="access")
    
    assert payload is not None
    assert payload["tenant_id"] == "test-tenant-123"
    assert payload["user_id"] == "user-456"
    assert payload["type"] == "access"


def test_verify_invalid_token():
    """Test verification of invalid token."""
    invalid_token = "invalid.token.here"
    
    with pytest.raises(HTTPException) as exc_info:
        verify_token(invalid_token)
    
    assert exc_info.value.status_code == 401


def test_verify_wrong_token_type():
    """Test verification fails when token type doesn't match."""
    token_data = {
        "tenant_id": "test-tenant-123",
        "user_id": "user-456"
    }
    
    access_token = create_access_token(token_data)
    
    with pytest.raises(HTTPException) as exc_info:
        verify_token(access_token, token_type="refresh")
    
    assert exc_info.value.status_code == 401
    assert "Invalid token type" in exc_info.value.detail


def test_refresh_access_token():
    """Test refreshing access token from refresh token."""
    token_data = {
        "tenant_id": "test-tenant-123",
        "user_id": "user-456"
    }
    
    refresh_token = create_refresh_token(token_data)
    new_access_token = refresh_access_token(refresh_token)
    
    assert new_access_token is not None
    assert isinstance(new_access_token, str)
    
    # Verify new access token contains correct data
    payload = verify_token(new_access_token, token_type="access")
    assert payload["tenant_id"] == "test-tenant-123"
    assert payload["user_id"] == "user-456"


def test_token_expiration():
    """Test that expired tokens are rejected."""
    token_data = {
        "tenant_id": "test-tenant-123",
        "user_id": "user-456"
    }
    
    # Create token that expires immediately
    expired_token = create_access_token(
        token_data,
        expires_delta=timedelta(seconds=-1)
    )
    
    with pytest.raises(HTTPException) as exc_info:
        verify_token(expired_token)
    
    assert exc_info.value.status_code == 401


def test_token_without_tenant_id():
    """Test that tokens without tenant_id are rejected."""
    token_data = {
        "user_id": "user-456"
        # Missing tenant_id
    }
    
    token = create_access_token(token_data)
    
    with pytest.raises(HTTPException) as exc_info:
        verify_token(token)
    
    assert exc_info.value.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
