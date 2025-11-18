# ReAct Agent Implementation Plan (Beta/Experimental)

## Project Overview
Transform the current RAG system into an intelligent conversational agent for logistics operations that can:
- Ask follow-up questions when information is missing
- Decide when to query the database
- Handle multi-turn conversations with context
- Provide order tracking, shipment status, and delivery estimates

---

## Implementation Strategy

### Phase 1: Setup & Infrastructure (2-3 hours)

#### 1.1 Feature Flag Configuration
- [ ] Add `ENABLE_REACT_AGENT=false` to `.env`
- [ ] Create config variable in `app/config.py`
- [ ] Document how to enable/disable the feature

#### 1.2 Create Beta Module Structure
```
app/
├── routers/
│   └── agent_router_beta.py          # New beta agent endpoints
├── services/
│   ├── agent_service_beta.py         # ReAct agent logic
│   └── agent_tools.py                # Tool definitions for agent
└── prompts/
    └── agent_prompts.py              # System prompts for agent
```

#### 1.3 Dependencies
- [ ] Add to `requirements.txt`:
  ```
  langchain-core>=0.1.52
  langchain-google-genai>=1.0.2
  langgraph>=0.0.20  # For advanced agent workflows
  ```
- [ ] Install: `.venv\Scripts\python.exe -m pip install langgraph`

---

### Phase 2: Database Schema & Sample Data (COMPLETED ✓)

**Database Location:** `W:\EcoStance-RAG-db-connect\QuickShip.db`

#### 2.1 Existing Database Schema (QuickShip Logistics)

**customers** table:
- customer_id (PK)
- name, phone, email
- city, pincode
- joined_date
- total_orders, total_spent

**shipments** table:
- shipment_id (PK) - Format: QS250XXX
- tracking_number - Format: TRKXXXXXXXXX
- customer_id (FK)
- pickup_address, delivery_address, pincode
- weight_kg, charges, cod_amount
- shipment_date, expected_delivery_date, actual_delivery_date
- status (Delivered, In Transit, Booked, Lost, Returned, Out for Delivery)
- delivery_boy_id (FK)
- remarks

**delivery_boys** table:
- boy_id (PK)
- name, phone, city
- vehicle_number
- joined_date
- total_deliveries, on_time_percentage

**payments** table:
- payment_id (PK)
- shipment_id (FK)
- amount_paid, payment_mode (COD/Prepaid)
- payment_date, cod_collected_date

**complaints** table:
- complaint_id (PK)
- shipment_id (FK), customer_id (FK)
- complaint_type (Delay, Damage, Missing, Wrong item, Rude behaviour)
- date, status (Open, Resolved, Refunded)
- refund_amount

**daily_summary** table:
- date (PK)
- total_bookings, total_delivered
- total_cod_collected, total_revenue
- delayed_count

#### 2.2 Sample Data Status
- ✓ 250 shipments with realistic data
- ✓ 50 customers across major Indian cities
- ✓ 20 delivery personnel
- ✓ Various shipment statuses and scenarios
- ✓ Payment and complaint records

#### 2.3 Database Connection
- [x] Database already exists at `QuickShip.db`
- [ ] Update connection_manager.py to use QuickShip.db
- [ ] Create helper functions for common queries

---

### Phase 3: Agent Tools Development (3-4 hours)

#### 3.1 Core Tools to Implement

**Tool 1: get_shipment_status**
```python
@tool
def get_shipment_status(shipment_id: str) -> str:
    """
    Retrieves the current status of a shipment by shipment ID.
    Use this when customer provides their shipment ID (format: QS250XXX).
    
    Args:
        shipment_id: The shipment ID (e.g., QS250001)
    
    Returns:
        Shipment status, tracking number, delivery address, expected delivery date,
        actual delivery date (if delivered), charges, COD amount, and remarks
    """
```

**Tool 2: search_shipments_by_customer**
```python
@tool
def search_shipments_by_customer(phone: str = None, email: str = None) -> str:
    """
    Search for shipments by customer phone or email.
    Use when customer doesn't have shipment ID but provides contact info.
    
    Args:
        phone: Customer phone number (10 digits)
        email: Customer email address
    
    Returns:
        List of shipments for that customer with status and dates
    """
```

**Tool 3: track_by_tracking_number**
```python
@tool
def track_by_tracking_number(tracking_number: str) -> str:
    """
    Get detailed tracking information using tracking number.
    Use when customer provides tracking number (format: TRKXXXXXXXXX).
    
    Args:
        tracking_number: Shipment tracking number
    
    Returns:
        Current status, location, expected delivery, and delivery boy details
    """
```

**Tool 4: get_delivery_estimate**
```python
@tool
def get_delivery_estimate(shipment_id: str) -> str:
    """
    Get estimated or actual delivery date for a shipment.
    Use when customer asks "when will my shipment arrive?"
    
    Args:
        shipment_id: The shipment ID
    
    Returns:
        Expected delivery date, actual delivery date (if delivered), 
        and current status
    """
```

**Tool 5: check_customer_shipments**
```python
@tool
def check_customer_shipments(customer_id: int = None, phone: str = None) -> str:
    """
    Get all shipments for a customer with summary.
    Use when customer asks about their shipment history.
    
    Args:
        customer_id: Customer ID (if known)
        phone: Customer phone number
    
    Returns:
        List of all shipments with status, total spent, and order count
    """
```

**Tool 6: check_cod_payment_status**
```python
@tool
def check_cod_payment_status(shipment_id: str) -> str:
    """
    Check if COD payment has been collected for a shipment.
    Use when customer asks about payment or COD collection.
    
    Args:
        shipment_id: The shipment ID
    
    Returns:
        Payment mode, amount, payment status, and collection date
    """
```

**Tool 7: get_complaint_status**
```python
@tool
def get_complaint_status(shipment_id: str) -> str:
    """
    Check if there are any complaints for a shipment.
    Use when customer asks about issues or complaints.
    
    Args:
        shipment_id: The shipment ID
    
    Returns:
        Complaint details, status, type, and refund information
    """
```

#### 3.2 Tool Implementation Checklist
- [ ] Create `app/services/agent_tools.py`
- [ ] Implement each tool with proper error handling
- [ ] Add logging for tool invocations
- [ ] Write unit tests for each tool
- [ ] Add tool descriptions that guide agent behavior

---

### Phase 4: ReAct Agent Implementation (4-5 hours)

#### 4.1 Agent Service Setup
- [ ] Create `app/services/agent_service_beta.py`
- [ ] Initialize LangChain ReAct agent with Gemini
- [ ] Configure conversation memory (ConversationBufferMemory)
- [ ] Register all tools with the agent

#### 4.2 System Prompt Engineering
Create comprehensive system prompt that includes:
- [ ] Agent role: "You are a helpful logistics customer service agent"
- [ ] Behavior guidelines:
  - Always be polite and professional
  - Ask for missing information before querying database
  - Provide clear, concise answers
  - Offer proactive help (e.g., "Would you like tracking details?")
- [ ] Examples of good conversations
- [ ] Edge case handling (order not found, multiple orders, etc.)

#### 4.3 Agent Configuration
```python
# Key settings to configure:
- temperature: 0.3 (balanced creativity/consistency)
- max_iterations: 5 (prevent infinite loops)
- early_stopping_method: "generate" (graceful stopping)
- handle_parsing_errors: True (robust error handling)
```

#### 4.4 Conversation Flow Logic
- [ ] Implement session management (track conversations by session_id)
- [ ] Add conversation history persistence
- [ ] Implement context window management (summarize old messages)
- [ ] Add conversation reset functionality

---

### Phase 5: API Endpoints (2-3 hours)

#### 5.1 Create Beta Router
File: `app/routers/agent_router_beta.py`

**Endpoint 1: Chat with Agent**
```python
POST /api/v1/beta/agent/chat
{
    "session_id": "uuid",
    "message": "Where is my order?",
    "context": {}  # Optional additional context
}

Response:
{
    "response": "I'd be happy to help! Could you provide your order ID?",
    "needs_input": true,
    "suggested_actions": ["provide_order_id", "provide_email"],
    "agent_thoughts": "User wants order status but hasn't provided ID"
}
```

**Endpoint 2: Get Conversation History**
```python
GET /api/v1/beta/agent/history/{session_id}

Response:
{
    "session_id": "uuid",
    "messages": [...],
    "created_at": "timestamp"
}
```

**Endpoint 3: Reset Conversation**
```python
POST /api/v1/beta/agent/reset/{session_id}

Response:
{
    "message": "Conversation reset successfully"
}
```

#### 5.2 Integration with Main App
- [ ] Conditionally include router in `app/main.py` based on feature flag
- [ ] Add proper error handling and logging
- [ ] Implement rate limiting (optional)

---

### Phase 6: UI Implementation (3-4 hours)

#### 6.1 Add Beta Tab to Streamlit UI
File: `ui/app.py`

- [ ] Add new tab: "🧪 AI Agent (Beta)"
- [ ] Add beta warning banner
- [ ] Implement chat interface similar to existing chat
- [ ] Add visual indicators for:
  - Agent thinking/reasoning
  - Tool usage (show when DB is queried)
  - Follow-up questions highlighted differently

#### 6.2 UI Features
- [ ] Session management (new conversation button)
- [ ] Show agent's reasoning process (optional toggle)
- [ ] Display tool calls in expandable sections
- [ ] Add feedback buttons (helpful/not helpful)
- [ ] Export conversation feature

#### 6.3 UI Helper Functions
```python
def chat_with_agent(session_id, message):
    """Send message to agent and get response"""
    
def get_agent_history(session_id):
    """Retrieve conversation history"""
    
def reset_agent_conversation(session_id):
    """Start new conversation"""
```

---

### Phase 7: Testing & Validation (3-4 hours)

#### 7.1 Unit Tests
- [ ] Test each tool independently
- [ ] Test agent initialization
- [ ] Test conversation memory
- [ ] Test error handling

#### 7.2 Integration Tests
- [ ] Test complete conversation flows
- [ ] Test multi-turn conversations
- [ ] Test edge cases:
  - Invalid order IDs
  - Multiple orders for same customer
  - Missing information scenarios
  - Database connection failures

#### 7.3 Conversation Scenarios to Test
1. **Happy Path**: User provides order ID immediately
2. **Missing Info**: User asks vague question, agent asks for details
3. **Multiple Orders**: Customer has multiple orders, agent helps narrow down
4. **Order Not Found**: Handle gracefully, offer alternatives
5. **Complex Query**: "Where is my order and when will it arrive?"
6. **Follow-up Questions**: Multi-turn conversation with context

#### 7.4 Create Test Script
- [ ] Create `tests/test_agent_scenarios.py`
- [ ] Implement automated conversation testing
- [ ] Add performance benchmarks (response time)

---

### Phase 8: Documentation (2 hours)

#### 8.1 User Documentation
- [ ] Create `docs/AGENT_USER_GUIDE.md`
- [ ] Document how to enable beta feature
- [ ] Provide example conversations
- [ ] List supported queries
- [ ] FAQ section

#### 8.2 Developer Documentation
- [ ] Document agent architecture
- [ ] Explain tool creation process
- [ ] Add code examples for extending tools
- [ ] Document prompt engineering guidelines

#### 8.3 API Documentation
- [ ] Update OpenAPI/Swagger docs
- [ ] Add example requests/responses
- [ ] Document error codes

---

### Phase 9: Monitoring & Observability (2-3 hours)

#### 9.1 Logging
- [ ] Log all agent interactions
- [ ] Log tool invocations with parameters
- [ ] Log reasoning steps (for debugging)
- [ ] Log errors and exceptions

#### 9.2 Metrics to Track
- [ ] Conversation success rate
- [ ] Average turns per conversation
- [ ] Tool usage frequency
- [ ] Response time per query
- [ ] Error rate

#### 9.3 Debugging Tools
- [ ] Add verbose mode for development
- [ ] Create agent trace viewer
- [ ] Add conversation replay functionality

---

## Technical Considerations

### Security
- [ ] Sanitize all user inputs
- [ ] Validate order IDs before DB queries
- [ ] Implement rate limiting per session
- [ ] Add authentication for sensitive operations
- [ ] Prevent SQL injection in tool queries

### Performance
- [ ] Cache frequent queries
- [ ] Optimize database queries
- [ ] Implement connection pooling
- [ ] Set reasonable timeouts
- [ ] Consider async operations for tools

### Scalability
- [ ] Use Redis for session storage (future)
- [ ] Implement conversation archiving
- [ ] Consider message queue for high load
- [ ] Plan for horizontal scaling

---

## Rollout Plan

### Stage 1: Internal Testing (Week 1)
- Deploy with feature flag OFF by default
- Enable for development environment only
- Test with team members
- Gather feedback and iterate

### Stage 2: Limited Beta (Week 2-3)
- Enable for select users
- Monitor performance and errors
- Collect user feedback
- Fix critical issues

### Stage 3: Open Beta (Week 4+)
- Make available to all users (opt-in)
- Add prominent beta label
- Continue monitoring and improving
- Plan for GA release

---

## Success Metrics

### Quantitative
- 80%+ of conversations successfully resolve user query
- Average conversation length: 2-4 turns
- Response time: < 3 seconds per message
- Error rate: < 5%

### Qualitative
- Users prefer agent over manual DB queries
- Positive feedback on conversation quality
- Agent correctly identifies when to ask follow-ups
- Natural conversation flow

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Agent makes incorrect DB queries | High | Extensive testing, query validation, human review option |
| Slow response times | Medium | Optimize queries, implement caching, set timeouts |
| Agent gets stuck in loops | Medium | Max iteration limits, early stopping, reset option |
| Hallucination/incorrect info | High | Strict tool-only responses, fact-checking, disclaimers |
| High API costs (Gemini) | Medium | Rate limiting, caching, monitor usage |

---

## Future Enhancements (Post-Beta)

- [ ] Multi-language support
- [ ] Voice interface integration
- [ ] Proactive notifications (order updates)
- [ ] Integration with shipping carrier APIs
- [ ] Customer sentiment analysis
- [ ] Automated issue resolution (refunds, returns)
- [ ] Analytics dashboard for agent performance
- [ ] A/B testing framework for prompt optimization

---

## Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Setup | 2-3 hours | None |
| Phase 2: Database | 2-3 hours | Phase 1 |
| Phase 3: Tools | 3-4 hours | Phase 2 |
| Phase 4: Agent | 4-5 hours | Phase 3 |
| Phase 5: API | 2-3 hours | Phase 4 |
| Phase 6: UI | 3-4 hours | Phase 5 |
| Phase 7: Testing | 3-4 hours | Phase 6 |
| Phase 8: Docs | 2 hours | Phase 7 |
| Phase 9: Monitoring | 2-3 hours | Phase 7 |

**Total Estimated Time: 24-32 hours** (3-4 working days)

---

## Getting Started

1. Enable feature flag: Set `ENABLE_REACT_AGENT=true` in `.env`
2. Install dependencies: `.venv\Scripts\python.exe -m pip install langgraph`
3. Create database schema: Run `scripts/create_logistics_db.sql`
4. Start with Phase 1 and work sequentially
5. Test each phase before moving to next

---

## Questions to Resolve

- [ ] Which database to use for logistics data? (SQLite for dev, PostgreSQL for prod?)
- [ ] Session storage strategy? (In-memory, Redis, Database?)
- [ ] Authentication requirements for beta users?
- [ ] Budget for Gemini API calls during beta?
- [ ] Feedback collection mechanism?

---

## Resources & References

- LangChain ReAct Agent: https://python.langchain.com/docs/modules/agents/agent_types/react
- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- Tool Creation Guide: https://python.langchain.com/docs/modules/agents/tools/
- Conversation Memory: https://python.langchain.com/docs/modules/memory/

---

**Document Version:** 1.0  
**Last Updated:** November 17, 2025  
**Status:** Planning Phase  
**Owner:** Development Team
