# QuickShip AI Agent - Quick Reference Card

## 🚀 Installation (30 seconds)

```bash
cd quickship_agent
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
```

## 💻 Basic Usage (3 lines)

```python
from quickship_agent import AgentService
agent = AgentService()
response = agent.chat("session-123", "Track QS250001")
```

## 🔌 FastAPI Integration (4 lines)

```python
from fastapi import FastAPI
from quickship_agent.router import router

app = FastAPI()
app.include_router(router, prefix="/api/v1")
```

## 📡 API Endpoints

```bash
# Chat
POST /api/v1/agent/chat
Body: {"session_id": "123", "message": "Track order", "knowledge_base": "faq"}

# History
GET /api/v1/agent/history/{session_id}

# Reset
POST /api/v1/agent/reset/{session_id}
```

## 🛠️ Available Tools

### Database Tools (6)
1. `get_shipment_status(shipment_id)` - Get shipment details
2. `search_shipments_by_customer(phone, email)` - Find by contact
3. `track_by_tracking_number(tracking_number)` - Track by number
4. `get_delivery_estimate(shipment_id)` - Get delivery date
5. `check_cod_payment_status(shipment_id)` - Check payment
6. `get_complaint_status(shipment_id)` - Check complaints

### Knowledge Base Tools (2)
1. `search_knowledge_base(collection, query)` - Search docs
2. `list_available_knowledge_bases()` - List KBs

## 🎨 Customization Points

### 1. System Prompt
```python
# In agent_service.py
SYSTEM_PROMPT = """Your custom prompt here"""
```

### 2. Add Tool
```python
from langchain.tools import tool

@tool
def my_tool(param: str) -> str:
    """Description"""
    return result

# Register in agent_service.py
self.tools.append(my_tool)
```

### 3. Database Query
```python
# In tools/database_tools.py
@tool
def my_query(param: str) -> str:
    conn = get_db_connection()
    cursor.execute("SELECT * FROM table WHERE id = ?", (param,))
    return format_result(cursor.fetchone())
```

### 4. Change Model
```env
# In .env
AGENT_MODEL=gemini-1.5-pro
AGENT_TEMPERATURE=0.5
```

## 🔧 Configuration

### Environment Variables
```env
GOOGLE_API_KEY=your_key
QDRANT_URL=your_url
QDRANT_API_KEY=your_key
QUICKSHIP_DB_PATH=path/to/db
AGENT_MODEL=gemini-2.5-flash-lite
AGENT_TEMPERATURE=0.3
```

## 📊 Response Format

```python
{
    "response": "Agent's answer",
    "session_id": "uuid",
    "success": true,
    "error": null
}
```

## 🐛 Common Issues

### Import Error
```bash
pip install -e .
```

### API Key Error
```bash
# Check .env file exists and has valid key
cat .env | grep GOOGLE_API_KEY
```

### Database Error
```bash
# Verify database path
ls -la QuickShip.db
```

## 📁 File Structure

```
quickship_agent/
├── agent_service.py      # Main agent logic
├── router.py             # FastAPI endpoints
├── config.py             # Configuration
├── tools/
│   ├── database_tools.py # DB tools
│   └── knowledge_base_tools.py # KB tools
├── services/
│   ├── qdrant_service.py # Vector DB
│   └── rag_service.py    # RAG logic
└── examples/             # Usage examples
```

## 🧪 Quick Test

```python
# Test 1: Basic chat
from quickship_agent import agent_service
r = agent_service.chat("test", "Track QS250001")
print(r["response"])

# Test 2: Multi-turn
r1 = agent_service.chat("test2", "Where is my order?")
r2 = agent_service.chat("test2", "My phone is 9224217802")
print(r2["response"])

# Test 3: History
history = agent_service.get_conversation_history("test2")
print(f"Messages: {len(history)}")
```

## 🔄 Migration from Original

```python
# Before
from app.services.agent_service_beta import agent_service
from app.routers.agent_router_beta import router

# After
from quickship_agent import agent_service
from quickship_agent.router import router
```

## 📚 Documentation Files

- **README.md** - Overview & quick start
- **INTEGRATION_GUIDE.md** - Detailed integration
- **MIGRATION_GUIDE.md** - Migration steps
- **ARCHITECTURE.md** - System design
- **CHECKLIST.md** - Integration checklist
- **PACKAGE_SUMMARY.md** - Package overview

## 🎯 Example Queries

```python
# Shipment tracking
"Track QS250001"
"Where is my order?"
"My phone is 9224217802"
"Track TRK123456789"

# Delivery info
"When will my package arrive?"
"Delivery estimate for QS250001"

# Payment
"Check payment status for QS250001"
"Has COD been collected?"

# Knowledge base
"What is your return policy?"
"What are your shipping rates?"
"How long does delivery take?"
```

## 🚀 Production Deployment

```python
# 1. Use secrets manager
import boto3
secrets = boto3.client('secretsmanager')

# 2. Add Redis for sessions
import redis
redis_client = redis.Redis(host='localhost', port=6379)

# 3. Add monitoring
from prometheus_client import Counter
requests_total = Counter('agent_requests_total', 'Total requests')

# 4. Add rate limiting
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

# 5. Run with gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

## 💡 Pro Tips

1. **Cache frequent queries** for better performance
2. **Use streaming** for long responses
3. **Implement retry logic** for API calls
4. **Monitor token usage** to control costs
5. **Update prompts regularly** based on user feedback
6. **Use connection pooling** for database
7. **Implement circuit breakers** for external APIs
8. **Log all interactions** for debugging
9. **Version your prompts** for A/B testing
10. **Set up alerts** for high error rates

## 📞 Quick Help

```bash
# View logs
tail -f agent.log

# Check dependencies
pip list | grep langchain

# Test database connection
python -c "from quickship_agent.tools.database_tools import get_db_connection; print(get_db_connection())"

# Test Qdrant connection
python -c "from quickship_agent.services.qdrant_service import get_qdrant_client; print(get_qdrant_client().get_collections())"
```

## 🎓 Learning Path

1. ✅ Read README.md (5 min)
2. ✅ Try basic_usage.py (5 min)
3. ✅ Read INTEGRATION_GUIDE.md (15 min)
4. ✅ Customize for your needs (30 min)
5. ✅ Test thoroughly (30 min)
6. ✅ Deploy to production (varies)

---

**Keep this card handy for quick reference!** 📌

Print it out or bookmark this page for easy access.
