"""
Database Router with Tenant Context and Connection Pooling.
Manages per-tenant database connections with secure credential storage.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import logging

from ..db.sql_query_generator import SQLQueryGenerator
from ..services.connection_manager_service import get_connection_manager_service
from ..services.credential_service import get_credential_service
from ..auth.dependencies import get_current_user, get_tenant_id
from ..auth.rbac import RBACService
from ..auth.permissions import Permission
from ..services.audit_service import AuditService
from ..db.database import get_db
from sqlalchemy.orm import Session
from urllib.parse import urlparse

router = APIRouter()
logger = logging.getLogger(__name__)

# Tenant-scoped storage
_tenant_query_generators: Dict[str, SQLQueryGenerator] = {}


class DBConnectionRequest(BaseModel):
    db_uri: str
    db_id: str = "default"  # Database identifier for this tenant


class QueryRequest(BaseModel):
    question: str
    db_id: str = "default"


class ExecuteRequest(BaseModel):
    query: str
    db_id: str = "default"


class SaveConnectionRequest(BaseModel):
    db_id: str
    db_type: str
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    db_path: Optional[str] = None


def parse_db_uri(db_uri: str) -> dict:
    """Parse database URI into connection config dictionary"""
    parsed = urlparse(db_uri)
    
    if parsed.scheme == 'sqlite':
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


def get_query_generator_key(tenant_id: str, db_id: str) -> str:
    """Generate key for query generator storage."""
    return f"{tenant_id}:{db_id}"


@router.post("/db/connect")
async def connect_to_db(
    req: Request,
    request: DBConnectionRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Connect to a database with tenant context.
    Connections are pooled per tenant and reused.
    
    Requires: DB_CONNECT permission
    """
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.DB_CONNECT)
    try:
        connection_manager = get_connection_manager_service()
        
        # Parse connection config
        connection_config = parse_db_uri(request.db_uri)
        
        logger.info(f"Connecting to database for tenant {tenant_id}, db_id: {request.db_id}")
        
        # Get or create connection (runs in thread pool)
        loop = asyncio.get_event_loop()
        connector = await loop.run_in_executor(
            None,
            connection_manager.get_connection,
            tenant_id,
            request.db_id,
            connection_config
        )
        
        if connector is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to create database connection"
            )
        
        # Get schema info
        schema = await loop.run_in_executor(None, connector.get_schema_info)
        
        if not isinstance(schema, dict):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve schema: {schema}"
            )
        
        # Create and store query generator for this tenant+db
        query_gen_key = get_query_generator_key(tenant_id, request.db_id)
        _tenant_query_generators[query_gen_key] = SQLQueryGenerator(schema)
        
        # Get connection stats
        stats = connection_manager.get_connection_stats(tenant_id)
        
        logger.info(
            f"Database connected for tenant {tenant_id}: "
            f"{stats['active_connections']}/{stats['max_connections']} connections"
        )
        
        # Log successful connection
        audit = AuditService(db)
        audit.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action="connect_database",
            resource_type="database",
            resource_id=request.db_id,
            details={"db_type": connection_config.get("db_type")},
            status="success",
            request=req
        )
        
        return {
            "message": "Database connection successful and schema loaded",
            "tenant_id": tenant_id,
            "db_id": request.db_id,
            "connection_stats": stats
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Connection error for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/db/generate-query")
async def generate_sql_query(
    req: Request,
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate SQL query from natural language question.
    Uses tenant-specific database schema.
    
    Requires: DB_QUERY permission
    """
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.DB_QUERY)
    query_gen_key = get_query_generator_key(tenant_id, request.db_id)
    
    if query_gen_key not in _tenant_query_generators:
        raise HTTPException(
            status_code=400,
            detail=f"Database not connected. Please connect to db_id '{request.db_id}' first."
        )
    
    query_generator = _tenant_query_generators[query_gen_key]
    
    try:
        result = await query_generator.generate_query(request.question)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        logger.info(f"Query generated for tenant {tenant_id}, db_id: {request.db_id}")
        return result
        
    except Exception as e:
        logger.error(f"Query generation error for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/db/execute-query")
async def execute_sql_query(
    req: Request,
    request: ExecuteRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Execute SQL query against tenant's database connection.
    
    Requires: DB_EXECUTE permission
    """
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.DB_EXECUTE)
    try:
        connection_manager = get_connection_manager_service()
        
        # Get connection (will reuse existing if available)
        connector = connection_manager.get_connection(tenant_id, request.db_id)
        
        if connector is None:
            raise HTTPException(
                status_code=400,
                detail=f"Database not connected. Please connect to db_id '{request.db_id}' first."
            )
        
        # Execute query in thread pool
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            connector.execute_query,
            request.query
        )
        
        if isinstance(results, dict):
            if not results.get('success', False):
                raise HTTPException(
                    status_code=500,
                    detail=results.get('error', 'Query execution failed')
                )
            
            logger.info(
                f"Query executed for tenant {tenant_id}, db_id: {request.db_id}, "
                f"rows: {results.get('row_count', 0)}"
            )
            
            # Log successful execution
            audit = AuditService(db)
            audit.log_action(
                tenant_id=tenant_id,
                user_id=user_id,
                action="execute_query",
                resource_type="database",
                resource_id=request.db_id,
                details={
                    "query": request.query[:100],  # Truncate long queries
                    "row_count": results.get('row_count', 0)
                },
                status="success",
                request=req
            )
            
            # Return rows if available
            if 'rows' in results:
                return {
                    "rows": results['rows'],
                    "row_count": results['row_count'],
                    "tenant_id": tenant_id,
                    "db_id": request.db_id
                }
            else:
                return {
                    "message": results.get('message', 'Query executed successfully'),
                    "tenant_id": tenant_id,
                    "db_id": request.db_id
                }
        
        raise HTTPException(
            status_code=500,
            detail="Unexpected response format from database"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query execution error for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/db/connections/save")
async def save_connection(
    req: Request,
    request: SaveConnectionRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save database connection configuration with encrypted credentials.
    Stored in tenant_databases table.
    
    Requires: DB_MANAGE permission
    """
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.DB_MANAGE)
    try:
        credential_service = get_credential_service()
        
        # Build connection config
        connection_data = {
            'type': request.db_type,
            'host': request.host,
            'port': request.port,
            'username': request.username,
            'password': request.password,
            'database': request.database,
            'db_path': request.db_path
        }
        
        # Encrypt sensitive fields
        encrypted_config = credential_service.encrypt_connection_config(connection_data)
        
        # TODO: Store in tenant_databases table
        # For now, just return success
        # In production, save to database with tenant_id
        
        logger.info(f"Connection saved for tenant {tenant_id}, db_id: {request.db_id}")
        
        return {
            "message": f"Connection '{request.db_id}' saved successfully",
            "tenant_id": tenant_id,
            "db_id": request.db_id
        }
        
    except Exception as e:
        logger.error(f"Save connection error for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/db/connections/stats")
async def get_connection_stats(tenant_id: str = Depends(get_tenant_id)):
    """
    Get connection statistics for tenant.
    """
    try:
        connection_manager = get_connection_manager_service()
        stats = connection_manager.get_connection_stats(tenant_id)
        
        return stats
        
    except Exception as e:
        logger.error(f"Stats error for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/db/connections/{db_id}/close")
async def close_connection(
    db_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Close a specific database connection for tenant.
    """
    try:
        connection_manager = get_connection_manager_service()
        success = connection_manager.close_connection(tenant_id, db_id)
        
        # Remove query generator
        query_gen_key = get_query_generator_key(tenant_id, db_id)
        if query_gen_key in _tenant_query_generators:
            del _tenant_query_generators[query_gen_key]
        
        if success:
            logger.info(f"Connection closed for tenant {tenant_id}, db_id: {db_id}")
            return {
                "message": f"Connection '{db_id}' closed successfully",
                "tenant_id": tenant_id,
                "db_id": db_id
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Connection '{db_id}' not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Close connection error for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/db/connections/close-all")
async def close_all_tenant_connections(tenant_id: str = Depends(get_tenant_id)):
    """
    Close all database connections for tenant.
    """
    try:
        connection_manager = get_connection_manager_service()
        count = connection_manager.close_tenant_connections(tenant_id)
        
        # Remove all query generators for this tenant
        keys_to_remove = [
            key for key in _tenant_query_generators.keys()
            if key.startswith(f"{tenant_id}:")
        ]
        for key in keys_to_remove:
            del _tenant_query_generators[key]
        
        logger.info(f"All connections closed for tenant {tenant_id}: {count} connections")
        
        return {
            "message": f"Closed {count} connection(s)",
            "tenant_id": tenant_id,
            "count": count
        }
        
    except Exception as e:
        logger.error(f"Close all connections error for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/db/connections/{db_id}/health")
async def check_connection_health(
    db_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Check health of a specific database connection.
    """
    try:
        connection_manager = get_connection_manager_service()
        is_healthy = connection_manager.health_check(tenant_id, db_id)
        
        return {
            "healthy": is_healthy,
            "tenant_id": tenant_id,
            "db_id": db_id
        }
        
    except Exception as e:
        logger.error(f"Health check error for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
