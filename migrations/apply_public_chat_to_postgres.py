"""
Apply public chat tables migration to PostgreSQL
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Get PostgreSQL connection
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env")
    exit(1)

print(f"Connecting to PostgreSQL...")
engine = create_engine(DATABASE_URL)

# Read the PostgreSQL migration
with open('migrations/008_create_public_chat_tables_postgres.sql', 'r') as f:
    sql = f.read()

# Execute the migration
try:
    with engine.connect() as conn:
        # Split by semicolon and execute each statement
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        
        for statement in statements:
            if statement:
                print(f"Executing: {statement[:100]}...")
                conn.execute(text(statement))
                conn.commit()
        
        print("\n✅ Public chat tables created successfully in PostgreSQL!")
        
        # Verify tables exist
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE 'public_chat%'
        """))
        
        tables = [row[0] for row in result]
        print(f"\nCreated tables:")
        for table in tables:
            print(f"  - {table}")
            
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nMake sure your PostgreSQL database is running and accessible.")
