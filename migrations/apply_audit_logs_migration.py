"""
Apply audit logs table migration.
"""

import sqlite3
import os


def apply_migration():
    """Apply the audit logs table migration."""
    
    db_path = "tenant_system.db"
    
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} not found")
        return
    
    print(f"Applying audit logs migration to {db_path}...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Read migration SQL
        with open("migrations/003_create_audit_logs_table.sql", "r") as f:
            migration_sql = f.read()
        
        # Execute migration
        cursor.executescript(migration_sql)
        conn.commit()
        
        print("✓ Audit logs table created successfully")
        
        # Verify table creation
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='audit_logs'
        """)
        
        if cursor.fetchone():
            print("✓ Audit logs table verified")
            
            # Check indexes
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND tbl_name='audit_logs'
            """)
            indexes = cursor.fetchall()
            print(f"✓ Created {len(indexes)} indexes")
        else:
            print("✗ Table verification failed")
    
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    apply_migration()
