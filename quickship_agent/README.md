# QuickShip AI Agent - Standalone Package

A reusable conversational AI agent for logistics and customer service applications. Built with LangChain, Google Gemini, and supports both database queries and knowledge base search.

## Features

- 🤖 Natural language conversation with ReAct agent pattern
- 📦 Database query tools (shipment tracking, customer search, etc.)
- 📚 Knowledge base search with RAG (Retrieval Augmented Generation)
- 💬 Multi-turn conversations with session management
- 🔧 Easy to customize and extend with new tools
- 🚀 FastAPI-ready with pre-built router

## Quick Start

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file:

```env
GOOGLE_API_KEY=your_gemini_api_key
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_api_key
QUICKSHIP_DB_PATH=path/to/your/database.db
```

### 3. Basic Usage

```python
from quickship_agent import AgentService

# Initialize the agent
agent = AgentService()

# Chat with the agent
response = agent.chat(
    session_id="user-123",
    message="Track shipment QS250001"
)

print(response["response"])
```

### 4. Use with FastAPI

```python
from fastapi import FastAPI
from quickship_agent.router import router as agent_router

app = FastAPI()
app.include_router(agent_router, prefix="/api/v1/beta")
```

## Architecture

```
User Query
    ↓
Agent Service
    ↓
ReAct Agent (LangChain + Gemini)
    ↓
Tools Layer
    ├── Database Tools (SQLite)
    └── Knowledge Base Tools (Qdrant + RAG)
```

## Customization

### Adding New Tools

Create a new tool in `tools/custom_tools.py`:

```python
from langchain.tools import tool

@tool
def my_custom_tool(param: str) -> str:
    """Description of what this tool does"""
    # Your logic here
    return "Result"
```

Register it in `agent_service.py`:

```python
from .tools.custom_tools import my_custom_tool

self.tools = [
    # ... existing tools
    my_custom_tool
]
```

### Customizing the System Prompt

Edit `SYSTEM_PROMPT` in `agent_service.py` to change the agent's behavior and personality.

### Using Your Own Database

Modify `tools/database_tools.py` to connect to your database schema. The tools use standard Python DB-API, so you can easily adapt to PostgreSQL, MySQL, etc.

## API Reference

### AgentService

**Methods:**

- `chat(session_id: str, message: str, knowledge_base: str = None) -> Dict`
  - Process a user message and return agent response
  
- `get_conversation_history(session_id: str) -> List[Dict]`
  - Retrieve conversation history for a session
  
- `reset_conversation(session_id: str) -> bool`
  - Clear conversation history for a session

### FastAPI Router

**Endpoints:**

- `POST /agent/chat` - Chat with the agent
- `GET /agent/history/{session_id}` - Get conversation history
- `POST /agent/reset/{session_id}` - Reset conversation

## Examples

See the `examples/` directory for:
- Basic usage
- FastAPI integration
- Custom tool creation
- Streamlit UI integration

## Requirements

- Python 3.8+
- Google Gemini API key
- Qdrant vector database (for knowledge base features)
- SQLite database (or adapt to your database)

## License

MIT License - Feel free to use in your projects!

## Support

For issues or questions, please open an issue on GitHub.
