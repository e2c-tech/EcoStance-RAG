"""
Test script for public agent tool restrictions
"""
from quickship_agent.public_agent_service import PublicAgentService

# Test 1: Full access
print("=" * 60)
print("Test 1: Full Access (all tools)")
print("=" * 60)
agent_full = PublicAgentService(
    tenant_id="test-tenant",
    allowed_tools=["tracking", "customer_search", "delivery_estimates", "payments", "complaints"]
)
print(f"Number of tools: {len(agent_full.tools)}")
print(f"Tool names: {[t.name for t in agent_full.tools]}")
print()

# Test 2: Restricted access (tracking and payments only)
print("=" * 60)
print("Test 2: Restricted Access (tracking and payments only)")
print("=" * 60)
agent_restricted = PublicAgentService(
    tenant_id="test-tenant",
    allowed_tools=["tracking", "payments"]
)
print(f"Number of tools: {len(agent_restricted.tools)}")
print(f"Tool names: {[t.name for t in agent_restricted.tools]}")
print()

# Test 3: Minimal access (tracking only)
print("=" * 60)
print("Test 3: Minimal Access (tracking only)")
print("=" * 60)
agent_minimal = PublicAgentService(
    tenant_id="test-tenant",
    allowed_tools=["tracking"]
)
print(f"Number of tools: {len(agent_minimal.tools)}")
print(f"Tool names: {[t.name for t in agent_minimal.tools]}")
print()

# Test 4: No database tools (KB only)
print("=" * 60)
print("Test 4: No Database Tools (KB only)")
print("=" * 60)
agent_kb_only = PublicAgentService(
    tenant_id="test-tenant",
    allowed_tools=[]
)
print(f"Number of tools: {len(agent_kb_only.tools)}")
print(f"Tool names: {[t.name for t in agent_kb_only.tools]}")
print()

print("✅ All tests completed successfully!")
