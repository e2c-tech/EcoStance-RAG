# QuickShip AI Agent - Usage Diagram

## 🎯 Three Ways to Use the Agent

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUICKSHIP AI AGENT PACKAGE                   │
│                         (quickship_agent/)                       │
└─────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
         ┌──────────────┐ ┌──────────┐ ┌──────────────┐
         │   Option 1   │ │ Option 2 │ │   Option 3   │
         │ Direct Python│ │  FastAPI │ │  Streamlit   │
         └──────────────┘ └──────────┘ └──────────────┘
```

---

## Option 1: Direct Python Usage

### Use Case
- Python scripts
- Jupyter notebooks
- Background jobs
- CLI applications

### Code
```python
from quickship_agent import AgentService

# Initialize
agent = AgentService()

# Chat
response = agent.chat(
    session_id="user-123",
    message="Track QS250001"
)

print(response["response"])
```

### Flow Diagram
```
Your Python Code
       ↓
   AgentService
       ↓
   ReAct Agent
       ↓
   Tools (DB/KB)
       ↓
   Response Dict
```

---

## Option 2: FastAPI Integration

### Use Case
- REST API
- Microservice
- Web backend
- Mobile app backend

### Code
```python
from fastapi import FastAPI
from quickship_agent.router import router

app = FastAPI()
app.include_router(router, prefix="/api/v1")
```

### Flow Diagram
```
HTTP Client (curl/Postman/Frontend)
       ↓
POST /api/v1/agent/chat
       ↓
   FastAPI Router
       ↓
   AgentService
       ↓
   ReAct Agent
       ↓
   Tools (DB/KB)
       ↓
   JSON Response
```

### API Call Example
```bash
curl -X POST "http://localhost:8000/api/v1/agent/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user-123",
    "message": "Track QS250001",
    "knowledge_base": "faq"
  }'
```

---

## Option 3: Streamlit Integration

### Use Case
- Interactive UI
- Demo application
- Internal tools
- Proof of concept

### Code
```python
import streamlit as st
from quickship_agent import agent_service

st.title("AI Customer Service")

if prompt := st.chat_input("Ask me anything..."):
    response = agent_service.chat(
        session_id=st.session_state.session_id,
        message=prompt
    )
    st.write(response["response"])
```

### Flow Diagram
```
Streamlit UI
       ↓
   User Input
       ↓
   agent_service.chat()
       ↓
   ReAct Agent
       ↓
   Tools (DB/KB)
       ↓
   Display Response
```

---

## 🔄 Complete Request Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                            │
│  "Track my order QS250001"                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT SERVICE                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 1: Query Classification                             │  │
│  │ - Analyze user intent                                    │  │
│  │ - Determine query type (DB/KB/Out-of-scope)             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 2: Pattern Matching (for DB queries)               │  │
│  │ - Extract shipment ID: QS250001                          │  │
│  │ - Select appropriate tool                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 3: Tool Execution                                   │  │
│  │ - Call: get_shipment_status("QS250001")                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATABASE TOOL                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. Connect to database                                   │  │
│  │ 2. Execute SQL query                                     │  │
│  │ 3. Fetch results                                         │  │
│  │ 4. Format response with emojis                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FORMATTED RESPONSE                         │
│  📦 Shipment Details:                                           │
│  Shipment ID: QS250001                                          │
│  Status: Delivered                                              │
│  Tracking: TRK123456789                                         │
│  🔗 Track Online: https://quickship.in/track?id=TRK123456789   │
│  ...                                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         USER SEES                               │
│  Beautiful formatted response with all shipment details         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎨 Customization Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR REQUIREMENTS                            │
│  "I need to track orders in my e-commerce app"                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 1: ADAPT DATABASE                       │
│  Edit: tools/database_tools.py                                  │
│  - Change table names (shipments → orders)                      │
│  - Update SQL queries                                           │
│  - Modify response format                                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 2: UPDATE PROMPT                        │
│  Edit: agent_service.py                                         │
│  - Change SYSTEM_PROMPT                                         │
│  - Update agent personality                                     │
│  - Modify guidelines                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 3: ADD CUSTOM TOOLS                     │
│  Create: tools/custom_tools.py                                  │
│  - Define new tools                                             │
│  - Register in agent_service.py                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 4: TEST                                 │
│  Run: python examples/basic_usage.py                            │
│  - Test all scenarios                                           │
│  - Verify responses                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    READY TO USE!                                │
│  Your customized AI agent is ready                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔀 Multi-Turn Conversation Flow

```
Turn 1:
User: "Where is my order?"
       ↓
Agent: Classify → Missing info
       ↓
Response: "I need your shipment ID or phone number"

Turn 2:
User: "My phone is 9224217802"
       ↓
Agent: Extract phone → search_shipments_by_customer
       ↓
Database: Find 2 shipments
       ↓
Response: "Found 2 shipments: QS250001 (Delivered), QS250022 (In Transit)"

Turn 3:
User: "Tell me about QS250022"
       ↓
Agent: Extract ID → get_shipment_status
       ↓
Database: Get full details
       ↓
Response: [Full shipment details]
```

---

## 🏗️ Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                         │
│  FastAPI Router / Streamlit UI / Python Script                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BUSINESS LOGIC LAYER                       │
│  Agent Service (ReAct Pattern)                                  │
│  - Query classification                                         │
│  - Tool selection                                               │
│  - Response generation                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
┌───────────────────────────┐  ┌──────────────────────────┐
│      TOOLS LAYER          │  │    TOOLS LAYER           │
│  Database Tools           │  │  Knowledge Base Tools    │
│  - get_shipment_status    │  │  - search_knowledge_base │
│  - search_by_customer     │  │  - list_knowledge_bases  │
│  - track_by_number        │  │                          │
│  - get_delivery_estimate  │  │                          │
│  - check_payment_status   │  │                          │
│  - get_complaint_status   │  │                          │
└────────────┬──────────────┘  └────────────┬─────────────┘
             │                              │
             ▼                              ▼
┌───────────────────────────┐  ┌──────────────────────────┐
│      DATA LAYER           │  │    DATA LAYER            │
│  SQLite/PostgreSQL/MySQL  │  │  Qdrant Vector DB        │
│  - shipments              │  │  - Document embeddings   │
│  - customers              │  │  - Semantic search       │
│  - payments               │  │                          │
│  - complaints             │  │                          │
└───────────────────────────┘  └──────────────────────────┘
```

---

## 🚀 Deployment Options

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT OPTIONS                           │
└─────────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Option A   │    │   Option B   │    │   Option C   │
│  Standalone  │    │ Microservice │    │  Integrated  │
│   Server     │    │              │    │   in App     │
└──────────────┘    └──────────────┘    └──────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Run FastAPI  │    │ Docker       │    │ Import in    │
│ with agent   │    │ Container    │    │ existing app │
│ router       │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## 📊 Data Flow Summary

```
Input → Classification → Tool Selection → Execution → Response

Where:
- Input: User message
- Classification: DB/KB/Out-of-scope
- Tool Selection: Choose appropriate tool
- Execution: Run tool and get data
- Response: Format and return to user
```

---

## 🎯 Decision Tree

```
User Query
    │
    ├─ Contains shipment ID? → get_shipment_status
    │
    ├─ Contains phone/email? → search_shipments_by_customer
    │
    ├─ Contains tracking #? → track_by_tracking_number
    │
    ├─ Asks "when"? → get_delivery_estimate
    │
    ├─ Asks about payment? → check_cod_payment_status
    │
    ├─ Asks about complaint? → get_complaint_status
    │
    ├─ Asks about policy/rate? → search_knowledge_base
    │
    ├─ Out of scope? → Polite rejection
    │
    └─ Unknown? → LLM with tools
```

---

**Use these diagrams to understand and explain the agent's behavior!**
