"""
Test script for email/password authentication
"""
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_email_password_auth():
    print("=" * 60)
    print("Testing Email/Password Authentication")
    print("=" * 60)
    
    # 1. Register tenant with password
    print("\n1. Registering tenant with email and password...")
    response = requests.post(
        f"{BASE_URL}/tenants/register",
        json={
            "name": "Test Auth Company",
            "email": "auth@testcompany.com",
            "password": "SecurePassword123!",
            "billing_tier": "free"
        }
    )
    
    if response.status_code == 200:
        tenant = response.json()
        print(f"✅ Tenant registered successfully!")
        print(f"   Email: {tenant['email']}")
        print(f"   Tenant ID: {tenant['id']}")
        print(f"   Slug: {tenant['slug']}")
    else:
        print(f"❌ Registration failed: {response.status_code}")
        print(f"   Error: {response.json()}")
        return
    
    # 2. Login with email and password
    print("\n2. Logging in with email and password...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "auth@testcompany.com",
            "password": "SecurePassword123!"
        }
    )
    
    if response.status_code == 200:
        tokens = response.json()
        print(f"✅ Login successful!")
        print(f"   Access Token: {tokens['access_token'][:40]}...")
        print(f"   Tenant ID: {tokens['tenant_id']}")
        access_token = tokens['access_token']
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"   Error: {response.json()}")
        return
    
    # 3. Test wrong password
    print("\n3. Testing with wrong password...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "auth@testcompany.com",
            "password": "WrongPassword123!"
        }
    )
    
    if response.status_code == 401:
        print(f"✅ Correctly rejected wrong password")
    else:
        print(f"⚠️ Unexpected response: {response.status_code}")
    
    # 4. Test authenticated endpoint
    print("\n4. Testing authenticated endpoint...")
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        f"{BASE_URL}/tenants/me",
        headers=headers
    )
    
    if response.status_code == 200:
        tenant_info = response.json()
        print(f"✅ Successfully accessed authenticated endpoint")
        print(f"   Tenant Name: {tenant_info['name']}")
        print(f"   Email: {tenant_info['email']}")
    else:
        print(f"❌ Failed to access endpoint: {response.status_code}")
    
    # 5. Test backward compatibility (tenant_id login)
    print("\n5. Testing backward compatibility (tenant_id login)...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "tenant_id": tenant['id']
        }
    )
    
    if response.status_code == 200:
        print(f"✅ Tenant ID login still works (backward compatible)")
    else:
        print(f"⚠️ Tenant ID login failed: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_email_password_auth()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
