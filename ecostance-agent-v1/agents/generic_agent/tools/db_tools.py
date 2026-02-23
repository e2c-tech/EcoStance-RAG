import logging
from langchain.tools import tool
from app.db.database_connector import DatabaseConnector
from app.db.connection_manager import get_connection_manager
from sqlalchemy import text

logger = logging.getLogger(__name__)

def create_db_query_tool(db_connection: str = None, tenant_id: str = None):
    """
    Creates a tool to query a specific database connection.
    
    Args:
        db_connection: Can be a saved connection name or a raw database URI.
        tenant_id: Optional tenant ID for prefixing connection names.
    """
    @tool
    def query_database(query: str) -> str:
        """
        Query the connected database using SQL (SQLite, PostgreSQL, MySQL). 
        IMPORTANT: NEVER guess column names. You MUST call 'list_database_tables' first 
        to see the schema (tables and columns) before writing your SQL query.
        """
        connector = None
        current_db_conn = db_connection
        
        logger.info(f"query_database called. current_db_conn: {current_db_conn}, tenant_id: {tenant_id}")
        
        # 1. Fallback to active global connector if no db_connection provided
        if not current_db_conn:
            logger.info("No specific db_connection provided, checking global db_router.db_connector")
            from app.routers import db_router
            if db_router.db_connector and (db_router.db_connector.engine or db_router.db_connector.client):
                # Use the active global connector directly
                logger.info("Using active global database connector")
                result = db_router.db_connector.execute_query(query)
                if not result.get('success'):
                    return f"Error: {result.get('error')}"
                if 'rows' in result:
                    return str(result['rows']) if result['rows'] else "Query executed successfully. No rows found."
                return f"Query executed successfully. Result: {result.get('message')}"
            else:
                logger.warning("No global database connector found.")
                return "Error: Database connection is not active. If you just reloaded the code, please go to the Database Interaction page and click 'Connect' again to restore the connection."
            
        connector = DatabaseConnector()
        try:
            # 2. Try to load as a saved connection first
            connection_manager = get_connection_manager()
            
            # Try with tenant prefix first, then raw name
            conn_data = None
            if tenant_id:
                prefixed_name = f"{tenant_id}_{current_db_conn}"
                logger.info(f"Attempting to load prefixed connection: {prefixed_name}")
                conn_data = connection_manager.load_connection(prefixed_name)
            
            if not conn_data:
                logger.info(f"Attempting to load raw connection: {current_db_conn}")
                conn_data = connection_manager.load_connection(current_db_conn)
            
            if conn_data:
                logger.info(f"Successfully loaded connection data for: {current_db_conn}")
                connector.connect(conn_data)
            else:
                # 3. Try to parse as a URI (if it looks like one)
                if '://' in current_db_conn:
                    logger.info("Using raw database URI from parameter")
                    from app.routers.db_router import parse_db_uri
                    conn_config = parse_db_uri(current_db_conn)
                    connector.connect(conn_config)
                else:
                    logger.error(f"Database connection '{current_db_conn}' not found (tenant: {tenant_id})")
                    return f"Error: Database connection '{current_db_conn}' was not found in saved connections. Please ensure the connection name is correct or pass a full database URI."
            
            # 4. Execute query
            result = connector.execute_query(query)
            
            if not result.get('success'):
                return f"Error from database: {result.get('error')}"
                
            if 'rows' in result:
                rows = result['rows']
                if not rows:
                    return "Query executed successfully. Result: No rows found."
                return str(rows)
            else:
                return f"Query executed successfully. Result: {result.get('message')}"
                
        except Exception as e:
            logger.error(f"Exception during query_database: {str(e)}", exc_info=True)
            return f"Error connecting to database '{current_db_conn}': {str(e)}"
        finally:
            if connector and (connector.engine or connector.client):
                connector.close_connection()
            
    return query_database

def create_list_db_tables_tool(db_connection: str = None, tenant_id: str = None):
    """Creates a tool to list tables in the database to help the agent discover the schema."""
    @tool
    def list_database_tables() -> str:
        """
        List all tables AND their column names/types available in the connected database.
        Use this to discover schema details. CALL THIS FIRST before using 'query_database'.
        """
        connector = None
        current_db_conn = db_connection
        
        logger.info(f"list_database_tables called. current_db_conn: {current_db_conn}, tenant_id: {tenant_id}")
        
        # Fallback to active global connector
        if not current_db_conn:
            from app.routers import db_router
            if db_router.db_connector and (db_router.db_connector.engine or db_router.db_connector.client):
                logger.info("Using active global database connector for schema")
                schema = db_router.db_connector.get_schema_info()
                if 'tables' in schema:
                    table_details = []
                    for table_name, table_info in schema['tables'].items():
                        cols = [f"{c['name']} ({c['type']})" for c in table_info.get('columns', [])]
                        table_details.append(f"Table '{table_name}': {', '.join(cols)}")
                    return "Available tables and their columns:\n" + "\n".join(table_details)
                elif 'collections' in schema:
                    coll_details = []
                    for coll_name, coll_info in schema['collections'].items():
                        fields = [f"{f} ({t})" for f, t in coll_info.get('fields', {}).items()]
                        coll_details.append(f"Collection '{coll_name}': {', '.join(fields)}")
                    return "Available collections and their fields:\n" + "\n".join(coll_details)
                return "The database is connected but no tables or collections were found."
            else:
                return "Error: No active database connection found. If the server recently reloaded, please re-connect your database in the 'Database Interaction' tab."
                
        connector = DatabaseConnector()
        try:
            connection_manager = get_connection_manager()
            
            # Try with tenant prefix first, then raw name
            conn_data = None
            if tenant_id:
                prefixed_name = f"{tenant_id}_{current_db_conn}"
                conn_data = connection_manager.load_connection(prefixed_name)
            
            if not conn_data:
                conn_data = connection_manager.load_connection(current_db_conn)
            
            # Fallback to URI parsing
            if not conn_data and '://' in current_db_conn:
                from app.routers.db_router import parse_db_uri
                conn_data = parse_db_uri(current_db_conn)
            
            if not conn_data:
                return f"Error: Could not find connection details for '{current_db_conn}'."
                
            connector.connect(conn_data)
            schema = connector.get_schema_info()
            if 'tables' in schema:
                table_details = []
                for table_name, table_info in schema['tables'].items():
                    cols = [f"{c['name']} ({c['type']})" for c in table_info.get('columns', [])]
                    table_details.append(f"Table '{table_name}': {', '.join(cols)}")
                return "Available tables and their columns:\n" + "\n".join(table_details)
            elif 'collections' in schema:
                coll_details = []
                for coll_name, coll_info in schema['collections'].items():
                    fields = [f"{f} ({t})" for f, t in coll_info.get('fields', {}).items()]
                    coll_details.append(f"Collection '{coll_name}': {', '.join(fields)}")
                return "Available collections and their fields:\n" + "\n".join(coll_details)
            return "No tables found in the specified database."
        except Exception as e:
            logger.error(f"Exception during list_database_tables: {str(e)}", exc_info=True)
            return f"Error listing tables for '{current_db_conn}': {str(e)}"
        finally:
            if connector and (connector.engine or connector.client):
                connector.close_connection()
                
    return list_database_tables
