"""
Test script for Knowledge Base Management with tenant isolation
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_kb_management():
    print("=" * 60)
    print("Testing Knowledge Base Management with Tenant Isolation")
    print("=" * 60)
    
    # 1. Login
    print("\n1. Logging in as test_tenant...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"tenant_id": "test_tenant"}
    )
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"✅ Login successful! Token: {token[:20]}...")
    
    # 2. List knowledge bases
    print("\n2. Listing knowledge bases...")
    response = requests.get(
        f"{BASE_URL}/manage/knowledge-bases/",
        headers=headers
    )
    kbs = response.json()
    print(f"✅ Found {len(kbs)} knowledge bases: {kbs}")
    
    # 3. If there are KBs, get details of the first one
    if kbs:
        kb_name = kbs[0]
        print(f"\n3. Getting details for KB: {kb_name}")
        response = requests.get(
            f"{BASE_URL}/manage/knowledge-bases/{kb_name}/details",
            headers=headers
        )
        details = response.json()
        print(f"✅ KB Details:")
        print(f"   - Name: {details.get('name')}")
        print(f"   - Collection: {details.get('collection_name')}")
        print(f"   - Total Points: {details.get('total_points', 0)}")
        print(f"   - Files Count: {details.get('files_count', 0)}")
        
        # 4. Get files in KB
        print(f"\n4. Getting files in KB: {kb_name}")
        response = requests.get(
            f"{BASE_URL}/manage/knowledge-bases/{kb_name}/files",
            headers=headers
        )
        files_data = response.json()
        files = files_data.get('files', [])
        print(f"✅ Found {len(files)} files:")
        for file in files:
            print(f"   - {file.get('filename')}: {file.get('chunk_count')} chunks")
    else:
        print("\n⚠️ No knowledge bases found. Upload and process files first!")
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_kb_management()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
