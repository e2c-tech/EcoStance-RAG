from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from ..db.database_connector import DatabaseConnector
from ..db.sql_query_generator import SQLQueryGenerator
from ..db.connection_manager import get_connection_manager
from ..auth.dependencies import get_current_user
from ..services.file_access_service import get_file_access_service
import asyncio
from urllib.parse import urlparse
from typing import Optional
import os
from sqlalchemy.orm import Session
from ..db.database import get_db

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
            'database': parsed.path.lstrip('/'),
            'query': parsed.query
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
async def save_connection(
    request: SaveConnectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Save a database connection profile securely for the current tenant.
    """
    try:
        tenant_id = current_user["tenant_id"]
        connection_manager = get_connection_manager()
        
        # Prefix connection name with tenant_id for isolation
        internal_name = f"{tenant_id}_{request.name}"
        
        connection_data = {
            'type': request.db_type,
            'host': request.host,
            'port': request.port,
            'username': request.username,
            'password': request.password,
            'database': request.database,
            'db_path': request.db_path,
            'tenant_id': tenant_id  # Store tenant_id in connection data
        }
        
        success = connection_manager.save_connection(internal_name, connection_data)
        
        if success:
            return {"message": f"Connection '{request.name}' saved successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save connection")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/db/connections/list")
async def list_connections(
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of saved connection profiles for the current tenant.
    """
    try:
        tenant_id = current_user["tenant_id"]
        connection_manager = get_connection_manager()
        all_connections = connection_manager.list_connections()
        
        # Filter connections by tenant - connections should be prefixed with tenant_id
        tenant_prefix = f"{tenant_id}_"
        
        # Get info for each connection belonging to this tenant (without passwords)
        connection_list = []
        for name in all_connections:
            # Only include connections that belong to this tenant
            if name.startswith(tenant_prefix):
                info = connection_manager.get_connection_info(name)
                if info:
                    # Remove tenant prefix from display name
                    display_name = name[len(tenant_prefix):]
                    connection_list.append({
                        'name': display_name,
                        'internal_name': name,  # Keep full name for internal use
                        'type': info.get('type', 'unknown'),
                        'host': info.get('host', ''),
                        'database': info.get('database', ''),
                        'username': info.get('username', '')
                    })
        
        return connection_list
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/db/connections/{name}")
async def load_connection(
    name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Load a saved connection profile (with decrypted password) for the current tenant.
    Returns connection data with a ready-to-use db_uri field.
    """
    try:
        tenant_id = current_user["tenant_id"]
        connection_manager = get_connection_manager()
        
        # Prefix connection name with tenant_id for isolation
        internal_name = f"{tenant_id}_{name}"
        connection_data = connection_manager.load_connection(internal_name)
        
        if connection_data is None:
            raise HTTPException(status_code=404, detail=f"Connection '{name}' not found")
        
        # Verify tenant_id matches (extra security check)
        if connection_data.get('tenant_id') != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied to this connection")
        
        # Generate db_uri for easy connection
        db_type = connection_data.get('type')
        
        if db_type == 'sqlite':
            # For SQLite, database field contains the full URI or path
            db_path = connection_data.get('database') or connection_data.get('db_path')
            if db_path and db_path.startswith('sqlite:///'):
                connection_data['db_uri'] = db_path
            else:
                connection_data['db_uri'] = f"sqlite:///{db_path}"
        elif db_type in ['postgresql', 'postgres']:
            host = connection_data.get('host')
            port = connection_data.get('port', 5432)
            username = connection_data.get('username')
            password = connection_data.get('password')
            database = connection_data.get('database')
            connection_data['db_uri'] = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        elif db_type == 'mysql':
            host = connection_data.get('host')
            port = connection_data.get('port', 3306)
            username = connection_data.get('username')
            password = connection_data.get('password')
            database = connection_data.get('database')
            connection_data['db_uri'] = f"mysql://{username}:{password}@{host}:{port}/{database}"
        elif db_type == 'mongodb':
            host = connection_data.get('host')
            port = connection_data.get('port', 27017)
            database = connection_data.get('database')
            connection_data['db_uri'] = f"mongodb://{host}:{port}/{database}"
        
        return connection_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/db/connections/{name}")
async def delete_connection(
    name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a saved connection profile for the current tenant.
    Use '__empty__' as the name to delete connections with empty names.
    """
    try:
        tenant_id = current_user["tenant_id"]
        connection_manager = get_connection_manager()
        
        # Handle empty name deletion
        if name == "__empty__":
            name = ""
        
        # Prefix connection name with tenant_id for isolation
        internal_name = f"{tenant_id}_{name}" if name else f"{tenant_id}_"
        
        # Verify the connection belongs to this tenant before deleting
        connection_data = connection_manager.get_connection_info(internal_name)
        if connection_data and connection_data.get('tenant_id') != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied to this connection")
        
        success = connection_manager.delete_connection(internal_name)
        
        if success:
            display_name = "unnamed connection" if name == "" else f"'{name}'"
            return {"message": f"Connection {display_name} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Connection '{name}' not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/db/upload-sqlite")
async def upload_sqlite_database(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a SQLite database file for use with the AI Agent.
    Returns the file path that can be used with /db/connect endpoint.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    tenant_id = current_user["tenant_id"]
    
    # Validate file type
    allowed_extensions = ['.db', '.sqlite', '.sqlite3']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only SQLite files ({', '.join(allowed_extensions)}) are allowed."
        )
    
    # Check file size (max 100MB)
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    max_size = 100 * 1024 * 1024  # 100MB
    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds maximum allowed size of {max_size / (1024*1024):.0f}MB"
        )
    
    try:
        # Create tenant-specific database directory
        file_service = get_file_access_service()
        base_dir = file_service.ensure_tenant_directory(tenant_id)
        db_dir = os.path.join(base_dir, "databases")
        os.makedirs(db_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(db_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Generate SQLite URI
        # Convert to absolute path and normalize for SQLite
        abs_path = os.path.abspath(file_path)
        # Convert Windows backslashes to forward slashes for SQLite URI
        abs_path = abs_path.replace('\\', '/')
        sqlite_uri = f"sqlite:///{abs_path}"
        
        logger.info(f"SQLite database uploaded for tenant {tenant_id}: {file.filename}")
        
        return {
            "message": "SQLite database uploaded successfully",
            "file_path": sqlite_uri,
            "filename": file.filename,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "tenant_id": tenant_id
        }
        
    except Exception as e:
        logger.error(f"Failed to upload SQLite database: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")


@router.get("/db/status")
async def get_connection_status():
    """
    Get the current database connection status.
    Returns information about the connected database or null if not connected.
    """
    if not db_connector:
        return {
            "connected": False,
            "database": None
        }
    
    try:
        # Get basic connection info
        connection_info = {
            "connected": True,
            "database": {
                "type": db_connector.db_type,
                "status": "active"
            }
        }
        
        # Add database-specific info
        if db_connector.db_type in ['postgresql', 'mysql']:
            connection_info["database"]["host"] = getattr(db_connector.engine.url, 'host', 'unknown')
            connection_info["database"]["database"] = getattr(db_connector.engine.url, 'database', 'unknown')
        elif db_connector.db_type == 'sqlite':
            connection_info["database"]["path"] = str(db_connector.engine.url.database)
        elif db_connector.db_type == 'mongodb':
            connection_info["database"]["host"] = db_connector.client.address[0] if db_connector.client else 'unknown'
            connection_info["database"]["database"] = db_connector.db.name if db_connector.db else 'unknown'
        
        return connection_info
        
    except Exception as e:
        return {
            "connected": True,
            "database": {
                "type": db_connector.db_type if db_connector else "unknown",
                "status": "error",
                "error": str(e)
            }
        }


@router.get("/db/schema")
async def get_database_schema():
    """
    Get the schema of the currently connected database.
    Returns list of tables with their columns and types.
    """
    if not db_connector:
        raise HTTPException(status_code=400, detail="Database not connected. Please connect to a database first.")
    
    try:
        loop = asyncio.get_event_loop()
        schema = await loop.run_in_executor(None, db_connector.get_schema_info)
        
        if not isinstance(schema, dict):
            raise HTTPException(status_code=500, detail=f"Failed to retrieve schema: {schema}")
        
        # Transform schema into frontend-friendly format
        tables = []
        
        # Handle SQL databases (has 'tables' key)
        if 'tables' in schema:
            for table_name, table_info in schema['tables'].items():
                columns = []
                # Columns is a list of dicts with name, type, nullable, default
                for col in table_info.get('columns', []):
                    columns.append({
                        "name": col['name'],
                        "type": col['type'],
                        "nullable": col.get('nullable', True),
                        "default": col.get('default')
                    })
                
                tables.append({
                    "name": table_name,
                    "columns": columns,
                    "primary_keys": table_info.get('primary_keys', []),
                    "foreign_keys": table_info.get('foreign_keys', [])
                })
        
        # Handle MongoDB (has 'collections' key)
        elif 'collections' in schema:
            for collection_name, collection_info in schema['collections'].items():
                fields = collection_info.get('fields', {})
                columns = []
                for field_name, field_type in fields.items():
                    columns.append({
                        "name": field_name,
                        "type": field_type
                    })
                
                tables.append({
                    "name": collection_name,
                    "columns": columns
                })
        
        return {
            "tables": tables,
            "relationships": schema.get('relationships', [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving schema: {str(e)}")
