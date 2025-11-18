# QuickShip AI Agent (Beta) - README

## Overview
The QuickShip AI Agent is a conversational AI assistant that helps customers track shipments, check delivery status, and get information about their orders using natural language.

## Features

✅ **Implemented:**
- Natural language shipment tracking
- Search by phone number or email
- Delivery estimate queries
- Payment status checks
- Complaint status lookup
- **Knowledge base search** (policies, FAQs, procedures)
- Multi-turn conversations with context
- Session management
- Hybrid data access (database + documents)

## How to Enable

The beta agent is controlled by a feature flag in `.env`:

```bash
ENABLE_REACT_AGENT=true
```

Set to `false` to disable the feature.

## API Endpoints

### 1. Chat with Agent
```http
POST /api/v1/beta/agent/chat
Content-Type: application/json

{
  "session_id": "optional-uuid",
  "message": "Where is my order?"
}
```

**Response:**
```json
{
  "response": "I'd be happy to help! Could you provide your shipment ID or phone number?",
  "session_id": "uuid",
  "success": true
}
```

### 2. Get Conversation History
```http
GET /api/v1/beta/agent/history/{session_id}
```

### 3. Reset Conversation
```http
POST /api/v1/beta/agent/reset/{session_id}
```

## Using the UI

1. Start the application: `python run_app.py`
2. Open Streamlit UI: http://localhost:8501
3. Navigate to the "🧪 AI Agent (Beta)" tab
4. Start chatting!

## Example Conversations

### Example 1: Direct Query
```
User: Track QS250001
Agent: [Shows full shipment details with status, tracking, delivery info]
```

### Example 2: Missing Information
```
User: Where is my order?
Agent: I'd be happy to help! Could you provide your shipment ID or phone number?
User: 9224217802
Agent: I found 2 shipments for you:
       1. QS250001 - Delivered
       2. QS250022 - Delivered
       Which one would you like to know about?
```

### Example 3: Complex Query
```
User: My phone is 8786649843, when will my package arrive?
Agent: I found your shipment QS250021. It's currently Delivered!
       It was delivered on Dec 1, 2024 to Kolkata (700001).
```

### Example 4: Knowledge Base Query
```
User: What is your return policy?
Agent: [Searches knowledge base and provides policy information from documents]
```

### Example 5: Hybrid Query
```
User: My shipment is delayed, what are my options?
Agent: Let me check your shipment status first. Could you provide your shipment ID?
User: QS250020
Agent: [Checks database] Your shipment QS250020 is in transit, expected Dec 15.
       [Searches knowledge base] According to our policy, if a shipment is delayed
       beyond the expected date, you can request a refund or reschedule delivery.
```

## Available Tools

The agent has access to these tools:

**Shipment & Database Tools:**
1. **get_shipment_status** - Get full shipment details by ID
2. **search_shipments_by_customer** - Find shipments by phone/email
3. **track_by_tracking_number** - Track using tracking number
4. **get_delivery_estimate** - Get delivery date estimates
5. **check_cod_payment_status** - Check COD payment status
6. **get_complaint_status** - Check complaints for a shipment

**Knowledge Base Tools:**
7. **search_knowledge_base** - Search company documents (policies, FAQs, procedures)
8. **list_available_knowledge_bases** - List all available knowledge bases

## Database

The agent queries the QuickShip.db SQLite database with:
- 250 shipments
- 50 customers
- 20 delivery personnel
- Payment records
- Complaint tracking

## Testing

Run basic tests:
```bash
.venv\Scripts\python.exe tests/test_agent_basic.py
```

## Architecture

```
User Query
    ↓
Streamlit UI (tab4)
    ↓
FastAPI Endpoint (/api/v1/beta/agent/chat)
    ↓
Agent Service (agent_service_beta.py)
    ↓
ReAct Agent (LangChain + Gemini)
    ↓
Tools (agent_tools.py)
    ↓
QuickShip.db (SQLite)
```

## Configuration

Key settings in `agent_service_beta.py`:
- **Model**: gemini-2.5-flash-lite
- **Temperature**: 0.3 (balanced)
- **Max Iterations**: 5 (prevents loops)
- **Handle Parsing Errors**: True

## Limitations (Beta)

- Session storage is in-memory (resets on server restart)
- No authentication/authorization
- Limited to QuickShip database queries
- English language only
- No voice interface

## Troubleshooting

**Agent not responding:**
- Check if `ENABLE_REACT_AGENT=true` in `.env`
- Verify `GOOGLE_API_KEY` is set
- Check backend logs for errors

**Agent hallucinating:**
- This is a known issue with LLMs
- The agent is instructed to only use tool outputs
- Report specific cases for prompt improvement

**Slow responses:**
- First query may be slow (model initialization)
- Subsequent queries should be faster
- Check database connection

**Database errors:**
- Verify `QuickShip.db` exists in project root
- Check file permissions
- Ensure database is not corrupted

## Future Enhancements

- [ ] Persistent session storage (Redis)
- [ ] Multi-language support
- [ ] Voice interface
- [ ] Proactive notifications
- [ ] Integration with real carrier APIs
- [ ] Sentiment analysis
- [ ] Analytics dashboard
- [ ] A/B testing framework

## Support

For issues or questions:
1. Check the logs in `errorlog.txt`
2. Review the implementation plan: `docs/REACT_AGENT_IMPLEMENTATION.md`
3. See quick start guide: `docs/QUICKSTART_AGENT.md`

## Version

- **Version**: 1.0.0-beta
- **Last Updated**: November 17, 2025
- **Status**: Beta Testing

---

**Note**: This is a beta feature. Feedback and bug reports are welcome!
