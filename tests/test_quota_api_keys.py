"""
Test script for Quota Status and API Keys endpoints.
Tests the bug fix for passing Tenant object instead of tenant_id.
"""
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TEST_TENANT_ID = "test-tenant-001"

def get_auth_token():
    """Get authentication token for testing."""
    # First, try to register/login
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!",
            "company_name": "Test Company"
        }
    )
    
    if response.status_code == 201:
        data = response.json()
        return data.get("access_token")
    
    # If registration fails, try login
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    
    raise Exception(f"Failed to authenticate: {response.text}")


def test_quota_status(token):
    """Test GET /api/v1/quota/status endpoint."""
    print("\n=== Testing Quota Status Endpoint ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/quota/status", headers=headers)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✓ Quota status retrieved successfully")
        print(json.dumps(data, indent=2))
        
        # Verify response structure
        assert "storage" in data, "Missing 'storage' field"
        assert "queries" in data, "Missing 'queries' field"
        assert "documents" in data, "Missing 'documents' field"
        assert "connections" in data, "Missing 'connections' field"
        assert "api_calls" in data, "Missing 'api_calls' field"
        
        # Verify storage fields
        storage = data["storage"]
        assert "limit_bytes" in storage
        assert "used_bytes" in storage
        assert "available_bytes" in storage
        assert "usage_percent" in storage
        
        # Verify queries fields
        queries = data["queries"]
        assert "daily_limit" in queries
        assert "daily_used" in queries
        assert "monthly_limit" in queries
        assert "monthly_used" in queries
        assert "daily_percent" in queries
        assert "monthly_percent" in queries
        
        print("✓ All required fields present")
        return True
    else:
        print(f"✗ Failed: {response.text}")
        return False


def test_list_api_keys(token):
    """Test GET /api/v1/api-keys/ endpoint."""
    print("\n=== Testing List API Keys Endpoint ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/api-keys/", headers=headers)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ API keys retrieved successfully ({len(data)} keys)")
        print(json.dumps(data, indent=2))
        return True
    else:
        print(f"✗ Failed: {response.text}")
        return False


def test_create_api_key(token):
    """Test POST /api/v1/api-keys/ endpoint."""
    print("\n=== Testing Create API Key Endpoint ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": f"Test Key {datetime.now().strftime('%Y%m%d%H%M%S')}",
        "expires_in_days": 30,
        "permissions": ["read", "write"]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/api-keys/",
        headers=headers,
        json=payload
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 201:
        data = response.json()
        print("✓ API key created successfully")
        print(f"Key ID: {data.get('id')}")
        print(f"Key Prefix: {data.get('key_prefix')}")
        print(f"Full Key: {data.get('api_key')[:20]}...")
        print(f"Message: {data.get('message')}")
        
        # Verify response structure
        assert "id" in data
        assert "api_key" in data
        assert "key_prefix" in data
        assert "name" in data
        assert "permissions" in data
        assert "message" in data
        
        print("✓ All required fields present")
        return data.get("id")
    else:
        print(f"✗ Failed: {response.text}")
        return None


def test_revoke_api_key(token, key_id):
    """Test DELETE /api/v1/api-keys/{key_id} endpoint."""
    print("\n=== Testing Revoke API Key Endpoint ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(
        f"{BASE_URL}/api/v1/api-keys/{key_id}",
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✓ API key revoked successfully")
        print(json.dumps(data, indent=2))
        return True
    else:
        print(f"✗ Failed: {response.text}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Quota Status & API Keys Endpoints Test")
    print("=" * 60)
    
    try:
        # Get authentication token
        print("\n--- Authenticating ---")
        token = get_auth_token()
        print(f"✓ Authentication successful")
        
        # Test quota status
        quota_success = test_quota_status(token)
        
        # Test list API keys
        list_success = test_list_api_keys(token)
        
        # Test create API key
        key_id = test_create_api_key(token)
        
        # Test revoke API key (if we created one)
        revoke_success = False
        if key_id:
            revoke_success = test_revoke_api_key(token, key_id)
        
        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"Quota Status:    {'✓ PASS' if quota_success else '✗ FAIL'}")
        print(f"List API Keys:   {'✓ PASS' if list_success else '✗ FAIL'}")
        print(f"Create API Key:  {'✓ PASS' if key_id else '✗ FAIL'}")
        print(f"Revoke API Key:  {'✓ PASS' if revoke_success else '✗ FAIL'}")
        
        all_passed = quota_success and list_success and key_id and revoke_success
        print("\n" + ("=" * 60))
        if all_passed:
            print("✓ ALL TESTS PASSED")
        else:
            print("✗ SOME TESTS FAILED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
