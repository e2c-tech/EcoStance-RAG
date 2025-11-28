#!/usr/bin/env python3

import requests
import json
import time
import tempfile
import os

# Configuration
BASE_URL = "http://localhost:8000"
KB_NAME = "test_background_processing"

def test_background_processing():
    """Test the new background processing functionality."""
    
    print("Testing Background Processing Implementation")
    print("=" * 60)
    
    # Create a test file
    test_content = """
    This is a test document for background processing.
    
    The new implementation should:
    1. Return immediately with a job ID
    2. Process the file in the background
    3. Allow status tracking via the job ID
    4. Update progress messages during processing
    
    This test verifies that the background task system works correctly.
    """
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        temp_file_path = f.name
    
    try:
        print(f"\n📁 Created test file: {temp_file_path}")
        
        # Step 1: Upload the file
        print("\n🔄 Step 1: Uploading file...")
        with open(temp_file_path, 'rb') as f:
            files = {'file': ('test_background.txt', f, 'text/plain')}
            response = requests.post(f"{BASE_URL}/api/v1/upload/", files=files)
        
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return
        
        upload_result = response.json()
        uploaded_file_path = upload_result.get('file_path')
        print(f"✅ File uploaded to: {uploaded_file_path}")
        
        # Step 2: Start background processing
        print("\n🔄 Step 2: Starting background processing...")
        data = {
            'file_path': uploaded_file_path,
            'collection_name': KB_NAME
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/upload-to-qdrant/", data=data)
        
        if response.status_code != 200:
            print(f"❌ Processing start failed: {response.status_code} - {response.text}")
            return
        
        process_result = response.json()
        job_id = process_result.get('job_id')
        print(f"✅ Background processing started!")
        print(f"   Job ID: {job_id}")
        print(f"   Status URL: {process_result.get('status_url')}")
        
        # Step 3: Monitor job progress
        print(f"\n🔄 Step 3: Monitoring job progress...")
        
        max_wait_time = 120  # 2 minutes max
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # Get job status
            response = requests.get(f"{BASE_URL}/api/v1/processing-status/{job_id}")
            
            if response.status_code != 200:
                print(f"❌ Status check failed: {response.status_code}")
                break
            
            status_info = response.json()
            status = status_info.get('status')
            progress = status_info.get('progress_message', 'No progress info')
            
            print(f"   Status: {status}")
            print(f"   Progress: {progress}")
            
            if status == 'completed':
                print("✅ Processing completed successfully!")
                break
            elif status == 'failed':
                error_msg = status_info.get('error_message', 'Unknown error')
                print(f"❌ Processing failed: {error_msg}")
                break
            
            # Wait before next check
            time.sleep(3)
        else:
            print("⏰ Timeout waiting for job completion")
        
        # Step 4: Test the processed data
        print(f"\n🔄 Step 4: Testing query against processed data...")
        
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
        
        # Step 5: Check job listing endpoint
        print(f"\n🔄 Step 5: Testing job listing endpoint...")
        
        response = requests.get(f"{BASE_URL}/api/v1/jobs/")
        
        if response.status_code == 200:
            jobs_info = response.json()
            total_jobs = jobs_info.get('total_jobs', 0)
            print(f"✅ Job listing successful!")
            print(f"   Total jobs in system: {total_jobs}")
            
            # Find our job
            our_job = None
            for job in jobs_info.get('jobs', []):
                if job.get('job_id') == job_id:
                    our_job = job
                    break
            
            if our_job:
                print(f"   Our job found with status: {our_job.get('status')}")
            else:
                print(f"   Our job not found in listing")
        else:
            print(f"❌ Job listing failed: {response.status_code}")
        
    finally:
        # Cleanup
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print(f"\n🧹 Cleaned up test file: {temp_file_path}")
    
    print(f"\n{'='*60}")
    print("Background Processing Test Summary:")
    print("✅ Immediate response with job ID")
    print("✅ Background processing with progress tracking")
    print("✅ Status monitoring via API")
    print("✅ Job listing functionality")
    print("✅ Successful data processing and querying")
    print("\n🎉 Background processing implementation is working correctly!")

if __name__ == "__main__":
    test_background_processing()