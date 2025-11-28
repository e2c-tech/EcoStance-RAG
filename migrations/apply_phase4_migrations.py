"""
Apply Phase 4 migrations for Resource Management.
"""
import sqlite3
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def apply_migration(db_path: str, migration_file: str):
    """Apply a single migration file."""
    print(f"Applying migration: {migration_file}")
    
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Execute migration
        cursor.executescript(sql)
        conn.commit()
        print(f"✓ Successfully applied {migration_file}")
        return True
    except Exception as e:
        print(f"✗ Error applying {migration_file}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def main():
    """Apply all Phase 4 migrations."""
    # Database path
    db_path = "tenant_system.db"
    
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found")
        return False
    
    # Migration files in order
    migrations = [
        "migrations/005_create_quota_tables.sql",
        "migrations/006_create_metrics_tables.sql",
    ]
    
    print("=" * 60)
    print("Phase 4: Resource Management Migrations")
    print("=" * 60)
    print()
    
    success_count = 0
    for migration in migrations:
        if os.path.exists(migration):
            if apply_migration(db_path, migration):
                success_count += 1
            print()
        else:
            print(f"Warning: Migration file '{migration}' not found")
            print()
    
    print("=" * 60)
    print(f"Migration Summary: {success_count}/{len(migrations)} successful")
    print("=" * 60)
    
    return success_count == len(migrations)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
