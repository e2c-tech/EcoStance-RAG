from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..db.database_connector import DatabaseConnector
from ..db.sql_query_generator import SQLQueryGenerator
from ..db.connection_manager import get_connection_manager
import asyncio
from urllib.parse import urlparse
from typing import Optional

router = APIRouter()

class DBConnectionRequest(BaseModel):
    db_uri: str

class QueryRequest(BaseModel):
    question: str

class ExecuteRequest(BaseModel):
    query: str

class SaveConnectionRequest(BaseModel):
    name: str
    db_type: str
    host: Optional[str] = None
    port: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    db_path: Optional[str] = None

db_connector: DatabaseConnector = None
query_generator: SQLQueryGenerator = None

def parse_db_uri(db_uri: str) -> dict:
    """Parse database URI into connection config dictionary"""
    parsed = urlparse(db_uri)
    
    if parsed.scheme == 'sqlite':
        # SQLite: sqlite:///path/to/db.db
        db_path = db_uri.replace('sqlite:///', '')
        return {
            'type': 'sqlite',
            'database': db_path
        }
    elif parsed.scheme in ['postgresql', 'postgres']:
        return {
            'type': 'postgresql',
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'username': parsed.username,
            'password': parsed.password,
            'database': parsed.path.lstrip('/')
        }
    elif parsed.scheme in ['mysql', 'mysql+pymysql', 'mysql+mysqlconnector']:
        return {
            'type': 'mysql',
            'host': parsed.hostname,
            'port': parsed.port or 3306,
            'username': parsed.username,
            'password': parsed.password,
            'database': parsed.path.lstrip('/')
        }
    elif parsed.scheme == 'mongodb':
        return {
            'type': 'mongodb',
            'host': parsed.hostname,
            'port': parsed.port or 27017,
            'database': parsed.path.lstrip('/')
        }
    else:
        raise ValueError(f"Unsupported database scheme: {parsed.scheme}")

@router.post("/db/connect")
async def connect_to_db(request: DBConnectionRequest):
    """
    Connects to a database using the provided connection details.
    """
    global db_connector, query_generator
    try:
        # Parse the URI into connection config
        connection_config = parse_db_uri(request.db_uri)
        
        # Initialize connector
        db_connector = DatabaseConnector()
        
        # The connect and get_schema_info methods in DatabaseConnector are synchronous,
        # so we run them in a thread pool to avoid blocking the event loop.
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, db_connector.connect, connection_config)
        
        schema = await loop.run_in_executor(None, db_connector.get_schema_info)
        if not isinstance(schema, dict):
            raise HTTPException(status_code=500, detail=f"Failed to retrieve schema: {schema}")
            
        query_generator = SQLQueryGenerator(schema)
        return {"message": "Database connection successful and schema loaded."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/db/generate-query")
async def generate_sql_query(request: QueryRequest):
    """
    Generates a SQL query from a natural language question.
    """
    if not query_generator:
        raise HTTPException(status_code=400, detail="Database not connected or schema not loaded.")
    
    result = await query_generator.generate_query(request.question)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result

@router.post("/db/execute-query")
async def execute_sql_query(request: ExecuteRequest):
    """
    Executes a SQL query against the connected database.
    """
    if not db_connector:
        raise HTTPException(status_code=400, detail="Database not connected.")
    
    # It's a good practice to re-verify the query's safety here.
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, db_connector.execute_query, request.query)
    
    if isinstance(results, dict):
        if not results.get('success', False):
            raise HTTPException(status_code=500, detail=results.get('error', 'Query execution failed'))
        
        # Return the rows if available
        if 'rows' in results:
            return results['rows']
        else:
            return {"message": results.get('message', 'Query executed successfully')}
    
    raise HTTPException(status_code=500, detail="Unexpected response format from database")

@router.post("/db/connections/save")
async def save_connection(request: SaveConnectionRequest):
    """
    Save a database connection profile securely.
    """
    try:
        connection_manager = get_connection_manager()
        
        connection_data = {
            'type': request.db_type,
            'host': request.host,
            'port': request.port,
            'username': request.username,
            'password': request.password,
            'database': request.database,
            'db_path': request.db_path
        }
        
        success = connection_manager.save_connection(request.name, connection_data)
        
        if success:
            return {"message": f"Connection '{request.name}' saved successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save connection")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/db/connections/list")
async def list_connections():
    """
    Get list of saved connection profiles.
    """
    try:
        connection_manager = get_connection_manager()
        connections = connection_manager.list_connections()
        
        # Get info for each connection (without passwords)
        connection_list = []
        for name in connections:
            info = connection_manager.get_connection_info(name)
            if info:
                connection_list.append({
                    'name': name,
                    'type': info.get('type', 'unknown'),
                    'host': info.get('host', ''),
                    'database': info.get('database', ''),
                    'username': info.get('username', '')
                })
        
        return connection_list
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/db/connections/{name}")
async def load_connection(name: str):
    """
    Load a saved connection profile (with decrypted password).
    """
    try:
        connection_manager = get_connection_manager()
        connection_data = connection_manager.load_connection(name)
        
        if connection_data is None:
            raise HTTPException(status_code=404, detail=f"Connection '{name}' not found")
        
        return connection_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/db/connections/{name}")
async def delete_connection(name: str):
    """
    Delete a saved connection profile.
    """
    try:
        connection_manager = get_connection_manager()
        success = connection_manager.delete_connection(name)
        
        if success:
            return {"message": f"Connection '{name}' deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Connection '{name}' not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
