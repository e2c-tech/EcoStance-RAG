"""
Test Public Chat API Endpoints
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Test credentials (update with your actual credentials)
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"


def get_auth_token():
    """Get authentication token for admin user."""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Login failed: {response.status_code} - {response.text}")
        return None


def test_public_chat_config():
    """Test getting public chat configuration (public endpoint)."""
    print("\n=== Test: Get Public Chat Config ===")
    response = requests.get(f"{BASE_URL}/api/v1/public-chat/config")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_admin_get_config(token):
    """Test getting admin configuration."""
    print("\n=== Test: Get Admin Config ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/v1/admin/public-chat/config",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200, response.json()


def test_admin_update_config(token, kb_ids):
    """Test updating admin configuration."""
    print("\n=== Test: Update Admin Config ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    config_data = {
        "enabled": True,
        "allowed_kbs": kb_ids[:1] if kb_ids else [],  # Use first KB
        "welcome_message": "Welcome! How can I assist you today?",
        "suggested_questions": [
            "What services do you offer?",
            "How can I contact support?",
            "What are your business hours?"
        ],
        "branding": {
            "logo": "https://example.com/logo.png",
            "primary_color": "#0066CC",
            "company_name": "Test Company"
        },
        "rate_limit": {
            "queries_per_minute": 10,
            "max_messages_per_session": 50
        },
        "features": {
            "show_sources": True,
            "allow_feedback": True,
            "show_suggested_questions": True
        }
    }
    
    response = requests.put(
        f"{BASE_URL}/api/v1/admin/public-chat/config",
        headers=headers,
        json=config_data
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_get_available_kbs(token):
    """Test getting available knowledge bases."""
    print("\n=== Test: Get Available Knowledge Bases ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/v1/admin/public-chat/available-kbs",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        kb_ids = [kb["id"] for kb in data.get("knowledge_bases", [])]
        return True, kb_ids
    else:
        print(f"Response: {response.text}")
        return False, []


def test_public_chat_query():
    """Test sending a query to public chat."""
    print("\n=== Test: Public Chat Query ===")
    
    session_id = f"test-session-{int(time.time())}"
    
    query_data = {
        "session_id": session_id,
        "query": "What services do you offer?",
        "conversation_history": []
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/public-chat/query",
        json=query_data
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        return True, session_id, response.json()
    return False, session_id, None


def test_submit_feedback(session_id, message_id):
    """Test submitting feedback."""
    print("\n=== Test: Submit Feedback ===")
    
    feedback_data = {
        "session_id": session_id,
        "message_id": message_id,
        "feedback_type": "positive",
        "comment": "Very helpful!"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/public-chat/feedback",
        json=feedback_data
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_get_analytics(token):
    """Test getting analytics."""
    print("\n=== Test: Get Analytics ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/v1/admin/public-chat/analytics?days=30",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_get_session_details(token, session_id):
    """Test getting session details."""
    print("\n=== Test: Get Session Details ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/v1/admin/public-chat/sessions/{session_id}",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("PUBLIC CHAT API TESTS")
    print("=" * 60)
    
    # Get auth token
    print("\n=== Getting Authentication Token ===")
    token = get_auth_token()
    if not token:
        print("✗ Failed to get authentication token. Please check credentials.")
        return
    print("✓ Authentication successful")
    
    # Test 1: Get available KBs
    success, kb_ids = test_get_available_kbs(token)
    if not success:
        print("✗ Failed to get available KBs")
        return
    print(f"✓ Found {len(kb_ids)} knowledge bases")
    
    if not kb_ids:
        print("\n⚠ No knowledge bases found. Please create a KB first.")
        print("Continuing with other tests...")
    
    # Test 2: Get admin config
    success, config = test_admin_get_config(token)
    if success:
        print("✓ Admin config retrieved")
    else:
        print("✗ Failed to get admin config")
    
    # Test 3: Update admin config
    if kb_ids:
        success = test_admin_update_config(token, kb_ids)
        if success:
            print("✓ Admin config updated")
        else:
            print("✗ Failed to update admin config")
    
    # Test 4: Get public config
    success = test_public_chat_config()
    if success:
        print("✓ Public config retrieved")
    else:
        print("✗ Failed to get public config")
    
    # Test 5: Send query (only if enabled and KBs configured)
    if kb_ids:
        success, session_id, response_data = test_public_chat_query()
        if success:
            print("✓ Query sent successfully")
            
            # Test 6: Submit feedback
            # Note: We need a valid message_id from the response
            # For now, we'll skip this if the response doesn't have it
            print("\n⚠ Feedback test skipped (requires valid message_id)")
        else:
            print("✗ Failed to send query")
            session_id = None
    else:
        print("\n⚠ Query test skipped (no KBs configured)")
        session_id = None
    
    # Test 7: Get analytics
    success = test_get_analytics(token)
    if success:
        print("✓ Analytics retrieved")
    else:
        print("✗ Failed to get analytics")
    
    # Test 8: Get session details (if we have a session)
    if session_id:
        success = test_get_session_details(token, session_id)
        if success:
            print("✓ Session details retrieved")
        else:
            print("✗ Failed to get session details")
    
    print("\n" + "=" * 60)
    print("TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
