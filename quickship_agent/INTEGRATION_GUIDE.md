# QuickShip AI Agent - Integration Guide

This guide shows you how to integrate the QuickShip AI Agent into your existing application.

## Table of Contents

1. [Installation](#installation)
2. [Basic Setup](#basic-setup)
3. [Database Adaptation](#database-adaptation)
4. [FastAPI Integration](#fastapi-integration)
5. [Streamlit Integration](#streamlit-integration)
6. [Customization](#customization)
7. [Production Deployment](#production-deployment)

---

## Installation

### Option 1: Install from source

```bash
cd quickship_agent
pip install -e .
```

### Option 2: Install from requirements

```bash
cd quickship_agent
pip install -r requirements.txt
```

---

## Basic Setup

### 1. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
GOOGLE_API_KEY=your_actual_gemini_api_key
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_api_key
QUICKSHIP_DB_PATH=path/to/your/database.db
```

### 2. Test Basic Functionality

```python
from quickship_agent import AgentService

agent = AgentService()
response = agent.chat(
    session_id="test-123",
    message="Track QS250001"
)
print(response["response"])
```

---

## Database Adaptation

The agent comes with tools for a QuickShip logistics database. To adapt it to your database:

### Step 1: Understand Your Schema

Identify the tables and columns you need to query. For example:
- Orders table
- Customers table
- Products table
- etc.

### Step 2: Modify Database Tools

Edit `quickship_agent/tools/database_tools.py`:

```python
@tool
def get_order_status(order_id: str) -> str:
    """
    Get order status from your database.
    Adapt the SQL query to match your schema.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # MODIFY THIS QUERY FOR YOUR SCHEMA
        query = """
        SELECT o.order_id, o.status, o.customer_name, o.total_amount
        FROM orders o
        WHERE o.order_id = ?
        """
        
        cursor.execute(query, (order_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return f"No order found with ID {order_id}"
        
        # Format response
        return f"""
Order ID: {result['order_id']}
Status: {result['status']}
Customer: {result['customer_name']}
Total: ${result['total_amount']}
"""
    except Exception as e:
        return f"Error: {str(e)}"
```

### Step 3: Update System Prompt

Edit `quickship_agent/agent_service.py` and modify `SYSTEM_PROMPT` to reflect your business domain:

```python
SYSTEM_PROMPT = """You are a helpful customer service agent for [YOUR COMPANY].

Your role:
- Help customers with their orders
- Answer questions about products
- Provide support and assistance

Available Tools:
- get_order_status(order_id): Get order details
- search_orders_by_customer(email): Find customer orders
- [Add your tools here]

Guidelines:
1. Always be polite and professional
2. Use tools to get accurate information
3. Never make up information
...
"""
```

### Step 4: Update Database Connection

If you're using PostgreSQL, MySQL, or another database, modify `get_db_connection()` in `database_tools.py`:

```python
# For PostgreSQL
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    conn = psycopg2.connect(
        host="your_host",
        database="your_db",
        user="your_user",
        password="your_password"
    )
    conn.cursor_factory = RealDictCursor
    return conn

# For MySQL
import mysql.connector

def get_db_connection():
    conn = mysql.connector.connect(
        host="your_host",
        database="your_db",
        user="your_user",
        password="your_password"
    )
    return conn
```

---

## FastAPI Integration

### Full Example

```python
from fastapi import FastAPI
from quickship_agent.router import router as agent_router

app = FastAPI(title="My App with AI Agent")

# Include agent router
app.include_router(
    agent_router,
    prefix="/api/v1",
    tags=["AI Agent"]
)

# Your existing routes
@app.get("/")
async def root():
    return {"message": "Welcome to My App"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### API Endpoints

Once integrated, you'll have these endpoints:

- `POST /api/v1/agent/chat` - Chat with agent
- `GET /api/v1/agent/history/{session_id}` - Get conversation history
- `POST /api/v1/agent/reset/{session_id}` - Reset conversation

### Example API Call

```bash
curl -X POST "http://localhost:8000/api/v1/agent/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user-123",
    "message": "Track my order",
    "knowledge_base": "faq"
  }'
```

---

## Streamlit Integration

### Example Streamlit App

```python
import streamlit as st
from quickship_agent import AgentService
import uuid

# Initialize agent
if 'agent' not in st.session_state:
    st.session_state.agent = AgentService()

# Initialize session ID
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Initialize chat history
if 'messages' not in st.session_state:
    st.session_state.messages = []

st.title("🤖 AI Customer Service Agent")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything..."):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = st.session_state.agent.chat(
                session_id=st.session_state.session_id,
                message=prompt
            )
            st.markdown(response["response"])
    
    # Add to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": response["response"]
    })

# Sidebar
with st.sidebar:
    if st.button("Reset Conversation"):
        st.session_state.agent.reset_conversation(st.session_state.session_id)
        st.session_state.messages = []
        st.rerun()
```

---

## Customization

### Adding New Tools

Create a new file `my_custom_tools.py`:

```python
from langchain.tools import tool

@tool
def check_inventory(product_id: str) -> str:
    """Check product inventory levels"""
    # Your logic here
    return f"Product {product_id} has 50 units in stock"
```

Register in your agent:

```python
from quickship_agent import AgentService
from my_custom_tools import check_inventory

class MyAgentService(AgentService):
    def __init__(self):
        super().__init__()
        self.tools.append(check_inventory)
        self.llm_with_tools = self.llm.bind_tools(self.tools)

# Use your custom agent
agent = MyAgentService()
```

### Changing the LLM Model

Edit `config.py` or set environment variable:

```env
AGENT_MODEL=gemini-1.5-pro
AGENT_TEMPERATURE=0.5
```

### Customizing Response Format

Modify the tool return values in `database_tools.py` to match your preferred format (JSON, plain text, markdown, etc.).

---

## Production Deployment

### 1. Environment Variables

Use a secrets manager (AWS Secrets Manager, Azure Key Vault, etc.) instead of `.env` files.

### 2. Session Storage

Replace in-memory session storage with Redis or a database:

```python
import redis

class AgentService:
    def __init__(self):
        # ... existing code ...
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True
        )
    
    def get_conversation_history(self, session_id: str):
        history = self.redis_client.get(f"session:{session_id}")
        return json.loads(history) if history else []
    
    def _save_conversation(self, session_id: str, messages: list):
        self.redis_client.setex(
            f"session:{session_id}",
            3600,  # 1 hour TTL
            json.dumps(messages)
        )
```

### 3. Logging

Add proper logging:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent.log'),
        logging.StreamHandler()
    ]
)
```

### 4. Error Handling

Add retry logic and circuit breakers for external API calls.

### 5. Monitoring

Add metrics and monitoring:

```python
from prometheus_client import Counter, Histogram

chat_requests = Counter('agent_chat_requests_total', 'Total chat requests')
chat_duration = Histogram('agent_chat_duration_seconds', 'Chat duration')

@chat_duration.time()
def chat(self, session_id, message, knowledge_base=None):
    chat_requests.inc()
    # ... existing code ...
```

### 6. Rate Limiting

Implement rate limiting to prevent abuse:

```python
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/agent/chat")
@limiter.limit("10/minute")
async def chat_with_agent(request: Request, chat_request: ChatRequest):
    # ... existing code ...
```

---

## Troubleshooting

### Common Issues

**Issue**: "GOOGLE_API_KEY not set"
- **Solution**: Make sure `.env` file exists and contains valid API key

**Issue**: "Database connection error"
- **Solution**: Check `QUICKSHIP_DB_PATH` points to correct database file

**Issue**: "Qdrant connection failed"
- **Solution**: Verify `QDRANT_URL` and `QDRANT_API_KEY` are correct

**Issue**: Agent gives wrong answers
- **Solution**: Review and update the `SYSTEM_PROMPT` to be more specific

---

## Support

For issues or questions:
- Check the examples in `examples/` directory
- Review the main README.md
- Open an issue on GitHub

---

## License

MIT License - See LICENSE file for details
