# Agent vs RAG Endpoints - Important Difference

## The Problem

You have TWO different query systems, and your UI is calling the wrong one!

---

## System 1: Regular RAG Query (OLD)

**Endpoint:** `POST /api/v1/query/`

**What it does:**
- ONLY searches knowledge base documents
- No database access
- No intelligent routing
- Just RAG (Retrieval Augmented Generation)

**Request:**
```json
{
  "query": "where is my order",
  "kb_name": "test-demo",
  "chat_history": []
}
```

**Response:**
```json
{
  "answer": "Go to quickship.in/track and enter your tracking number..."
}
```

**Problem:** It can ONLY answer from documents, cannot query database!

---

## System 2: AI Agent (NEW - CORRECT ONE)

**Endpoint:** `POST /api/v1/beta/agent/chat`

**What it does:**
- ✅ Intelligently routes queries
- ✅ Can query database (shipment tracking)
- ✅ Can search knowledge base (policies)
- ✅ Decides which tool to use based on query
- ✅ Multi-turn conversations

**Request:**
```json
{
  "session_id": "user-123",
  "message": "where is my order",
  "knowledge_base": "test-demo"
}
```

**Response:**
```json
{
  "response": "I'd be happy to help! To find your shipment, I need...",
  "session_id": "user-123",
  "success": true
}
```

**Benefit:** Intelligently decides to ask for shipment ID/phone/email to query database!

---

## What's Happening in Your Logs

### Your Current Flow (WRONG):
```
User types: "where is my order"
  ↓
Frontend calls: POST /api/v1/query/
  ↓
RAG Service searches knowledge base
  ↓
Returns: "Go to quickship.in/track..." (generic answer from docs)
```

### What Should Happen (CORRECT):
```
User types: "where is my order"
  ↓
Frontend calls: POST /api/v1/beta/agent/chat
  ↓
Agent analyzes query
  ↓
Agent decides: "This is a tracking query, need more info"
  ↓
Agent asks: "Please provide shipment ID, phone, or email"
  ↓
User provides: "QS250001"
  ↓
Agent calls database tool
  ↓
Returns: Actual shipment status from database
```

---

## How to Fix

### Option 1: Update Frontend to Use Agent Endpoint

Change your chat interface to call:
```javascript
// WRONG (current)
fetch('/api/v1/query/', {
  method: 'POST',
  body: JSON.stringify({
    query: message,
    kb_name: selectedKB,
    chat_history: []
  })
})

// CORRECT (should be)
fetch('/api/v1/beta/agent/chat', {
  method: 'POST',
  body: JSON.stringify({
    session_id: sessionId,
    message: message,
    knowledge_base: selectedKB
  })
})
```

### Option 2: Keep Both, Add Toggle

Add a toggle in your UI:
- "RAG Mode" → Uses `/api/v1/query/` (document search only)
- "Agent Mode" → Uses `/api/v1/beta/agent/chat` (intelligent routing)

---

## Comparison Table

| Feature | RAG Endpoint | Agent Endpoint |
|---------|--------------|----------------|
| **Path** | `/api/v1/query/` | `/api/v1/beta/agent/chat` |
| **Database Access** | ❌ No | ✅ Yes |
| **KB Search** | ✅ Yes | ✅ Yes |
| **Intelligent Routing** | ❌ No | ✅ Yes |
| **Multi-turn Conversations** | ❌ No | ✅ Yes |
| **Tool Selection** | N/A | ✅ Automatic |
| **Session Management** | ❌ No | ✅ Yes |
| **Use Case** | Simple doc search | Full customer service |

---

## Example Queries

### Query: "Where is my order?"

**RAG Endpoint Response:**
```
"Go to quickship.in/track and enter your tracking number..."
```
(Generic answer from docs, not helpful)

**Agent Endpoint Response:**
```
"I'd be happy to help you track your order! To find your shipment, I need one of the following:
- Shipment ID (e.g., QS250001)
- Your phone number (10 digits)
- Your email address
- Tracking number (e.g., TRK123456789)"
```
(Intelligent, asks for what it needs)

### Query: "Track QS250001"

**RAG Endpoint Response:**
```
"Go to quickship.in/track and enter your tracking number..."
```
(Still generic, doesn't actually track)

**Agent Endpoint Response:**
```
"📦 Shipment QS250001
Status: In Transit
From: Mumbai
To: Delhi
Expected Delivery: Nov 26, 2024
Current Location: Pune Hub
..."
```
(Actual data from database!)

### Query: "What are your shipping rates?"

**RAG Endpoint Response:**
```
"Up to 1 kg: Same zone ₹55 | Nearby zone ₹80 | Far zone ₹120..."
```
(Works fine, searches docs)

**Agent Endpoint Response:**
```
"Up to 1 kg: Same zone ₹55 | Nearby zone ₹80 | Far zone ₹120..."
```
(Also works, searches KB)

---

## Summary

🔴 **Current Problem:** Your UI is calling `/api/v1/query/` which can ONLY search documents

🟢 **Solution:** Update UI to call `/api/v1/beta/agent/chat` which can:
- Query database for shipment tracking
- Search knowledge base for policies
- Intelligently decide which to use

---

## Quick Fix for Testing

Test the agent endpoint directly:

```bash
curl -X POST http://localhost:8000/api/v1/beta/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Track QS250001"
  }'
```

You should see it actually query the database!

---

**Status:** Agent endpoint is working correctly
**Issue:** Frontend calling wrong endpoint
**Fix:** Update frontend to use `/api/v1/beta/agent/chat`
