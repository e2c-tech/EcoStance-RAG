# AI Agent Dynamic Database Support - TODO

## Current Status

✅ **Agent now checks if database is connected**
- If user tries to query shipments without connecting to a DB, agent asks them to connect first
- Agent receives `database_connection` parameter from UI

❌ **Database tools still use hardcoded path**
- Tools use `QUICKSHIP_DB_PATH` from `.env` file
- Need to make tools use the dynamically selected database

---

## What Works Now

### Request Format
```json
{
  "session_id": "user-123",
  "message": "Track QS250001",
  "knowledge_base": "test-demo",
  "database_connection": "logistics-demo"
}
```

### Agent Behavior
1. ✅ Receives database_connection parameter
2. ✅ Stores it in session: `self.session_db[session_id] = database_connection`
3. ✅ Checks if DB is connected before executing database tools
4. ✅ Shows helpful message if no DB connected
5. ❌ Still uses hardcoded `QuickShip.db` from `.env`

---

## What Needs to Be Done

### Option 1: Use Connection Manager (Recommended)

Modify `quickship_agent/tools/database_tools.py` to:

1. **Import connection manager:**
```python
from app.db.connection_manager import get_connection_manager
```

2. **Create dynamic connection function:**
```python
def get_db_connection_dynamic(connection_name: str = None):
    """Get database connection from connection manager or fallback to default"""
    if connection_name:
        # Load from connection manager
        connection_manager = get_connection_manager()
        connection_data = connection_manager.load_connection(connection_name)
        
        if connection_data:
            db_uri = connection_data.get('db_uri')
            # Parse and connect based on db_uri
            if db_uri.startswith('sqlite:///'):
                db_path = db_uri.replace('sqlite:///', '')
                conn = sqlite3.connect(db_path)
            elif db_uri.startswith('postgresql://'):
                # Use psycopg2
                conn = psycopg2.connect(db_uri)
            # etc.
            return conn
    
    # Fallback to default
    return sqlite3.connect(QUICKSHIP_DB_PATH)
```

3. **Update all tools to accept connection parameter:**
```python
@tool
def get_shipment_status(shipment_id: str, _db_connection: str = None) -> str:
    """..."""
    conn = get_db_connection_dynamic(_db_connection)
    # rest of code...
```

### Option 2: Global Database State (Simpler)

Create a global database connection manager in the agent service:

```python
class AgentService:
    def __init__(self):
        # ...
        self.db_connections = {}  # Store active connections
    
    def _get_or_create_db_connection(self, connection_name: str):
        """Get or create database connection"""
        if connection_name not in self.db_connections:
            # Load from connection manager and create connection
            connection_manager = get_connection_manager()
            connection_data = connection_manager.load_connection(connection_name)
            # Create and store connection
            self.db_connections[connection_name] = create_connection(connection_data)
        
        return self.db_connections[connection_name]
```

Then pass the connection to tools somehow (this is tricky with LangChain tools).

### Option 3: Environment Variable Switching (Quick Hack)

Before executing database tools, temporarily update the environment:

```python
import os
from ..config import QUICKSHIP_DB_PATH

# In agent_service.py, before tool execution:
if tool_name in db_tools and session_id in self.session_db:
    # Load connection and get db_path
    connection_manager = get_connection_manager()
    connection_data = connection_manager.load_connection(self.session_db[session_id])
    
    if connection_data:
        db_uri = connection_data.get('db_uri')
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            
            # Temporarily override the config
            old_path = QUICKSHIP_DB_PATH
            import quickship_agent.config as config
            config.QUICKSHIP_DB_PATH = db_path
            
            # Execute tool
            result = tool.invoke(tool_args)
            
            # Restore
            config.QUICKSHIP_DB_PATH = old_path
```

---

## Recommended Approach

**Use Option 1** - Modify database tools to accept connection parameter.

### Implementation Steps:

1. **Update `quickship_agent/tools/database_tools.py`:**
   - Add `_db_connection` parameter to all tool functions
   - Create `get_db_connection_dynamic()` helper
   - Update all tools to use dynamic connection

2. **Update `quickship_agent/agent_service.py`:**
   - When executing database tools, pass `_db_connection` in tool_args
   - Already done: Check if DB is connected

3. **Test:**
   - Connect to different databases in UI
   - Verify agent queries the correct database

---

## Current Workaround

For now, users must:
1. Connect to a database in the UI (e.g., "logistics-demo")
2. Manually update `.env` to point to that database:
   ```env
   QUICKSHIP_DB_PATH=path/to/logistics-demo.db
   ```
3. Restart the server

This is not ideal but works until dynamic database support is implemented.

---

## Files to Modify

1. `quickship_agent/tools/database_tools.py` - Add dynamic connection support
2. `quickship_agent/agent_service.py` - Pass connection to tools (already partially done)
3. `quickship_agent/config.py` - Maybe add connection manager import

---

## Testing

After implementation, test with:

```bash
# Test 1: No database connected
curl -X POST http://localhost:8000/api/v1/beta/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Track QS250001"}'

# Expected: "Please connect to a database first..."

# Test 2: Database connected
curl -X POST http://localhost:8000/api/v1/beta/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Track QS250001",
    "database_connection": "logistics-demo"
  }'

# Expected: Actual shipment data from logistics-demo database
```

---

**Status:** Partial implementation complete
**Priority:** HIGH (needed for production use)
**Estimated Time:** 2-3 hours
