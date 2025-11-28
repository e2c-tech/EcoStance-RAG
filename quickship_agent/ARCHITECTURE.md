# QuickShip AI Agent - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│  (Streamlit UI / Web App / Mobile App / API Client)            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI ROUTER                             │
│  POST /agent/chat                                               │
│  GET  /agent/history/{session_id}                               │
│  POST /agent/reset/{session_id}                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AGENT SERVICE                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Query Classification                                     │  │
│  │  - Database queries (shipment tracking)                  │  │
│  │  - Knowledge base queries (policies, FAQs)               │  │
│  │  - Out of scope detection                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ReAct Agent (LangChain + Google Gemini)                 │  │
│  │  - Reasoning: Understand user intent                     │  │
│  │  - Acting: Select and execute tools                      │  │
│  │  - Response: Generate natural language response          │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
┌───────────────────────────┐  ┌──────────────────────────┐
│   DATABASE TOOLS          │  │  KNOWLEDGE BASE TOOLS    │
│                           │  │                          │
│  • get_shipment_status    │  │  • search_knowledge_base │
│  • search_by_customer     │  │  • list_knowledge_bases  │
│  • track_by_number        │  │                          │
│  • get_delivery_estimate  │  │                          │
│  • check_payment_status   │  │                          │
│  • get_complaint_status   │  │                          │
└────────────┬──────────────┘  └────────────┬─────────────┘
             │                              │
             ▼                              ▼
┌───────────────────────────┐  ┌──────────────────────────┐
│   DATABASE                │  │  RAG SERVICE             │
│   (SQLite/PostgreSQL)     │  │  (Qdrant + Embeddings)   │
│                           │  │                          │
│  • shipments              │  │  • Document retrieval    │
│  • customers              │  │  • Semantic search       │
│  • payments               │  │  • Context generation    │
│  • complaints             │  │                          │
│  • delivery_boys          │  │                          │
└───────────────────────────┘  └────────────┬─────────────┘
                                            │
                                            ▼
                              ┌──────────────────────────┐
                              │  QDRANT VECTOR DB        │
                              │  • Policies collection   │
                              │  • FAQ collection        │
                              │  • Procedures collection │
                              └──────────────────────────┘
```

## Component Details

### 1. Agent Service (`agent_service.py`)

**Responsibilities:**
- Manage conversation sessions
- Classify user queries
- Orchestrate tool execution
- Generate responses

**Key Methods:**
```python
chat(session_id, message, knowledge_base) -> Dict
get_conversation_history(session_id) -> List[Dict]
reset_conversation(session_id) -> bool
```

**Query Classification:**
```
User Query → Classifier
    ├── Database Query → Direct tool execution
    ├── Knowledge Base Query → RAG search
    ├── Out of Scope → Polite rejection
    └── Unknown → LLM with tools
```

### 2. Tools Layer

#### Database Tools (`tools/database_tools.py`)

Each tool follows this pattern:
```python
@tool
def tool_name(param: str) -> str:
    """Tool description for LLM"""
    # 1. Connect to database
    # 2. Execute query
    # 3. Format results
    # 4. Return formatted string
```

**Tool Selection Logic:**
```
User mentions shipment ID → get_shipment_status
User provides phone/email → search_shipments_by_customer
User provides tracking # → track_by_tracking_number
User asks "when" → get_delivery_estimate
User asks about payment → check_cod_payment_status
User mentions complaint → get_complaint_status
```

#### Knowledge Base Tools (`tools/knowledge_base_tools.py`)

**RAG Flow:**
```
User Query
    ↓
Embedding Generation (HuggingFace)
    ↓
Vector Search (Qdrant)
    ↓
Top-K Documents Retrieved
    ↓
Context + Query → LLM
    ↓
Generated Answer
```

### 3. Services Layer

#### RAG Service (`services/rag_service.py`)

**Components:**
- **Retriever**: Qdrant vector search
- **Embeddings**: HuggingFace sentence-transformers
- **LLM**: Google Gemini for answer generation
- **Prompt**: Structured prompt with context

**Chain Structure:**
```python
RunnablePassthrough.assign(
    context=retrieve_and_format,
    chat_history=format_chat_history
) | qa_prompt | llm | StrOutputParser()
```

#### Qdrant Service (`services/qdrant_service.py`)

**Purpose:**
- Initialize Qdrant client
- Manage vector database connections

### 4. FastAPI Router (`router.py`)

**Endpoints:**

```python
POST /agent/chat
Request: {
    "session_id": "optional",
    "message": "user query",
    "knowledge_base": "optional"
}
Response: {
    "response": "agent response",
    "session_id": "uuid",
    "success": true,
    "error": null
}

GET /agent/history/{session_id}
Response: {
    "session_id": "uuid",
    "messages": [...]
}

POST /agent/reset/{session_id}
Response: {
    "message": "success message",
    "success": true
}
```

## Data Flow Examples

### Example 1: Shipment Tracking

```
User: "Track QS250001"
    ↓
Agent Service
    ↓
Query Classification: "database"
    ↓
Pattern Match: QS250\d{3}
    ↓
Tool: get_shipment_status("QS250001")
    ↓
Database Query: SELECT * FROM shipments WHERE shipment_id = ?
    ↓
Format Response: Shipment details with emoji
    ↓
Return to User
```

### Example 2: Policy Question

```
User: "What is your return policy?"
    ↓
Agent Service
    ↓
Query Classification: "knowledge_base"
    ↓
Tool: search_knowledge_base("policies", "return policy")
    ↓
RAG Service
    ├── Generate embedding for query
    ├── Search Qdrant for similar documents
    ├── Retrieve top 3 documents
    └── Generate answer with LLM
    ↓
Return formatted answer to User
```

### Example 3: Multi-turn Conversation

```
Turn 1:
User: "Where is my order?"
Agent: "I need your shipment ID or phone number"

Turn 2:
User: "My phone is 9224217802"
    ↓
Agent Service (with conversation history)
    ↓
Tool: search_shipments_by_customer(phone="9224217802")
    ↓
Database: Find all shipments for customer
    ↓
Agent: "I found 2 shipments: QS250001 (Delivered), QS250022 (In Transit)"
```

## Session Management

```
Session Storage (In-Memory)
{
    "session-123": [
        {"role": "user", "content": "Track my order"},
        {"role": "assistant", "content": "I need your shipment ID"},
        {"role": "user", "content": "QS250001"},
        {"role": "assistant", "content": "Your shipment..."}
    ]
}
```

**For Production:**
Replace with Redis or database:
```python
redis.setex(f"session:{session_id}", 3600, json.dumps(messages))
```

## Error Handling

```
Try-Catch Hierarchy:
    ├── Router Level: HTTP exceptions
    ├── Service Level: Business logic errors
    ├── Tool Level: Database/API errors
    └── Logging: All levels logged
```

## Configuration Management

```
Environment Variables (.env)
    ↓
config.py (loads and validates)
    ↓
Services (import from config)
```

**Configuration Hierarchy:**
1. Environment variables (highest priority)
2. .env file
3. Default values in config.py

## Security Architecture

```
API Request
    ↓
Rate Limiting (optional)
    ↓
Authentication (optional)
    ↓
Input Validation
    ↓
Agent Processing
    ↓
Output Sanitization
    ↓
Response
```

## Scalability Considerations

### Horizontal Scaling
```
Load Balancer
    ├── Agent Instance 1
    ├── Agent Instance 2
    └── Agent Instance 3
         ↓
    Shared Redis (sessions)
         ↓
    Database (read replicas)
```

### Caching Strategy
```
Request → Cache Check
    ├── Hit: Return cached response
    └── Miss: Process → Cache → Return
```

### Async Processing
```
User Request → Queue → Worker Pool → Response
```

## Monitoring Points

```
Metrics to Track:
├── Request count
├── Response time
├── Error rate
├── Tool usage frequency
├── Session duration
├── Database query time
├── LLM API latency
└── Cache hit rate
```

## Extension Points

### Adding New Tools
```python
# 1. Create tool
@tool
def my_tool(param: str) -> str:
    """Description"""
    return result

# 2. Register in agent_service.py
self.tools.append(my_tool)

# 3. Update system prompt
# 4. Test
```

### Adding New Data Sources
```python
# 1. Create new tool file
# tools/api_tools.py

# 2. Implement tools
@tool
def call_external_api(query: str) -> str:
    response = requests.get(f"https://api.example.com?q={query}")
    return response.json()

# 3. Register tools
```

### Changing LLM Provider
```python
# Replace in agent_service.py
from langchain_openai import ChatOpenAI

self.llm = ChatOpenAI(
    model="gpt-4",
    api_key=OPENAI_API_KEY
)
```

## Performance Optimization

### Database
- Use connection pooling
- Add indexes on frequently queried columns
- Use read replicas for scaling

### Caching
- Cache frequent queries
- Cache embeddings
- Cache LLM responses (with caution)

### LLM
- Use streaming for long responses
- Batch requests when possible
- Use cheaper models for simple queries

---

This architecture is designed to be:
- **Modular**: Easy to swap components
- **Scalable**: Can handle increasing load
- **Maintainable**: Clear separation of concerns
- **Extensible**: Easy to add new features
- **Testable**: Each component can be tested independently
