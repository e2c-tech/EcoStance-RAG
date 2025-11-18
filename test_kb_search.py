"""
Test KB search functionality
"""

import sys
sys.path.append('.')

from app.services.agent_tools import search_knowledge_base, list_available_knowledge_bases

print("=" * 60)
print("Testing Knowledge Base Search")
print("=" * 60)

# Test 1: List available KBs
print("\n1. Listing available knowledge bases...")
try:
    result = list_available_knowledge_bases.invoke({})
    print(f"✓ Result: {result}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 2: Search a KB (if any exist)
print("\n2. Testing KB search...")
try:
    # Try to search - you'll need to replace 'test_kb' with an actual KB name
    result = search_knowledge_base.invoke({
        "collection_name": "test_kb",  # Replace with actual KB name
        "query": "What is your return policy?"
    })
    print(f"✓ Result: {result[:200]}...")
except Exception as e:
    print(f"✗ Error: {e}")
    print("   (This is expected if no KB exists)")

print("\n" + "=" * 60)
print("Test completed!")
print("\nTo test with real data:")
print("1. Upload documents to create a knowledge base")
print("2. Replace 'test_kb' with your KB name")
print("3. Run this test again")
print("=" * 60)
