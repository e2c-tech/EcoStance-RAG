"""
Test script for stateful RAG functionality using HTTP requests
"""
import requests
import json

def make_query(query, chat_history=None):
    """Make a query to the RAG API"""
    if chat_history is None:
        chat_history = []
    
    url = "http://127.0.0.1:8000/api/v1/query/"
    data = {
        "collection_name": "ecostance-demo",
        "query": query,
        "chat_history": chat_history
    }
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return response.json()["answer"]
        else:
            return f"Error: {response.status_code} - {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: Server not running. Please start the server with 'uvicorn app.main:app --reload'"
    except Exception as e:
        return f"Error: {str(e)}"

def test_stateful_conversation():
    """Test the stateful RAG with a multi-turn conversation"""
    
    print("🧪 Testing Stateful RAG Conversation")
    print("=" * 50)
    
    # Test 1: Initial query (no history)
    print("\n📝 Test 1: Initial Query (No History)")
    query1 = "Do you accept international payments?"
    
    answer1 = make_query(query1, [])
    print(f"Q: {query1}")
    print(f"A: {answer1}")
    
    if "Error:" in answer1:
        print("❌ Test 1 failed - Server issue")
        return
    print("✅ Test 1 passed - Got response")
    
    # Test 2: Follow-up query with history
    print("\n📝 Test 2: Follow-up Query (With History)")
    query2 = "What about refunds?"
    chat_history2 = [query1, answer1]
    
    answer2 = make_query(query2, chat_history2)
    print(f"Q: {query2}")
    print(f"A: {answer2}")
    
    if "Error:" in answer2:
        print("❌ Test 2 failed - Server issue")
        return
    print("✅ Test 2 passed - Got response with history")
    
    # Test 3: Another follow-up with extended history
    print("\n📝 Test 3: Extended Conversation")
    query3 = "How long does that take?"
    chat_history3 = [query1, answer1, query2, answer2]
    
    answer3 = make_query(query3, chat_history3)
    print(f"Q: {query3}")
    print(f"A: {answer3}")
    
    if "Error:" in answer3:
        print("❌ Test 3 failed - Server issue")
        return
    print("✅ Test 3 passed - Got response with extended history")
    
    # Test 4: Test contextual understanding
    print("\n📝 Test 4: Contextual Understanding Test")
    query4 = "How much does it cost?"
    chat_history4 = []  # No history - should get general pricing
    
    answer4 = make_query(query4, chat_history4)
    print(f"Q: {query4}")
    print(f"A: {answer4}")
    
    if "Error:" in answer4:
        print("❌ Test 4 failed - Server issue")
        return
    print("✅ Test 4 passed - Got pricing info")
    
    # Analysis
    print("\n📊 Analysis:")
    print("=" * 30)
    
    # Check if responses are using context vs generic
    if "credit card" in answer1.lower() or "paypal" in answer1.lower():
        print("✅ Stateless RAG: Using knowledge base context")
    else:
        print("❌ Stateless RAG: Not using knowledge base context")
    
    # Check if follow-up understood context
    if "refund" in answer2.lower() and "I don't know" not in answer2:
        print("✅ Stateful RAG: Understanding follow-up questions")
    else:
        print("❌ Stateful RAG: Not understanding follow-up context")
    
    # Check if "that" reference worked
    if "I don't know" not in answer3 and len(answer3) > 10:
        print("✅ Contextual References: Understanding 'that' references")
    else:
        print("❌ Contextual References: Not understanding references")
    
    print(f"\n🎯 Conversation Flow Test:")
    print(f"1. Payment question → {'✅' if 'paypal' in answer1.lower() else '❌'}")
    print(f"2. Refund follow-up → {'✅' if 'refund' in answer2.lower() else '❌'}")
    print(f"3. Time reference → {'✅' if len(answer3) > 20 else '❌'}")
    print(f"4. Pricing question → {'✅' if '$' in answer4 or 'cost' in answer4.lower() else '❌'}")

def test_server_connection():
    """Test if the server is running"""
    print("\n🔌 Testing Server Connection")
    print("-" * 30)
    
    try:
        response = requests.get("http://127.0.0.1:8000/api/v1/manage/knowledge-bases/")
        if response.status_code == 200:
            print("✅ Server is running and accessible")
            return True
        else:
            print(f"❌ Server responded with status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running")
        print("💡 Please start the server with: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Stateful RAG Tests")
    print("Make sure your server is running on http://127.0.0.1:8000")
    
    # Test server connection first
    if not test_server_connection():
        print("\n⚠️  Cannot proceed without server. Please start the server first.")
        exit(1)
    
    # Test the full stateful conversation
    test_stateful_conversation()
    
    print("\n🏁 Test completed!")