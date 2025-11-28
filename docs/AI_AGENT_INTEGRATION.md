# AI Agent Integration Guide

## Overview

The QuickShip AI Agent is now integrated into your EcoStanceAgentV1 application. This conversational AI agent uses Google Gemini and LangChain to provide intelligent customer service capabilities.

## Features

✅ **Natural Language Conversations** - Chat with users in natural language
✅ **Database Queries** - Search shipments, customers, payments, complaints
✅ **Knowledge Base Search** - RAG-powered document search with Qdrant
✅ **Multi-turn Conversations** - Maintains conversation context
✅ **Session Management** - Track conversations by session ID
✅ **ReAct Pattern** - Reasoning + Acting for intelligent tool use

## API Endpoints

All agent endpoints are under `/api/v1/beta/agent/`

### 1. Chat with Agent

**POST** `/api/v1/beta/agent/chat`

Send a message to the AI agent and get a response.

**Request Body:**
```json
{
  "session_id": "optional-uuid",
  "message": "Track my shipment QS250001",
  "knowledge_base": "optional-kb-name"
}
```

**Response:**
```json
{
  "response": "Agent's response text",
  "session_id": "uuid",
  "success": true,
  "error": null
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/beta/agent/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, who are you?"
  }'
```

### 2. Get Conversation History

**GET** `/api/v1/beta/agent/history/{session_id}`

Retrieve the conversation history for a specific session.

**Response:**
```json
{
  "session_id": "uuid",
  "messages": [
    {
      "role": "user",
      "content": "Hello"
    },
    {
      "role": "assistant",
      "content": "Hi! I'm QuickShip's AI assistant..."
    }
  ]
}
```

### 3. Reset Conversation

**POST** `/api/v1/beta/agent/reset/{session_id}`

Clear the conversation history for a session.

**Response:**
```json
{
  "message": "Conversation reset successfully",
  "success": true
}
```

## Available Tools

The agent has access to these tools:

### Database Tools (6)

1. **get_shipment_status** - Get shipment details by ID (QS250XXX)
2. **search_shipments_by_customer** - Find shipments by phone/email
3. **track_by_tracking_number** - Track using tracking number (TRKXXXXXXXXX)
4. **get_delivery_estimate** - Get delivery date estimates
5. **check_cod_payment_status** - Check COD payment status
6. **get_complaint_status** - Check complaints for a shipment

### Knowledge Base Tools (2)

1. **search_knowledge_base** - Search documents with RAG
2. **list_available_knowledge_bases** - List available KBs

## Configuration

The agent is configured via environment variables in `.env`:

```env
# AI Agent Configuration
GOOGLE_API_KEY=your_gemini_api_key
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_api_key
QUICKSHIP_DB_PATH=tenant_system.db
AGENT_MODEL=gemini-2.0-flash-exp
AGENT_TEMPERATURE=0.3
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
```

## Usage Examples

### Example 1: Track a Shipment

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/beta/agent/chat",
    json={
        "message": "Track QS250001"
    }
)

print(response.json()["response"])
```

### Example 2: Multi-turn Conversation

```python
import requests

session_id = "user-123"

# First message
response = requests.post(
    "http://localhost:8000/api/v1/beta/agent/chat",
    json={
        "session_id": session_id,
        "message": "Where is my order?"
    }
)
print(response.json()["response"])

# Follow-up message
response = requests.post(
    "http://localhost:8000/api/v1/beta/agent/chat",
    json={
        "session_id": session_id,
        "message": "My phone is 9224217802"
    }
)
print(response.json()["response"])
```

### Example 3: Knowledge Base Query

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/beta/agent/chat",
    json={
        "message": "What are your shipping rates?",
        "knowledge_base": "policies"
    }
)

print(response.json()["response"])
```

## Testing

Run the integration test:

```bash
# Start the server
python run_app.py

# In another terminal, run the test
python test_agent_integration.py
```

## Customization

### Adding Custom Tools

Create a new tool in `quickship_agent/tools/custom_tools.py`:

```python
from langchain.tools import tool

@tool
def my_custom_tool(param: str) -> str:
    """Description of what this tool does"""
    # Your logic here
    return "Result"
```

Register it in `quickship_agent/agent_service.py`:

```python
from .tools.custom_tools import my_custom_tool

self.tools.append(my_custom_tool)
self.llm_with_tools = self.llm.bind_tools(self.tools)
```

### Customizing the System Prompt

Edit `SYSTEM_PROMPT` in `quickship_agent/agent_service.py` to change the agent's behavior and personality.

### Using a Different Database

Modify `quickship_agent/tools/database_tools.py` to connect to your database schema.

## Architecture

```
User Request
    ↓
FastAPI Router (/api/v1/beta/agent/*)
    ↓
Agent Service (agent_service.py)
    ↓
ReAct Agent (LangChain + Gemini)
    ↓
Tools Layer
    ├── Database Tools → SQLite/PostgreSQL
    └── KB Tools → Qdrant (RAG) → Gemini
    ↓
Response
```

## Query Classification

The agent automatically classifies queries:

- **Database Query** → Direct tool execution (shipment tracking)
- **Knowledge Base Query** → RAG search (policies, FAQs)
- **Out of Scope** → Polite rejection
- **Unknown** → LLM with tools

## Session Management

Sessions are stored in-memory by default. For production:

1. Use Redis for session storage
2. Implement session expiration
3. Add session cleanup

## Error Handling

The agent handles errors gracefully:

- Database connection errors
- API rate limits
- Invalid queries
- Missing information

## Security Considerations

- API keys are stored in environment variables
- Input validation on all endpoints
- Rate limiting recommended
- Authentication can be added via middleware

## Performance

- Response time: 1-3 seconds (depends on tool execution)
- Concurrent users: Scales with your infrastructure
- Session storage: In-memory (use Redis for production)

## Monitoring

Monitor these metrics:

- Request count
- Response time
- Error rate
- Tool usage frequency
- Session duration

## Troubleshooting

### Agent not responding

Check:
1. Server is running: `python run_app.py`
2. Environment variables are set in `.env`
3. Google API key is valid
4. Database path is correct

### Database errors

Check:
1. `QUICKSHIP_DB_PATH` points to correct database
2. Database file exists and is readable
3. Database schema matches expected structure

### Qdrant errors

Check:
1. `QDRANT_URL` and `QDRANT_API_KEY` are correct
2. Collections exist in Qdrant
3. Network connectivity to Qdrant

## Next Steps

1. ✅ Test the agent with `test_agent_integration.py`
2. ✅ Try it in the API docs at `/docs`
3. ✅ Customize the system prompt for your use case
4. ✅ Add custom tools if needed
5. ✅ Integrate into your frontend application

## Support

For more information, see:
- `quickship_agent/README.md` - Package overview
- `quickship_agent/INTEGRATION_GUIDE.md` - Detailed integration
- `quickship_agent/ARCHITECTURE.md` - System architecture
- `quickship_agent/examples/` - Usage examples

## API Documentation

Visit `http://localhost:8000/docs` and look for the **"13. AI Agent (Beta)"** section to try the endpoints interactively.
