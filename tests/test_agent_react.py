"""
Test the ReAct agent implementation
"""
import sys
sys.path.insert(0, 'quickship_agent')

from quickship_agent.agent_service import agent_service

print("🤖 Testing ReAct Agent Implementation\n")
print("=" * 60)

# Test 1: Simple greeting (should respond without tools)
print("\n1. Testing greeting (no tools needed):")
print("-" * 60)
response = agent_service.chat(
    session_id="test-1",
    message="Hello, who are you?"
)
print(f"Response: {response['response'][:200]}...")
print(f"Success: {response['success']}")

# Test 2: Shipment tracking (should call database tool)
print("\n2. Testing shipment tracking (should call DB tool):")
print("-" * 60)
response = agent_service.chat(
    session_id="test-2",
    message="Track QS250001"
)
print(f"Response: {response['response'][:200]}...")
print(f"Success: {response['success']}")

# Test 3: Policy question (should call KB tool if KB is selected)
print("\n3. Testing policy question (should call KB tool):")
print("-" * 60)
response = agent_service.chat(
    session_id="test-3",
    message="What are your shipping rates?",
    knowledge_base="customer-faq"  # Assuming this KB exists
)
print(f"Response: {response['response'][:200]}...")
print(f"Success: {response['success']}")

# Test 4: Out of scope (should reject)
print("\n4. Testing out-of-scope query (should reject):")
print("-" * 60)
response = agent_service.chat(
    session_id="test-4",
    message="Write me a Python function"
)
print(f"Response: {response['response'][:200]}...")
print(f"Success: {response['success']}")

print("\n" + "=" * 60)
print("✅ All tests completed!")
