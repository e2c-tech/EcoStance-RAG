# Hybrid Agent Architecture

## Overview

The QuickShip AI Agent is a **hybrid intelligent agent** that combines:
1. **Structured Data Access** - Direct database queries for shipment tracking
2. **Unstructured Data Access** - RAG-based search through knowledge base documents

This gives the agent the ability to answer both operational queries (shipments) and informational queries (policies, procedures).

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query                                │
│          "Where is my order? What's your return policy?"     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   ReAct Agent (Gemini)                       │
│              Decides which tools to use                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    ┌───────┴───────┐
                    ↓               ↓
        ┌───────────────────┐   ┌──────────────────────┐
        │  Database Tools   │   │ Knowledge Base Tools │
        │  (6 tools)        │   │  (2 tools)           │
        └───────────────────┘   └──────────────────────┘
                    ↓               ↓
        ┌───────────────────┐   ┌──────────────────────┐
        │   QuickShip.db    │   │   Qdrant Vector DB   │
        │   (SQLite)        │   │   (RAG System)       │
        │                   │   │                      │
        │ • Shipments       │   │ • Policies           │
        │ • Customers       │   │ • Procedures         │
        │ • Payments        │   │ • FAQs               │
        │ • Complaints      │   │ • Documentation      │
        └───────────────────┘   └──────────────────────┘
```

---

## Tool Categories

### 1. Database Tools (Structured Data)

**Purpose:** Query operational data from QuickShip database

**Tools:**
- `get_shipment_status(shipment_id)` - Get shipment details
- `search_shipments_by_customer(phone, email)` - Find customer shipments
- `track_by_tracking_number(tracking_number)` - Track by tracking #
- `get_delivery_estimate(shipment_id)` - Get delivery dates
- `check_cod_payment_status(shipment_id)` - Check payment status
- `get_complaint_status(shipment_id)` - View complaints

**Data Source:** QuickShip.db (SQLite)

**Use Cases:**
- "Where is my order QS250001?"
- "Track my shipment"
- "When will my package arrive?"
- "Has my COD been collected?"

### 2. Knowledge Base Tools (Unstructured Data)

**Purpose:** Search through company documents and knowledge bases

**Tools:**
- `search_knowledge_base(collection_name, query)` - Search documents
- `list_available_knowledge_bases()` - List available KBs

**Data Source:** Qdrant Vector Database (RAG System)

**Use Cases:**
- "What is your return policy?"
- "How do I file a complaint?"
- "What are your shipping rates?"
- "Tell me about delivery procedures"

---

## How the Agent Decides

The agent uses **reasoning** to determine which tools to use:

### Decision Flow:

```
User Query → Agent Analyzes → Determines Intent → Selects Tools

Examples:

1. "Track QS250001"
   → Intent: Shipment tracking
   → Tool: get_shipment_status
   → Source: Database

2. "What's your return policy?"
   → Intent: Policy information
   → Tool: search_knowledge_base
   → Source: Knowledge Base

3. "My order is delayed, what can I do?"
   → Intent: Hybrid (status + policy)
   → Tools: get_shipment_status + search_knowledge_base
   → Sources: Both Database and Knowledge Base
```

---

## Example Conversations

### Example 1: Pure Database Query
```
User: "Track shipment QS250001"
Agent: [Uses get_shipment_status tool]
Agent: "Your shipment QS250001 is Delivered.
       Delivered on: Oct 25, 2024
       Tracking: TRK10938466"
```

### Example 2: Pure Knowledge Base Query
```
User: "What is your return policy?"
Agent: [Uses list_available_knowledge_bases]
Agent: [Uses search_knowledge_base('policies', 'return policy')]
Agent: "According to our return policy document:
       - Returns accepted within 30 days
       - Item must be unused and in original packaging
       - Refund processed within 7-10 business days"
```

### Example 3: Hybrid Query
```
User: "My shipment is delayed, what are my options?"
Agent: "Let me check your shipment. What's your shipment ID?"
User: "QS250020"
Agent: [Uses get_shipment_status]
Agent: "Your shipment QS250020 is In Transit, expected Nov 15."
Agent: [Uses search_knowledge_base('policies', 'delayed shipment options')]
Agent: "For delayed shipments, you have these options:
       1. Wait for delivery (no charge)
       2. Request priority delivery (₹50 extra)
       3. Cancel and refund (full refund)
       Would you like me to help with any of these?"
```

---

## Benefits of Hybrid Approach

### 1. Comprehensive Coverage
- ✅ Answers operational questions (shipments)
- ✅ Answers informational questions (policies)
- ✅ Handles complex queries requiring both

### 2. Accurate Responses
- Database queries return exact, real-time data
- Knowledge base provides detailed policy information
- No hallucination - all answers grounded in data

### 3. Flexible & Extensible
- Easy to add new database queries
- Easy to add new knowledge bases
- Agent automatically learns to use new tools

### 4. Better User Experience
- Single interface for all queries
- No need to switch between systems
- Natural conversation flow

---

## Data Flow

### Database Query Flow:
```
User Query
  ↓
Agent decides to use database tool
  ↓
Tool executes SQL query
  ↓
Returns structured data
  ↓
Agent formats response
  ↓
User receives answer
```

### Knowledge Base Query Flow:
```
User Query
  ↓
Agent decides to use KB tool
  ↓
Tool performs vector search (RAG)
  ↓
Retrieves relevant documents
  ↓
LLM generates answer from documents
  ↓
Agent formats response
  ↓
User receives answer
```

---

## Configuration

### Database Configuration
```python
# app/config/__init__.py
QUICKSHIP_DB_PATH = "QuickShip.db"
```

### Knowledge Base Configuration
```python
# app/config/__init__.py
QDRANT_URL = "https://..."
QDRANT_API_KEY = "..."
```

### Agent Configuration
```python
# app/services/agent_service_beta.py
model = "gemini-2.5-flash-lite"
temperature = 0.3
tools = [
    # Database tools
    get_shipment_status,
    search_shipments_by_customer,
    # ... more database tools
    
    # Knowledge base tools
    search_knowledge_base,
    list_available_knowledge_bases
]
```

---

## Adding New Capabilities

### Adding a New Database Tool:
```python
@tool
def get_delivery_boy_info(shipment_id: str) -> str:
    """Get delivery person information for a shipment"""
    # Query database
    # Return formatted result
```

### Adding a New Knowledge Base:
1. Upload documents to Qdrant (via UI)
2. Agent automatically has access via `search_knowledge_base` tool
3. No code changes needed!

---

## Performance Considerations

### Database Queries:
- **Speed:** Very fast (< 100ms)
- **Accuracy:** 100% (exact data)
- **Scalability:** Good (indexed queries)

### Knowledge Base Queries:
- **Speed:** Moderate (1-2 seconds)
- **Accuracy:** High (depends on documents)
- **Scalability:** Good (vector search)

### Combined Queries:
- **Speed:** Sum of both (2-3 seconds)
- **Accuracy:** High for both parts
- **Scalability:** Good

---

## Limitations

### Current Limitations:
1. Knowledge base search requires documents to be uploaded first
2. Agent can only search one KB at a time (not multiple simultaneously)
3. No caching of KB search results
4. English language only

### Future Enhancements:
- [ ] Multi-KB search in single query
- [ ] Caching for frequent KB queries
- [ ] Multi-language support
- [ ] Semantic caching for similar queries

---

## Monitoring & Analytics

### Metrics to Track:
- **Tool Usage Distribution:**
  - % Database tool calls
  - % Knowledge base tool calls
  - % Hybrid queries

- **Performance:**
  - Average response time per tool type
  - Success rate per tool
  - Error rate

- **User Behavior:**
  - Most common query types
  - KB search topics
  - Database query patterns

---

## Security Considerations

### Database Access:
- ✅ Parameterized queries (SQL injection prevention)
- ✅ Read-only access
- ✅ No sensitive data exposure

### Knowledge Base Access:
- ✅ Access control per collection
- ✅ No PII in documents
- ✅ Audit logging

---

## Conclusion

The hybrid agent architecture provides:
- **Versatility:** Handles both structured and unstructured data
- **Accuracy:** Grounded in real data (no hallucination)
- **Extensibility:** Easy to add new capabilities
- **User Experience:** Single interface for all queries

This makes it a powerful tool for customer service, combining the precision of database queries with the flexibility of document search.

---

**Version:** 1.0.0-beta  
**Last Updated:** November 17, 2025  
**Architecture Type:** Hybrid (Database + RAG)
