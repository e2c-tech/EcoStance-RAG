"""
Apply Phase 5 migrations - Add tenant logo fields.
"""
import sqlite3
import os
from datetime import datetime


def apply_phase5_migrations(db_path: str = "tenant_system.db"):
    """Apply Phase 5 database migrations."""
    
    print(f"Applying Phase 5 migrations to {db_path}...")
    
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} not found")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if migrations already applied
        cursor.execute("PRAGMA table_info(tenants)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "logo_url" in columns:
            print("✓ Phase 5 migrations already applied")
            return True
        
        print("\n1. Adding logo fields to tenants table...")
        
        # Add logo fields
        cursor.execute("ALTER TABLE tenants ADD COLUMN logo_url VARCHAR(500)")
        cursor.execute("ALTER TABLE tenants ADD COLUMN logo_filename VARCHAR(255)")
        
        # Create index
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenants_logo_filename ON tenants(logo_filename)")
        
        conn.commit()
        print("✓ Logo fields added successfully")
        
        # Verify changes
        cursor.execute("PRAGMA table_info(tenants)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "logo_url" in columns and "logo_filename" in columns:
            print("\n✓ Phase 5 migrations completed successfully!")
            print(f"  - Added logo_url column")
            print(f"  - Added logo_filename column")
            print(f"  - Created index on logo_filename")
            return True
        else:
            print("\n✗ Migration verification failed")
            return False
            
    except Exception as e:
        print(f"\n✗ Error applying migrations: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = apply_phase5_migrations()
    exit(0 if success else 1)
