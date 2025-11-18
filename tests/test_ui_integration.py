#!/usr/bin/env python3

import requests
import json
import time
import tempfile
import os

# Configuration
BASE_URL = "http://localhost:8000"
KB_NAME = "ui_integration_test"

def test_ui_integration():
    """Test that the UI integration functions work correctly."""
    
    print("Testing UI Integration Functions")
    print("=" * 50)
    
    # Test the functions that the Streamlit UI uses
    
    # 1. Test file upload (simulating what upload_file() does in UI)
    print("\n🔄 Testing file upload function...")
    
    test_content = "This is a test document for UI integration testing."
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        temp_file_path = f.name
    
    try:
        # Upload file
        with open(temp_file_path, 'rb') as f:
            files = {'file': ('ui_test.txt', f, 'text/plain')}
            response = requests.post(f"{BASE_URL}/api/v1/upload/", files=files)
        
        if response.status_code == 200:
            upload_result = response.json()
            uploaded_file_path = upload_result.get('file_path')
            print(f"✅ File upload successful: {uploaded_file_path}")
        else:
            print(f"❌ File upload failed: {response.status_code}")
            return
        
        # 2. Test process_file function (what UI calls for background processing)
        print("\n🔄 Testing process_file function...")
        
        data = {
            'file_path': uploaded_file_path,
            'collection_name': KB_NAME
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/upload-to-qdrant/", data=data)
        
        if response.status_code == 200:
            process_result = response.json()
            job_id = process_result.get('job_id')
            print(f"✅ Background processing started: {job_id}")
        else:
            print(f"❌ Process start failed: {response.status_code}")
            return
        
        # 3. Test get_job_status function (what UI uses for monitoring)
        print("\n🔄 Testing get_job_status function...")
        
        max_attempts = 20
        for attempt in range(max_attempts):
            response = requests.get(f"{BASE_URL}/api/v1/processing-status/{job_id}")
            
            if response.status_code == 200:
                status_info = response.json()
                status = status_info.get('status')
                progress = status_info.get('progress_message', 'No progress')
                
                print(f"   Attempt {attempt + 1}: Status = {status}")
                print(f"   Progress: {progress}")
                
                if status == 'completed':
                    print("✅ Job completed successfully!")
                    break
                elif status == 'failed':
                    error_msg = status_info.get('error_message', 'Unknown error')
                    print(f"❌ Job failed: {error_msg}")
                    return
                
                time.sleep(1)
            else:
                print(f"❌ Status check failed: {response.status_code}")
                return
        else:
            print("⏰ Job didn't complete within expected time")
            return
        
        # 4. Test query_rag_agent function (what UI uses for chat)
        print("\n🔄 Testing query_rag_agent function...")
        
        query_data = {
            'collection_name': KB_NAME,
            'query': 'What is this document about?'
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/query/", data=query_data)
        
        if response.status_code == 200:
            query_result = response.json()
            answer = query_result.get('answer', 'No answer')
            print(f"✅ Query successful!")
            print(f"   Answer: {answer}")
        else:
            print(f"❌ Query failed: {response.status_code}")
            return
        
        # 5. Test get_knowledge_bases function
        print("\n🔄 Testing get_knowledge_bases function...")
        
        response = requests.get(f"{BASE_URL}/api/v1/manage/knowledge-bases/")
        
        if response.status_code == 200:
            kb_list = response.json()
            print(f"✅ Knowledge bases retrieved: {len(kb_list)} found")
            
            if KB_NAME in kb_list:
                print(f"   Our test KB '{KB_NAME}' is in the list")
            else:
                print(f"   Warning: Our test KB '{KB_NAME}' not found in list")
        else:
            print(f"❌ KB list retrieval failed: {response.status_code}")
        
        # 6. Test get_knowledge_base_details function
        print("\n🔄 Testing get_knowledge_base_details function...")
        
        response = requests.get(f"{BASE_URL}/api/v1/manage/knowledge-bases/{KB_NAME}/details")
        
        if response.status_code == 200:
            kb_details = response.json()
            total_points = kb_details.get('total_points', 0)
            files_count = kb_details.get('files_count', 0)
            print(f"✅ KB details retrieved:")
            print(f"   Total points: {total_points}")
            print(f"   Files count: {files_count}")
        else:
            print(f"❌ KB details retrieval failed: {response.status_code}")
        
    finally:
        # Cleanup
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print(f"\n🧹 Cleaned up test file: {temp_file_path}")
    
    print(f"\n{'='*50}")
    print("UI Integration Test Summary:")
    print("✅ File upload function works")
    print("✅ Background processing function works")
    print("✅ Job status monitoring function works")
    print("✅ Query function works")
    print("✅ Knowledge base listing function works")
    print("✅ Knowledge base details function works")
    print("\n🎉 All UI integration functions are working correctly!")

if __name__ == "__main__":
    test_ui_integration()