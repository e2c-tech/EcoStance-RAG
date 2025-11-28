"""
Test script to verify AI Agent integration
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_agent_chat():
    """Test the agent chat endpoint"""
    print("=" * 60)
    print("Testing AI Agent Chat Endpoint")
    print("=" * 60)
    
    # Test 1: Simple greeting
    print("\n1. Testing simple greeting...")
    response = requests.post(
        f"{BASE_URL}/api/v1/beta/agent/chat",
        json={
            "message": "Hello, who are you?"
        }
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data['response'][:200]}...")
        print(f"Session ID: {data['session_id']}")
    else:
        print(f"Error: {response.text}")
    
    # Test 2: Track shipment (if you have test data)
    print("\n2. Testing shipment tracking...")
    response = requests.post(
        f"{BASE_URL}/api/v1/beta/agent/chat",
        json={
            "message": "Track QS250001"
        }
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data['response'][:200]}...")
    else:
        print(f"Error: {response.text}")
    
    # Test 3: Knowledge base query
    print("\n3. Testing knowledge base query...")
    response = requests.post(
        f"{BASE_URL}/api/v1/beta/agent/chat",
        json={
            "message": "What are your shipping rates?"
        }
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data['response'][:200]}...")
    else:
        print(f"Error: {response.text}")

def test_agent_history():
    """Test conversation history endpoint"""
    print("\n" + "=" * 60)
    print("Testing Conversation History")
    print("=" * 60)
    
    # First, create a conversation
    response = requests.post(
        f"{BASE_URL}/api/v1/beta/agent/chat",
        json={
            "session_id": "test-session-123",
            "message": "Hello"
        }
    )
    
    if response.status_code == 200:
        # Get history
        response = requests.get(
            f"{BASE_URL}/api/v1/beta/agent/history/test-session-123"
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Messages in history: {len(data['messages'])}")
            for msg in data['messages']:
                print(f"  - {msg['role']}: {msg['content'][:50]}...")
        else:
            print(f"Error: {response.text}")

def test_agent_reset():
    """Test conversation reset endpoint"""
    print("\n" + "=" * 60)
    print("Testing Conversation Reset")
    print("=" * 60)
    
    response = requests.post(
        f"{BASE_URL}/api/v1/beta/agent/reset/test-session-123"
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Message: {data['message']}")
        print(f"Success: {data['success']}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    print("\n🤖 AI Agent Integration Test\n")
    
    try:
        test_agent_chat()
        test_agent_history()
        test_agent_reset()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        print("\nTo use the agent in your application:")
        print("1. Start the server: python run_app.py")
        print("2. Visit: http://localhost:8000/docs")
        print("3. Look for '13. AI Agent (Beta)' section")
        print("4. Try the /api/v1/beta/agent/chat endpoint")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the server")
        print("Please make sure the server is running:")
        print("  python run_app.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
