"""
Test Phase 5 Backend Endpoints
Tests tenant profile, logo upload, preferences, and admin dashboard endpoints.
"""
import requests
import json
import os
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

# Test credentials (update with actual values)
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "adminpassword123"


def get_auth_token(email: str, password: str) -> str:
    """Get JWT token for authentication."""
    response = requests.post(
        f"{API_V1}/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Login failed: {response.status_code} - {response.text}")
        return None


def test_tenant_profile_update(token: str):
    """Test updating tenant profile."""
    print("\n=== Testing Tenant Profile Update ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "name": "Updated Company Name",
        "phone": "+1-555-0123"
    }
    
    response = requests.patch(
        f"{API_V1}/tenants/me/profile",
        headers=headers,
        json=data
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✓ Profile updated successfully")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"✗ Failed: {response.text}")


def test_logo_upload(token: str):
    """Test logo upload."""
    print("\n=== Testing Logo Upload ===")
    
    # Create a test image file
    test_logo_path = "test_logo.png"
    if not os.path.exists(test_logo_path):
        # Create a simple 1x1 PNG
        import base64
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        with open(test_logo_path, "wb") as f:
            f.write(png_data)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    with open(test_logo_path, "rb") as f:
        files = {"file": ("logo.png", f, "image/png")}
        response = requests.post(
            f"{API_V1}/tenants/me/logo",
            headers=headers,
            files=files
        )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✓ Logo uploaded successfully")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"✗ Failed: {response.text}")
    
    # Cleanup
    if os.path.exists(test_logo_path):
        os.remove(test_logo_path)


def test_get_logo(token: str):
    """Test getting logo."""
    print("\n=== Testing Get Logo ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_V1}/tenants/me/logo",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✓ Logo retrieved successfully")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Content-Length: {len(response.content)} bytes")
    elif response.status_code == 404:
        print(f"ℹ No logo uploaded yet")
    else:
        print(f"✗ Failed: {response.text}")


def test_preferences(token: str):
    """Test notification preferences."""
    print("\n=== Testing Notification Preferences ===")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get preferences
    print("\n1. Getting preferences...")
    response = requests.get(
        f"{API_V1}/tenants/me/preferences",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✓ Preferences retrieved")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"✗ Failed: {response.text}")
    
    # Update preferences
    print("\n2. Updating preferences...")
    data = {
        "email_alerts": True,
        "quota_warnings": True,
        "error_alerts": False,
        "weekly_reports": True,
        "webhook_url": "https://example.com/webhook"
    }
    
    response = requests.put(
        f"{API_V1}/tenants/me/preferences",
        headers=headers,
        json=data
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✓ Preferences updated")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"✗ Failed: {response.text}")


def test_admin_dashboard(admin_token: str):
    """Test admin dashboard endpoints."""
    print("\n=== Testing Admin Dashboard ===")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Dashboard summary
    print("\n1. Getting dashboard summary...")
    response = requests.get(
        f"{API_V1}/admin/dashboard/summary",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✓ Dashboard summary retrieved")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"✗ Failed: {response.text}")
    
    # Search tenants
    print("\n2. Searching tenants...")
    response = requests.get(
        f"{API_V1}/admin/tenants/search",
        headers=headers,
        params={"q": "test", "limit": 5}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✓ Tenant search successful")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"✗ Failed: {response.text}")


def test_admin_tenant_management(admin_token: str, tenant_id: str):
    """Test admin tenant management endpoints."""
    print("\n=== Testing Admin Tenant Management ===")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Get activity
    print("\n1. Getting tenant activity...")
    response = requests.get(
        f"{API_V1}/admin/tenants/{tenant_id}/activity",
        headers=headers,
        params={"days": 7}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✓ Activity retrieved")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"✗ Failed: {response.text}")
    
    # Update tier (be careful with this in production!)
    print("\n2. Testing tier update (dry run)...")
    print("ℹ Skipping actual tier update to avoid changing production data")
    # Uncomment to test:
    # response = requests.patch(
    #     f"{API_V1}/admin/tenants/{tenant_id}/tier",
    #     headers=headers,
    #     params={"tier": "professional"}
    # )


def main():
    """Run all Phase 5 backend tests."""
    print("=" * 60)
    print("Phase 5 Backend Endpoint Tests")
    print("=" * 60)
    
    # Get tokens
    print("\n=== Authentication ===")
    print("Getting user token...")
    user_token = get_auth_token(TEST_EMAIL, TEST_PASSWORD)
    
    if not user_token:
        print("✗ Failed to get user token. Please check credentials.")
        print("Update TEST_EMAIL and TEST_PASSWORD in the script.")
        return
    
    print("✓ User token obtained")
    
    print("\nGetting admin token...")
    admin_token = get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
    
    if not admin_token:
        print("⚠ Failed to get admin token. Admin tests will be skipped.")
        admin_token = None
    else:
        print("✓ Admin token obtained")
    
    # Run tests
    try:
        # Tenant profile tests
        test_tenant_profile_update(user_token)
        test_logo_upload(user_token)
        test_get_logo(user_token)
        test_preferences(user_token)
        
        # Admin tests (if admin token available)
        if admin_token:
            test_admin_dashboard(admin_token)
            
            # Get tenant ID for management tests
            response = requests.get(
                f"{API_V1}/tenants/me",
                headers={"Authorization": f"Bearer {user_token}"}
            )
            if response.status_code == 200:
                tenant_id = response.json()["id"]
                test_admin_tenant_management(admin_token, tenant_id)
        
        print("\n" + "=" * 60)
        print("✓ All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
