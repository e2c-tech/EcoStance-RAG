"""
Test script for enhanced knowledge base management functionality
"""
import requests
import json

def test_kb_management():
    """Test the enhanced knowledge base management endpoints"""
    
    base_url = "http://127.0.0.1:8000/api/v1/manage"
    
    print("🧪 Testing Enhanced Knowledge Base Management")
    print("=" * 50)
    
    # Test 1: List all knowledge bases
    print("\n📝 Test 1: List Knowledge Bases")
    try:
        response = requests.get(f"{base_url}/knowledge-bases/")
        if response.status_code == 200:
            kbs = response.json()
            print(f"Found {len(kbs)} knowledge bases: {kbs}")
            
            if kbs:
                test_kb = kbs[0]
                print(f"Using '{test_kb}' for detailed testing...")
                
                # Test 2: Get knowledge base details
                print(f"\n📝 Test 2: Get Details for '{test_kb}'")
                response = requests.get(f"{base_url}/knowledge-bases/{test_kb}/details")
                if response.status_code == 200:
                    details = response.json()
                    print(f"✅ Knowledge Base Details:")
                    print(f"   - Name: {details.get('name')}")
                    print(f"   - Total Points: {details.get('total_points')}")
                    print(f"   - Files Count: {details.get('files_count')}")
                    print(f"   - Vector Size: {details.get('vector_size')}")
                    
                    files = details.get('files', [])
                    if files:
                        print(f"\n📁 Indexed Files:")
                        for i, file_info in enumerate(files[:5], 1):  # Show first 5 files
                            print(f"   {i}. {file_info.get('filename')}")
                            print(f"      - Chunks: {file_info.get('chunk_count')}")
                            print(f"      - Type: {file_info.get('file_type')}")
                            print(f"      - Characters: {file_info.get('total_characters')}")
                            print(f"      - Upload Date: {file_info.get('upload_date')}")
                        
                        if len(files) > 5:
                            print(f"   ... and {len(files) - 5} more files")
                    else:
                        print("   No files found in this knowledge base")
                else:
                    print(f"❌ Failed to get details: {response.status_code}")
                
                # Test 3: Get files list
                print(f"\n📝 Test 3: Get Files List for '{test_kb}'")
                response = requests.get(f"{base_url}/knowledge-bases/{test_kb}/files")
                if response.status_code == 200:
                    files_data = response.json()
                    files = files_data.get('files', [])
                    print(f"✅ Found {len(files)} files in '{test_kb}'")
                    
                    # Show available operations
                    if files:
                        sample_file = files[0]['filename']
                        print(f"\n🔧 Available Operations for '{sample_file}':")
                        print(f"   - Delete: DELETE {base_url}/knowledge-bases/{test_kb}/files/{sample_file}")
                        print(f"   - Reindex: POST {base_url}/knowledge-bases/{test_kb}/files/{sample_file}/reindex")
                else:
                    print(f"❌ Failed to get files: {response.status_code}")
            else:
                print("No knowledge bases found to test with")
        else:
            print(f"❌ Failed to list knowledge bases: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running. Please start with: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ Error: {e}")

def show_api_endpoints():
    """Show all available API endpoints for knowledge base management"""
    print("\n🔗 Available API Endpoints:")
    print("=" * 40)
    
    endpoints = [
        ("GET", "/api/v1/manage/knowledge-bases/", "List all knowledge bases"),
        ("GET", "/api/v1/manage/knowledge-bases/{kb_name}/details", "Get KB details with files"),
        ("GET", "/api/v1/manage/knowledge-bases/{kb_name}/files", "Get all files in KB"),
        ("DELETE", "/api/v1/manage/knowledge-bases/{kb_name}", "Delete entire KB"),
        ("DELETE", "/api/v1/manage/knowledge-bases/{kb_name}/files/{filename}", "Delete specific file"),
        ("POST", "/api/v1/manage/knowledge-bases/{kb_name}/files/{filename}/reindex", "Reindex specific file"),
    ]
    
    for method, endpoint, description in endpoints:
        print(f"{method:6} {endpoint:60} - {description}")

if __name__ == "__main__":
    print("🚀 Knowledge Base Management API Test")
    show_api_endpoints()
    test_kb_management()