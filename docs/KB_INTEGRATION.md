# Knowledge Base Integration with AI Agent

## Overview

The AI Agent now uses the **selected knowledge base from the sidebar** when searching documents. This provides a seamless experience where users can:
1. Select a knowledge base in the sidebar
2. Use the AI Agent to query both shipments AND that specific knowledge base

---

## How It Works

### User Flow:

```
1. User selects KB in sidebar (e.g., "company_policies")
   ↓
2. User goes to "🧪 AI Agent (Beta)" tab
   ↓
3. Agent shows: "📚 Knowledge Base: company_policies"
   ↓
4. User asks: "What is your return policy?"
   ↓
5. Agent searches the selected KB automatically
   ↓
6. Agent returns answer from company_policies KB
```

### Technical Flow:

```
UI (Sidebar)
  ↓ selected_kb
UI (Agent Tab)
  ↓ knowledge_base parameter
API Endpoint (/beta/agent/chat)
  ↓ knowledge_base
Agent Service
  ↓ session_kb[session_id]
search_knowledge_base tool
  ↓ collection_name
Qdrant Vector DB
```

---

## Changes Made

### 1. API Endpoint (`app/routers/agent_router_beta.py`)
```python
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    knowledge_base: Optional[str] = None  # NEW: Selected KB
```

### 2. Agent Service (`app/services/agent_service_beta.py`)
```python
def chat(self, session_id: str, message: str, knowledge_base: str = None):
    # Store KB for this session
    if knowledge_base:
        self.session_kb[session_id] = knowledge_base
    
    # Add KB context to system prompt
    kb_context = f"Use collection: '{knowledge_base}'"
```

### 3. UI (`ui/app.py`)
```python
# Show selected KB
st.info(f"📚 Knowledge Base: {selected_kb}")

# Pass KB to agent
result = chat_with_agent(
    session_id, 
    message,
    knowledge_base=selected_kb  # Pass from sidebar
)
```

---

## Example Scenarios

### Scenario 1: KB Selected
```
Sidebar: "company_policies" selected
Agent Tab: Shows "📚 Knowledge Base: company_policies"

User: "What is your return policy?"
Agent: [Searches company_policies KB]
       "According to our policy: Returns accepted within 30 days..."
```

### Scenario 2: No KB Selected
```
Sidebar: No KB selected
Agent Tab: Shows "📚 Knowledge Base: None selected"

User: "What is your return policy?"
Agent: "I don't have access to a knowledge base. Please select one from the sidebar."
```

### Scenario 3: Hybrid Query
```
Sidebar: "shipping_procedures" selected
Agent Tab: Shows "📚 Knowledge Base: shipping_procedures"

User: "My order QS250001 is delayed, what should I do?"
Agent: [Checks database for QS250001 status]
       [Searches shipping_procedures for delay policy]
       "Your order is in transit, expected Nov 15.
        According to our procedures, for delays you can..."
```

---

## Benefits

### 1. Context-Aware Search
- Agent knows which KB to search
- No need to specify KB in every query
- Consistent results within a session

### 2. User-Friendly
- Visual indicator of selected KB
- Clear feedback on what data is available
- Seamless integration with existing UI

### 3. Flexible
- Can switch KB by selecting different one in sidebar
- Works with any KB uploaded to the system
- Falls back gracefully if no KB selected

---

## UI Indicators

### When KB is Selected:
```
📚 Knowledge Base: company_policies (Agent will search this KB for document queries)
```

### When No KB is Selected:
```
📚 Knowledge Base: None selected (Agent can only query shipment database)
```

---

## Session Management

### KB Persistence:
- KB selection is stored per session
- Persists across multiple queries in same session
- Resets when "New Conversation" is clicked

### Changing KB:
1. Select different KB in sidebar
2. Send new message in agent
3. Agent uses new KB for that query onwards

---

## API Usage

### Request with KB:
```json
POST /api/v1/beta/agent/chat
{
  "session_id": "uuid",
  "message": "What is your return policy?",
  "knowledge_base": "company_policies"
}
```

### Request without KB:
```json
POST /api/v1/beta/agent/chat
{
  "session_id": "uuid",
  "message": "Track QS250001"
}
```

---

## Tool Behavior

### `search_knowledge_base` Tool:
```python
@tool
def search_knowledge_base(collection_name: str, query: str) -> str:
    """
    Search through company knowledge base documents.
    
    Args:
        collection_name: The KB to search (auto-filled from session)
        query: The search query
    """
```

**Before:** Agent had to guess which KB to search  
**After:** Agent uses the KB selected in sidebar

---

## Error Handling

### No KB Selected:
```
User: "What is your return policy?"
Agent: "I don't have access to a knowledge base. 
        Please select one from the sidebar to search documents."
```

### KB Not Found:
```
User: "What is your return policy?"
Agent: "I couldn't find the knowledge base 'old_policies'. 
        Please check if it exists."
```

### KB Search Error:
```
User: "What is your return policy?"
Agent: "I encountered an error searching the knowledge base. 
        Please try again."
```

---

## Testing

### Test Cases:

1. **Test with KB selected:**
   - Select KB in sidebar
   - Ask document question
   - Verify agent searches correct KB

2. **Test without KB:**
   - Don't select KB
   - Ask document question
   - Verify agent handles gracefully

3. **Test KB switching:**
   - Select KB1
   - Ask question
   - Select KB2
   - Ask question
   - Verify agent uses KB2

4. **Test hybrid queries:**
   - Select KB
   - Ask question needing both DB and KB
   - Verify agent uses both sources

---

## Future Enhancements

- [ ] Multi-KB search (search across multiple KBs)
- [ ] KB auto-detection (agent guesses best KB)
- [ ] KB recommendations (suggest relevant KBs)
- [ ] KB search history (show which KBs were searched)

---

**Version:** 1.1.0-beta  
**Last Updated:** November 17, 2025  
**Feature:** KB Integration with Sidebar Selection
