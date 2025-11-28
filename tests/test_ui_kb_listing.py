"""
Test script to verify KB listing works for UI
"""
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_ui_flow():
    print("=" * 60)
    print("Testing UI KB Listing Flow")
    print("=" * 60)
    
    # 1. Login
    print("\n1. Login as default-tenant...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"tenant_id": "default-tenant"}
    )
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"✅ Logged in successfully")
    
    # 2. List KBs (what UI calls)
    print("\n2. Listing knowledge bases (UI call)...")
    response = requests.get(
        f"{BASE_URL}/manage/knowledge-bases/",
        headers=headers
    )
    kbs = response.json()
    print(f"✅ API returned: {kbs}")
    
    if not kbs:
        print("⚠️  No KBs found! This is why UI shows empty.")
        print("\nDebugging...")
        
        # Check what's in kbs.json
        import json
        with open("kbs.json", "r") as f:
            all_kbs = json.load(f)
        print(f"   kbs.json contains: {all_kbs}")
        
        # Check parsing
        from app.services.qdrant_service import get_qdrant_client
        from app.services.tenant_service import get_tenant_service
        
        client = get_qdrant_client()
        ts = get_tenant_service(client)
        
        print("\n   Parsing each collection:")
        for kb in all_kbs:
            parsed = ts.parse_collection_name(kb)
            if parsed:
                matches = parsed["tenant_id"] == ts._sanitize_name("default-tenant")
                print(f"   - {kb}")
                print(f"     Parsed: {parsed}")
                print(f"     Matches tenant: {matches}")
            else:
                print(f"   - {kb} (not tenant format)")
    else:
        print(f"\n✅ SUCCESS! UI should show {len(kbs)} KB(s): {kbs}")
        
        # Test getting details for first KB
        if kbs:
            kb_name = kbs[0]
            print(f"\n3. Getting details for '{kb_name}'...")
            response = requests.get(
                f"{BASE_URL}/manage/knowledge-bases/{kb_name}/details",
                headers=headers
            )
            details = response.json()
            print(f"✅ Details retrieved:")
            print(f"   - Vectors: {details.get('vectors_count')}")
            print(f"   - Files: {details.get('files_count')}")
            
            # Test getting files
            print(f"\n4. Getting files in '{kb_name}'...")
            response = requests.get(
                f"{BASE_URL}/manage/knowledge-bases/{kb_name}/files",
                headers=headers
            )
            files_data = response.json()
            files = files_data.get('files', [])
            print(f"✅ Found {len(files)} file(s):")
            for file in files:
                print(f"   - {file.get('filename')}: {file.get('chunk_count')} chunks")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_ui_flow()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
