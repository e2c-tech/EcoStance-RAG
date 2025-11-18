# QuickShip Agent - Quick Start Guide

## Overview
Build a conversational AI agent for QuickShip logistics that can handle customer queries about shipments, track packages, and provide delivery estimates.

---

## What You Have

✅ **Database:** `QuickShip.db` with 250 shipments, 50 customers  
✅ **Current System:** RAG-based document Q&A  
✅ **Infrastructure:** FastAPI backend + Streamlit UI  

---

## What We're Building

A ReAct agent that can:
1. **Ask follow-up questions** when info is missing
2. **Query the database** intelligently
3. **Handle conversations** naturally
4. **Provide accurate** shipment information

---

## Example Conversations

### Scenario 1: Missing Information
```
User: "Where is my order?"
Agent: "I'd be happy to help! Could you provide your shipment ID or phone number?"
User: "9224217802"
Agent: [Uses search_shipments_by_customer tool]
Agent: "I found 2 shipments for you:
       - QS250001: Delivered on Oct 25
       - QS250022: Delivered on Oct 14
       Which one would you like to know about?"
```

### Scenario 2: Direct Query
```
User: "Track QS250020"
Agent: [Uses get_shipment_status tool]
Agent: "Your shipment QS250020 is currently In Transit.
       Tracking: TRK849965936
       Expected delivery: Nov 15, 2024
       Destination: Delhi (110065)"
```

### Scenario 3: Complex Query
```
User: "When will my package arrive? My phone is 8786649843"
Agent: [Uses search_shipments_by_customer, then get_delivery_estimate]
Agent: "I found your shipment QS250021. It's currently Delivered!
       It was delivered on Dec 1, 2024 to Kolkata (700001).
       Would you like tracking details?"
```

---

## Implementation Steps (Simplified)

### Step 1: Enable Feature Flag (1 min)
```bash
# Add to .env
ENABLE_REACT_AGENT=true
```

### Step 2: Install Dependencies (2 min)
```bash
.venv\Scripts\python.exe -m pip install langgraph
```

### Step 3: Create Agent Tools (30 min)
Create `app/services/agent_tools.py` with 7 tools that query QuickShip.db

### Step 4: Create Agent Service (45 min)
Create `app/services/agent_service_beta.py` with ReAct agent setup

### Step 5: Add API Endpoint (15 min)
Create `app/routers/agent_router_beta.py` with `/beta/agent/chat` endpoint

### Step 6: Add UI Tab (30 min)
Add "🧪 AI Agent (Beta)" tab to `ui/app.py`

### Step 7: Test (30 min)
Test various conversation scenarios

**Total Time: ~2.5 hours for MVP**

---

## Database Queries You'll Need

### Get Shipment by ID
```sql
SELECT s.*, c.name, c.phone, c.email, d.name as delivery_boy_name
FROM shipments s
JOIN customers c ON s.customer_id = c.customer_id
LEFT JOIN delivery_boys d ON s.delivery_boy_id = d.boy_id
WHERE s.shipment_id = ?
```

### Search by Phone
```sql
SELECT s.shipment_id, s.tracking_number, s.status, 
       s.expected_delivery_date, s.actual_delivery_date
FROM shipments s
JOIN customers c ON s.customer_id = c.customer_id
WHERE c.phone = ?
ORDER BY s.shipment_date DESC
```

### Get Payment Status
```sql
SELECT p.*, s.cod_amount, s.charges
FROM payments p
JOIN shipments s ON p.shipment_id = s.shipment_id
WHERE p.shipment_id = ?
```

### Check Complaints
```sql
SELECT complaint_type, status, date, refund_amount
FROM complaints
WHERE shipment_id = ?
```

---

## Agent System Prompt Template

```python
SYSTEM_PROMPT = """You are QuickShip's helpful customer service agent.

Your role:
- Help customers track their shipments
- Provide delivery estimates
- Answer questions about payments and complaints
- Always be polite and professional

Guidelines:
1. If customer doesn't provide shipment ID, ask for phone number or email
2. If multiple shipments found, list them and ask which one they want
3. Use tools to get accurate information from database
4. Never make up information - only use data from tools
5. If shipment is delayed, acknowledge and provide expected date
6. For complaints, check complaint status and inform customer

Available information:
- Shipment status (Delivered, In Transit, Booked, etc.)
- Tracking numbers
- Delivery dates (expected and actual)
- Payment status (COD/Prepaid)
- Complaint status
- Delivery personnel details

Always end with: "Is there anything else I can help you with?"
"""
```

---

## Tool Implementation Example

```python
from langchain.tools import tool
import sqlite3

DB_PATH = "W:/EcoStance-RAG-db-connect/QuickShip.db"

@tool
def get_shipment_status(shipment_id: str) -> str:
    """
    Retrieves the current status of a shipment by shipment ID.
    Use this when customer provides their shipment ID (format: QS250XXX).
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        query = """
        SELECT s.shipment_id, s.tracking_number, s.status, 
               s.delivery_address, s.expected_delivery_date, 
               s.actual_delivery_date, s.charges, s.cod_amount, s.remarks,
               c.name, c.phone
        FROM shipments s
        JOIN customers c ON s.customer_id = c.customer_id
        WHERE s.shipment_id = ?
        """
        
        cursor.execute(query, (shipment_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return f"No shipment found with ID {shipment_id}"
        
        return f"""
Shipment ID: {result[0]}
Tracking Number: {result[1]}
Status: {result[2]}
Delivery Address: {result[3]}
Expected Delivery: {result[4]}
Actual Delivery: {result[5] or 'Not yet delivered'}
Charges: ₹{result[6]}
COD Amount: ₹{result[7]}
Customer: {result[9]} ({result[10]})
Remarks: {result[8] or 'None'}
"""
    except Exception as e:
        return f"Error retrieving shipment: {str(e)}"
```

---

## Testing Checklist

- [ ] Agent asks for shipment ID when not provided
- [ ] Agent searches by phone number correctly
- [ ] Agent handles multiple shipments for same customer
- [ ] Agent provides accurate delivery dates
- [ ] Agent checks payment status when asked
- [ ] Agent handles "shipment not found" gracefully
- [ ] Agent maintains conversation context
- [ ] Agent doesn't hallucinate information

---

## Common Customer Queries to Handle

1. "Where is my order?"
2. "Track my shipment QS250XXX"
3. "When will my package arrive?"
4. "Has my COD been collected?"
5. "I have a complaint about my delivery"
6. "Show me all my orders"
7. "What's the status of tracking number TRKXXXXXXX?"
8. "My shipment is delayed, what happened?"

---

## Next Steps After MVP

1. Add proactive notifications
2. Integrate with real carrier APIs
3. Add ability to update delivery address
4. Handle refund requests
5. Multi-language support
6. Voice interface
7. Analytics dashboard

---

## Troubleshooting

**Agent not using tools:**
- Check tool descriptions are clear
- Verify database connection
- Check agent temperature (should be low, ~0.3)

**Agent hallucinating:**
- Add strict instructions to only use tool outputs
- Lower temperature
- Add examples in system prompt

**Slow responses:**
- Optimize database queries (add indexes)
- Cache frequent queries
- Use async operations

**Agent stuck in loops:**
- Set max_iterations limit (5-7)
- Add early stopping
- Provide clear exit conditions

---

## Resources

- LangChain Tools: https://python.langchain.com/docs/modules/agents/tools/
- ReAct Paper: https://arxiv.org/abs/2210.03629
- LangGraph: https://langchain-ai.github.io/langgraph/

---

**Ready to start?** Begin with Step 1 and work through sequentially. Each step builds on the previous one.

Good luck! 🚀
