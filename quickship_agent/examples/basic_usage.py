"""
Basic Usage Example for QuickShip AI Agent
"""

from quickship_agent import AgentService

# Initialize the agent
agent = AgentService()

# Example 1: Track a shipment
print("=" * 50)
print("Example 1: Track a shipment")
print("=" * 50)
response = agent.chat(
    session_id="demo-session-1",
    message="Track QS250001"
)
print(response["response"])
print()

# Example 2: Search by phone number
print("=" * 50)
print("Example 2: Search by phone number")
print("=" * 50)
response = agent.chat(
    session_id="demo-session-2",
    message="My phone is 9224217802"
)
print(response["response"])
print()

# Example 3: Multi-turn conversation
print("=" * 50)
print("Example 3: Multi-turn conversation")
print("=" * 50)
session_id = "demo-session-3"

# First message
response = agent.chat(
    session_id=session_id,
    message="Where is my order?"
)
print(f"User: Where is my order?")
print(f"Agent: {response['response']}")
print()

# Follow-up message
response = agent.chat(
    session_id=session_id,
    message="My phone is 8786649843"
)
print(f"User: My phone is 8786649843")
print(f"Agent: {response['response']}")
print()

# Get conversation history
history = agent.get_conversation_history(session_id)
print(f"Conversation history has {len(history)} messages")
print()

# Reset conversation
agent.reset_conversation(session_id)
print("Conversation reset successfully")
