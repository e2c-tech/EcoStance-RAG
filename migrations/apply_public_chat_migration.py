"""
Apply Public Chat Migration
Creates tables for public chat configuration, sessions, messages, and feedback.
"""
import sqlite3
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def apply_migration(db_path: str = "tenant_system.db"):
    """Apply the public chat migration."""
    print(f"Applying public chat migration to {db_path}...")
    
    # Read SQL file
    sql_file = os.path.join(os.path.dirname(__file__), "008_create_public_chat_tables.sql")
    with open(sql_file, 'r') as f:
        sql_script = f.read()
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Execute migration
        cursor.executescript(sql_script)
        conn.commit()
        print("✓ Public chat tables created successfully")
        
        # Verify tables were created
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'public_chat%'
            ORDER BY name
        """)
        tables = cursor.fetchall()
        
        print("\nCreated tables:")
        for table in tables:
            print(f"  - {table[0]}")
            
            # Count rows
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"    Rows: {count}")
        
        print("\n✓ Migration completed successfully!")
        
    except Exception as e:
        print(f"✗ Error applying migration: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    # Check if custom database path is provided
    db_path = sys.argv[1] if len(sys.argv) > 1 else "tenant_system.db"
    
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found")
        sys.exit(1)
    
    apply_migration(db_path)
