"""
Test script to verify database connection and check tables.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

print(f"DATABASE_URL: {DATABASE_URL}")
print(f"Database type: {'PostgreSQL' if 'postgresql' in DATABASE_URL else 'SQLite'}")

# Create engine
engine = create_engine(DATABASE_URL)

# Test connection
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.fetchone()
        print(f"\n✓ Connected successfully!")
        print(f"Database version: {version[0]}")
        
        # Check for tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\nTables found: {len(tables)}")
        if tables:
            for table in tables:
                print(f"  - {table}")
        else:
            print("  No tables found!")
            
except Exception as e:
    print(f"\n✗ Connection failed: {str(e)}")
