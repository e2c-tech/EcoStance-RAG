from sqlalchemy import create_engine, inspect, text
from typing import Dict, List, Any, Optional
import json



# Trigger reload
class DatabaseConnector:
    def __init__(self):
        self.connection = None
        self.engine = None
        self.db_type = None
        self.schema_info = {}
        self.client = None
        self.db = None

    def connect(self, connection_config: Dict[str, Any]) -> bool:
        """Connect to database based on configuration"""
        try:
            self.db_type = connection_config.get('type', '').lower()
            
            if self.db_type == 'sqlite':
                return self._connect_sqlite(connection_config)
            elif self.db_type == 'postgresql':
                return self._connect_postgresql(connection_config)
            elif self.db_type == 'mysql':
                return self._connect_mysql(connection_config)
            elif self.db_type == 'mongodb':
                return self._connect_mongodb(connection_config)
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")
                
        except Exception as e:
            print(f"Database connection error: {str(e)}")
            # Re-raise the exception to be caught by the caller UI
            raise e

    def _connect_sqlite(self, config: Dict[str, Any]) -> bool:
        """Connect to SQLite database"""
        db_path = config.get('database') or config.get('db_path', 'database.db')
        # Strip sqlite:/// prefix if already present to avoid double-prefixing
        if db_path.startswith('sqlite:///'):
            db_path = db_path[len('sqlite:///'):]
        self.engine = create_engine(f'sqlite:///{db_path}')
        self.connection = self.engine.connect()
        return True

    def _connect_postgresql(self, config: Dict[str, Any]) -> bool:
        """Connect to PostgreSQL database"""
        try:
            import psycopg2
        except ImportError:
            raise ImportError("psycopg2-binary is required for PostgreSQL connections. Install with: pip install psycopg2-binary")
        
        connection_string = (
            f"postgresql://{config['username']}:{config['password']}"
            f"@{config['host']}:{config.get('port', 5432)}/{config['database']}"
        )
        self.engine = create_engine(connection_string)
        self.connection = self.engine.connect()
        return True

    def _connect_mysql(self, config: Dict[str, Any]) -> bool:
        """Connect to MySQL database"""
        try:
            import mysql.connector
        except ImportError:
            raise ImportError("mysql-connector-python is required for MySQL connections. Install with: pip install mysql-connector-python")
        
        connection_string = (
            f"mysql+mysqlconnector://{config['username']}:{config['password']}"
            f"@{config['host']}:{config.get('port', 3306)}/{config['database']}"
        )
        if config.get('query'):
            connection_string += f"?{config['query']}"
        self.engine = create_engine(connection_string)
        self.connection = self.engine.connect()
        return True

    def _connect_mongodb(self, config: Dict[str, Any]) -> bool:
        """Connect to MongoDB database"""
        try:
            from pymongo import MongoClient
        except ImportError:
            raise ImportError("pymongo is required for MongoDB connections. Install with: pip install pymongo")
        
        connection_string = f"mongodb://{config['host']}:{config.get('port', 27017)}"
        self.client = MongoClient(connection_string)
        self.db = self.client[config['database']]
        # Test connection
        self.client.admin.command('ping')
        return True

    def get_schema_info(self) -> Dict[str, Any]:
        """Extract database schema information"""
        if self.db_type == 'mongodb':
            return self._get_mongodb_schema()
        else:
            return self._get_sql_schema()

    def _get_sql_schema(self) -> Dict[str, Any]:
        """Get schema for SQL databases"""
        inspector = inspect(self.engine)
        schema_info = {
            'tables': {},
            'relationships': []
        }
        
        table_names = inspector.get_table_names()
        
        for table_name in table_names:
            columns = inspector.get_columns(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            primary_keys = inspector.get_pk_constraint(table_name)
            
            schema_info['tables'][table_name] = {
                'columns': [
                    {
                        'name': col['name'],
                        'type': str(col['type']),
                        'nullable': col['nullable'],
                        'default': col.get('default')
                    }
                    for col in columns
                ],
                'primary_keys': primary_keys['constrained_columns'],
                'foreign_keys': foreign_keys
            }
            
            for fk in foreign_keys:
                schema_info['relationships'].append({
                    'from_table': table_name,
                    'from_columns': fk['constrained_columns'],
                    'to_table': fk['referred_table'],
                    'to_columns': fk['referred_columns']
                })
        
        self.schema_info = schema_info
        return schema_info

    def _get_mongodb_schema(self) -> Dict[str, Any]:
        """Get schema for MongoDB (sample-based)"""
        schema_info = {'collections': {}}
        
        for collection_name in self.db.list_collection_names():
            collection = self.db[collection_name]
            sample_docs = list(collection.find().limit(5))
            
            if sample_docs:
                fields = {}
                for doc in sample_docs:
                    for field, value in doc.items():
                        if field not in fields:
                            fields[field] = type(value).__name__
                
                schema_info['collections'][collection_name] = {
                    'fields': fields,
                    'sample_count': collection.count_documents({})
                }
        
        self.schema_info = schema_info
        return schema_info

    def execute_query(self, query: str) -> Dict[str, Any]:
        """Execute SQL query and return results"""
        try:
            if self.db_type == 'mongodb':
                return {"error": "Direct query execution not supported for MongoDB"}
            
            result = self.connection.execute(text(query))
            
            if result.returns_rows:
                rows = result.fetchall()
                columns = list(result.keys())
                
                return {
                    'success': True,
                    'columns': columns,
                    'rows': [dict(zip(columns, row)) for row in rows],
                    'row_count': len(rows)
                }
            else:
                return {
                    'success': True,
                    'message': f"Query executed successfully. Rows affected: {result.rowcount}",
                    'row_count': result.rowcount
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def test_connection(self) -> bool:
        """Test if database connection is active"""
        try:
            if self.db_type == 'mongodb':
                self.client.admin.command('ping')
                return True
            else:
                self.connection.execute(text("SELECT 1"))
                return True
        except:
            return False

    def is_connected(self) -> bool:
        """Check if database connection is active (alias for test_connection)"""
        return self.test_connection()

    def close_connection(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
        if hasattr(self, 'client') and self.client:
            self.client.close()
        self.connection = None
        self.engine = None
        self.client = None
        self.db = None
