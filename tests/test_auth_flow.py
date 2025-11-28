"""
Test script to verify user registration and login flow.
Run this after starting the FastAPI server.
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_registration_and_login():
    """Test the complete registration and login flow."""
    
    print("=" * 60)
    print("Testing User Registration and Login Flow")
    print("=" * 60)
    
    # Test 1: Register a new tenant
    print("\n1. Testing Tenant Registration...")
    print("-" * 60)
    
    registration_data = {
        "name": "Test Company",
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "phone": "+1-555-0123",
        "billing_tier": "free"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/tenants/register",
            json=registration_data
        )
        
        if response.status_code == 200:
            tenant = response.json()
            print("✅ Registration successful!")
            print(f"   Tenant ID: {tenant['id']}")
            print(f"   Name: {tenant['name']}")
            print(f"   Email: {tenant['email']}")
            print(f"   Slug: {tenant['slug']}")
            print(f"   Billing Tier: {tenant['billing_tier']}")
            tenant_id = tenant['id']
        elif response.status_code == 400:
            print("⚠️  Email already registered (this is expected if running multiple times)")
            print("   Continuing with login test...")
            tenant_id = None
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return False
    
    # Test 2: Login with email and password
    print("\n2. Testing Login with Email/Password...")
    print("-" * 60)
    
    login_data = {
        "email": "test@example.com",
        "password": "SecurePassword123!"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json=login_data
        )
        
        if response.status_code == 200:
            tokens = response.json()
            print("✅ Login successful!")
            print(f"   Access Token: {tokens['access_token'][:50]}...")
            print(f"   Refresh Token: {tokens['refresh_token'][:50]}...")
            print(f"   Token Type: {tokens['token_type']}")
            print(f"   Tenant ID: {tokens['tenant_id']}")
            access_token = tokens['access_token']
            refresh_token = tokens['refresh_token']
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False
    
    # Test 3: Verify token
    print("\n3. Testing Token Verification...")
    print("-" * 60)
    
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            f"{BASE_URL}/auth/verify",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Token verification successful!")
            print(f"   Valid: {result['valid']}")
            print(f"   Message: {result['message']}")
        else:
            print(f"❌ Token verification failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Token verification error: {e}")
        return False
    
    # Test 4: Get current tenant info
    print("\n4. Testing Get Current Tenant...")
    print("-" * 60)
    
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            f"{BASE_URL}/tenants/me",
            headers=headers
        )
        
        if response.status_code == 200:
            tenant = response.json()
            print("✅ Get current tenant successful!")
            print(f"   Tenant ID: {tenant['id']}")
            print(f"   Name: {tenant['name']}")
            print(f"   Email: {tenant['email']}")
            print(f"   Active: {tenant['is_active']}")
            print(f"   Billing Tier: {tenant['billing_tier']}")
        else:
            print(f"❌ Get current tenant failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Get current tenant error: {e}")
        return False
    
    # Test 5: Refresh token
    print("\n5. Testing Token Refresh...")
    print("-" * 60)
    
    try:
        refresh_data = {"refresh_token": refresh_token}
        response = requests.post(
            f"{BASE_URL}/auth/refresh",
            json=refresh_data
        )
        
        if response.status_code == 200:
            new_tokens = response.json()
            print("✅ Token refresh successful!")
            print(f"   New Access Token: {new_tokens['access_token'][:50]}...")
            print(f"   Token Type: {new_tokens['token_type']}")
        else:
            print(f"❌ Token refresh failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Token refresh error: {e}")
        return False
    
    # Test 6: Test with tenant_id (backward compatibility)
    print("\n6. Testing Login with Tenant ID (Backward Compatibility)...")
    print("-" * 60)
    
    if tenant_id:
        try:
            login_data = {"tenant_id": tenant_id}
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json=login_data
            )
            
            if response.status_code == 200:
                tokens = response.json()
                print("✅ Tenant ID login successful!")
                print(f"   Access Token: {tokens['access_token'][:50]}...")
                print(f"   Tenant ID: {tokens['tenant_id']}")
            else:
                print(f"❌ Tenant ID login failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Tenant ID login error: {e}")
    else:
        print("⏭️  Skipping (no tenant_id from registration)")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("=" * 60)
    print("\nAuthentication system is working correctly!")
    print("\nYou can now:")
    print("  1. Register new tenants via POST /api/v1/tenants/register")
    print("  2. Login with email/password via POST /api/v1/auth/login")
    print("  3. Use the access token in Authorization header")
    print("  4. Refresh tokens via POST /api/v1/auth/refresh")
    
    return True


if __name__ == "__main__":
    print("\n🚀 Starting authentication flow test...")
    print("📝 Make sure the FastAPI server is running on http://127.0.0.1:8000\n")
    
    try:
        # Quick health check
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running!\n")
            test_registration_and_login()
        else:
            print("❌ Server health check failed")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Please start the FastAPI server first:")
        print("   uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ Error: {e}")
