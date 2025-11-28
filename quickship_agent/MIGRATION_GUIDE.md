# Migration Guide: Using QuickShip Agent in Your Existing Application

This guide helps you integrate the standalone QuickShip AI Agent package into your existing QuickShip application or any other application.

## Quick Migration Steps

### Step 1: Copy the Package

Copy the entire `quickship_agent` folder to your project:

```bash
# From your project root
cp -r /path/to/quickship_agent ./quickship_agent
```

Or install it as a package:

```bash
cd quickship_agent
pip install -e .
```

### Step 2: Update Your Imports

**Before (in your existing app):**
```python
from app.services.agent_service_beta import agent_service
from app.routers.agent_router_beta import router
```

**After (using the standalone package):**
```python
from quickship_agent import agent_service
from quickship_agent.router import router
```

### Step 3: Update FastAPI Router Registration

**Before:**
```python
# In app/main.py
from app.routers import agent_router_beta

if ENABLE_REACT_AGENT:
    app.include_router(
        agent_router_beta.router,
        prefix="/api/v1/beta",
        tags=["Agent Beta"]
    )
```

**After:**
```python
# In app/main.py or your main file
from quickship_agent.router import router as agent_router

app.include_router(
    agent_router,
    prefix="/api/v1/beta",
    tags=["AI Agent"]
)
```

### Step 4: Update Environment Variables

The standalone package uses the same environment variables, so no changes needed if you already have:

```env
GOOGLE_API_KEY=your_key
QDRANT_URL=your_url
QDRANT_API_KEY=your_key
QUICKSHIP_DB_PATH=QuickShip.db
```

### Step 5: Update UI Integration (if using Streamlit)

**Before:**
```python
# In ui/app.py
from app.services.agent_service_beta import agent_service
```

**After:**
```python
# In ui/app.py
from quickship_agent import agent_service
```

## Side-by-Side Comparison

### File Structure Mapping

| Original Location | New Location |
|------------------|--------------|
| `app/services/agent_service_beta.py` | `quickship_agent/agent_service.py` |
| `app/services/agent_tools.py` | `quickship_agent/tools/database_tools.py` + `knowledge_base_tools.py` |
| `app/routers/agent_router_beta.py` | `quickship_agent/router.py` |
| `app/services/query_service.py` | `quickship_agent/services/rag_service.py` |
| `app/services/qdrant_service.py` | `quickship_agent/services/qdrant_service.py` |

### API Endpoints (No Changes)

The API endpoints remain the same:
- `POST /api/v1/beta/agent/chat`
- `GET /api/v1/beta/agent/history/{session_id}`
- `POST /api/v1/beta/agent/reset/{session_id}`

### Request/Response Format (No Changes)

The request and response formats are identical:

```json
// Request
{
  "session_id": "optional-uuid",
  "message": "Track QS250001",
  "knowledge_base": "optional-kb-name"
}

// Response
{
  "response": "...",
  "session_id": "uuid",
  "success": true,
  "error": null
}
```

## Using in a Different Application

If you want to use this agent in a completely different application (not QuickShip):

### 1. Adapt Database Tools

Edit `quickship_agent/tools/database_tools.py` to match your database schema:

```python
# Change table names, column names, and queries
@tool
def get_order_status(order_id: str) -> str:
    """Your custom implementation"""
    query = """
    SELECT * FROM your_orders_table
    WHERE order_id = ?
    """
    # ... rest of your logic
```

### 2. Update System Prompt

Edit `quickship_agent/agent_service.py` to change the agent's personality and instructions:

```python
SYSTEM_PROMPT = """You are [YOUR COMPANY]'s AI assistant.

Your role:
- [Your specific role]
- [Your specific tasks]

Available Tools:
- [Your tools]

Guidelines:
- [Your guidelines]
"""
```

### 3. Add/Remove Tools

Remove tools you don't need:

```python
# In agent_service.py
self.tools = [
    # Remove tools you don't need
    # get_shipment_status,  # Remove this
    # Add your custom tools
    my_custom_tool,
]
```

### 4. Configure for Your Database

Update `config.py` or environment variables:

```env
# For PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost/dbname

# For MySQL
DATABASE_URL=mysql://user:pass@localhost/dbname

# For MongoDB
DATABASE_URL=mongodb://localhost:27017/dbname
```

Then update `database_tools.py` to use your database connection.

## Testing After Migration

### 1. Test Basic Functionality

```python
from quickship_agent import AgentService

agent = AgentService()
response = agent.chat(
    session_id="test-123",
    message="Hello"
)
print(response)
```

### 2. Test API Endpoints

```bash
# Start your server
python run_app.py

# Test the endpoint
curl -X POST "http://localhost:8000/api/v1/beta/agent/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Track QS250001"}'
```

### 3. Test UI Integration

If you have a Streamlit UI, test the chat interface to ensure it works correctly.

## Rollback Plan

If you need to rollback to the original implementation:

1. Keep the original files in `app/services/` and `app/routers/`
2. Switch imports back to the original:
   ```python
   from app.services.agent_service_beta import agent_service
   ```
3. Re-register the original router in `main.py`

## Benefits of Using the Standalone Package

✅ **Reusability**: Use the same agent in multiple applications
✅ **Maintainability**: Easier to update and maintain
✅ **Portability**: Share with other teams or projects
✅ **Versioning**: Can version the package independently
✅ **Testing**: Easier to test in isolation
✅ **Documentation**: Self-contained with examples

## Common Migration Issues

### Issue 1: Import Errors

**Problem**: `ModuleNotFoundError: No module named 'quickship_agent'`

**Solution**: 
```bash
# Install the package
cd quickship_agent
pip install -e .
```

### Issue 2: Database Connection Errors

**Problem**: Agent can't connect to database

**Solution**: Verify `QUICKSHIP_DB_PATH` in `.env` points to correct location

### Issue 3: Qdrant Connection Errors

**Problem**: Knowledge base search fails

**Solution**: Check `QDRANT_URL` and `QDRANT_API_KEY` are correct

### Issue 4: Different Response Format

**Problem**: UI expects different response format

**Solution**: Add a wrapper function:
```python
def legacy_chat(session_id, message, kb=None):
    response = agent_service.chat(session_id, message, kb)
    # Transform to legacy format if needed
    return response
```

## Next Steps

1. ✅ Complete the migration
2. ✅ Test all functionality
3. ✅ Update documentation
4. ✅ Train team on new structure
5. ✅ Monitor for issues
6. ✅ Consider adding new features

## Support

For migration help:
- Review `INTEGRATION_GUIDE.md` for detailed integration steps
- Check `examples/` directory for usage examples
- Review `README.md` for API reference

---

**Note**: The standalone package maintains 100% compatibility with the original implementation, so migration should be seamless!
