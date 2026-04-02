import logging
from langchain.tools import tool

logger = logging.getLogger(__name__)


def _get_global_connector():
    """Return the active global db_connector set by /db/connect, or None."""
    from app.routers import db_router
    connector = db_router.db_connector
    if connector and (connector.engine or connector.client):
        return connector
    return None


def create_db_query_tool(db_connection: str = None, tenant_id: str = None):
    @tool
    def get_data_from_connected_database(sql_query: str) -> str:
        """
        Run a SQL query against the connected database to retrieve structured data.
        Use this for ANY question about data that lives in the database — products,
        orders, customers, inventory, sales, shipments, analytics, counts, filters, etc.
        
        RULES:
        - You MUST call 'get_database_schema' first to know the table and column names.
        - NEVER guess column names — always check schema first.
        - Use this tool BEFORE web_search for anything that could be in the database.
        
        Args:
            sql_query: A valid SQL SELECT statement
        """
        logger.info(f"get_data_from_connected_database called. tenant_id: {tenant_id}")

        connector = _get_global_connector()
        if not connector:
            return (
                "Error: No active database connection. "
                "Please go to the Database page, select your connection and click Connect."
            )

        result = connector.execute_query(sql_query)

        if not result.get('success'):
            return f"Error: {result.get('error')}"
        if 'rows' in result:
            rows = result['rows']
            return str(rows) if rows else "Query executed successfully. No rows found."
        return f"Query executed successfully. {result.get('message', '')}"

    return get_data_from_connected_database


def create_list_db_tables_tool(db_connection: str = None, tenant_id: str = None):
    @tool
    def list_database_tables() -> str:
        """
        Get the full schema of the connected database — all table names and their columns.
        ALWAYS call this FIRST before writing any SQL query so you know the exact
        table names and column names. Never skip this step.
        """
        logger.info(f"list_database_tables called. tenant_id: {tenant_id}")

        connector = _get_global_connector()
        if not connector:
            return (
                "Error: No active database connection. "
                "Please go to the Database page, select your connection and click Connect."
            )

        schema = connector.get_schema_info()

        if 'tables' in schema:
            if not schema['tables']:
                return "The database is connected but no tables were found."
            table_details = []
            for table_name, table_info in schema['tables'].items():
                cols = [f"{c['name']} ({c['type']})" for c in table_info.get('columns', [])]
                table_details.append(f"Table '{table_name}': {', '.join(cols)}")
            return "Available tables and their columns:\n" + "\n".join(table_details)

        if 'collections' in schema:
            if not schema['collections']:
                return "The database is connected but no collections were found."
            coll_details = []
            for coll_name, coll_info in schema['collections'].items():
                fields = [f"{f} ({t})" for f, t in coll_info.get('fields', {}).items()]
                coll_details.append(f"Collection '{coll_name}': {', '.join(fields)}")
            return "Available collections and their fields:\n" + "\n".join(coll_details)

        return "The database is connected but no schema information was found."

    return list_database_tables
