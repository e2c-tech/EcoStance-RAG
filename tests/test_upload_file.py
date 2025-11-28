"""
Test script to upload a file and process it to a KB
"""
import requests
import io

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_upload_and_process():
    print("=" * 60)
    print("Testing File Upload and Processing")
    print("=" * 60)
    
    # 1. Login
    print("\n1. Logging in...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"tenant_id": "default-tenant"}
    )
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Logged in")
    
    # 2. Create a test file
    print("\n2. Creating test file...")
    test_content = """
    # Test Document
    
    This is a test document for the knowledge base.
    
    ## Section 1
    This section contains information about testing.
    
    ## Section 2
    This section contains more test data.
    
    ## Section 3
    Final section with additional content.
    """
    
    file_data = io.BytesIO(test_content.encode('utf-8'))
    files = {"file": ("test_document.txt", file_data, "text/plain")}
    
    # 3. Upload file
    print("\n3. Uploading file...")
    response = requests.post(
        f"{BASE_URL}/upload/",
        files=files,
        headers=headers
    )
    response.raise_for_status()
    upload_result = response.json()
    print(f"✅ File uploaded: {upload_result['filename']}")
    print(f"   Path: {upload_result['file_path']}")
    
    # 4. Process to Qdrant
    print("\n4. Processing to knowledge base 'demo'...")
    data = {
        "file_path": upload_result['file_path'],
        "kb_name": "demo"
    }
    response = requests.post(
        f"{BASE_URL}/upload-to-qdrant/",
        data=data,
        headers=headers
    )
    response.raise_for_status()
    process_result = response.json()
    print(f"✅ Processing started!")
    print(f"   Job ID: {process_result['job_id']}")
    print(f"   Collection: {process_result['collection_name']}")
    
    # 5. Wait a bit for processing
    print("\n5. Waiting for processing to complete...")
    import time
    time.sleep(3)
    
    # 6. Check KB files
    print("\n6. Checking KB files...")
    response = requests.get(
        f"{BASE_URL}/manage/knowledge-bases/demo/files",
        headers=headers
    )
    files_data = response.json()
    files = files_data.get('files', [])
    print(f"✅ Found {len(files)} file(s) in KB:")
    for file in files:
        print(f"   - {file['filename']}: {file['chunk_count']} chunks")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_upload_and_process()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
