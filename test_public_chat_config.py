"""
Test public chat config endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

# First, login to get a token
print("1. Logging in...")
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={
        "email": "admin@example.com",
        "password": "admin123"
    }
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["access_token"]
print(f"✅ Login successful, got token")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Test get config
print("\n2. Getting admin config...")
config_response = requests.get(
    f"{BASE_URL}/api/v1/admin/public-chat/config",
    headers=headers
)

print(f"Status: {config_response.status_code}")
if config_response.status_code == 200:
    print("✅ Config retrieved successfully")
    print(json.dumps(config_response.json(), indent=2))
else:
    print(f"❌ Failed to get config")
    print(f"Response: {config_response.text}")

# Test get available KBs
print("\n3. Getting available KBs...")
kb_response = requests.get(
    f"{BASE_URL}/api/v1/admin/public-chat/available-kbs",
    headers=headers
)

print(f"Status: {kb_response.status_code}")
if kb_response.status_code == 200:
    print("✅ KBs retrieved successfully")
    print(json.dumps(kb_response.json(), indent=2))
else:
    print(f"❌ Failed to get KBs")
    print(f"Response: {kb_response.text}")
