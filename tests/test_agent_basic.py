"""
Basic test for ReAct Agent
Run this to verify the agent is working
"""

import sys
sys.path.append('.')

from app.services.agent_service_beta import agent_service

def test_agent():
    """Test basic agent functionality"""
    
    print("Testing QuickShip AI Agent...")
    print("=" * 50)
    
    # Test 1: Simple query
    print("\n Test 1: Asking about shipment status")
    result = agent_service.chat("test_session_1", "What is the status of shipment QS250001?")
    print(f"Response: {result['response'][:200]}...")
    print(f"Success: {result['success']}")
    
    # Test 2: Search by phone
    print("\n\nTest 2: Searching by phone number")
    result = agent_service.chat("test_session_2", "My phone is 9224217802, show my shipments")
    print(f"Response: {result['response'][:200]}...")
    print(f"Success: {result['success']}")
    
    # Test 3: Vague query (should ask for more info)
    print("\n\nTest 3: Vague query")
    result = agent_service.chat("test_session_3", "Where is my order?")
    print(f"Response: {result['response'][:200]}...")
    print(f"Success: {result['success']}")
    
    print("\n" + "=" * 50)
    print("Tests completed!")

if __name__ == "__main__":
    test_agent()
