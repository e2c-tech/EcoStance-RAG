"""
Database Migration Runner for PostgreSQL
Runs SQL migration scripts in order.
"""
import os
import sys
from pathlib import Path
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)


def parse_postgres_url(url: str) -> dict:
    """Parse PostgreSQL connection URL."""
    # Format: postgresql://user:password@host:port/database
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path[1:],  # Remove leading /
        "user": parsed.username,
        "password": parsed.password
    }


def get_connection():
    """Get database connection."""
    try:
        conn_params = parse_postgres_url(DATABASE_URL)
        conn = psycopg2.connect(**conn_params)
        return conn
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        sys.exit(1)


def create_migrations_table(conn):
    """Create migrations tracking table if it doesn't exist."""
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN NOT NULL DEFAULT TRUE
            )
        """)
        conn.commit()
        print("✓ Migrations tracking table ready")


def is_migration_applied(conn, migration_name: str) -> bool:
    """Check if migration has already been applied."""
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM schema_migrations WHERE migration_name = %s AND success = TRUE",
            (migration_name,)
        )
        count = cursor.fetchone()[0]
        return count > 0


def record_migration(conn, migration_name: str, success: bool = True):
    """Record migration in tracking table."""
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO schema_migrations (migration_name, success) VALUES (%s, %s)",
            (migration_name, success)
        )
        conn.commit()


def run_migration_file(conn, filepath: Path):
    """Run a single migration SQL file."""
    migration_name = filepath.name
    
    # Check if already applied
    if is_migration_applied(conn, migration_name):
        print(f"⊘ Skipping {migration_name} (already applied)")
        return True
    
    print(f"→ Running {migration_name}...")
    
    try:
        # Read SQL file
        with open(filepath, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Execute SQL
        with conn.cursor() as cursor:
            cursor.execute(sql_content)
        
        conn.commit()
        
        # Record success
        record_migration(conn, migration_name, success=True)
        print(f"✓ {migration_name} completed successfully")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"✗ {migration_name} failed: {e}")
        record_migration(conn, migration_name, success=False)
        return False


def run_all_migrations():
    """Run all migration files in order."""
    migrations_dir = Path(__file__).parent
    
    # Get all SQL files (excluding rollback)
    migration_files = sorted([
        f for f in migrations_dir.glob("*.sql")
        if not f.name.startswith("003_rollback")
    ])
    
    if not migration_files:
        print("No migration files found")
        return
    
    print(f"\nFound {len(migration_files)} migration(s) to run")
    print("=" * 60)
    
    # Connect to database
    conn = get_connection()
    
    try:
        # Create migrations tracking table
        create_migrations_table(conn)
        
        # Run each migration
        success_count = 0
        for migration_file in migration_files:
            if run_migration_file(conn, migration_file):
                success_count += 1
            else:
                print("\n⚠ Migration failed. Stopping execution.")
                break
        
        print("=" * 60)
        print(f"\nCompleted: {success_count}/{len(migration_files)} migrations")
        
        if success_count == len(migration_files):
            print("✓ All migrations completed successfully!")
        else:
            print("⚠ Some migrations failed. Check errors above.")
            
    finally:
        conn.close()


def show_migration_status():
    """Show status of all migrations."""
    conn = get_connection()
    
    try:
        create_migrations_table(conn)
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT migration_name, applied_at, success 
                FROM schema_migrations 
                ORDER BY applied_at
            """)
            
            results = cursor.fetchall()
            
            if not results:
                print("No migrations have been applied yet")
                return
            
            print("\nMigration Status:")
            print("=" * 80)
            print(f"{'Migration':<40} {'Applied At':<25} {'Status':<10}")
            print("-" * 80)
            
            for name, applied_at, success in results:
                status = "✓ Success" if success else "✗ Failed"
                print(f"{name:<40} {str(applied_at):<25} {status:<10}")
            
            print("=" * 80)
            
    finally:
        conn.close()


def rollback_migrations():
    """Run rollback script (emergency use only)."""
    print("\n⚠ WARNING: This will remove ALL tenant data!")
    print("Make sure you have a backup before proceeding.")
    
    response = input("\nType 'ROLLBACK' to confirm: ")
    
    if response != "ROLLBACK":
        print("Rollback cancelled")
        return
    
    migrations_dir = Path(__file__).parent
    rollback_file = migrations_dir / "003_rollback_tenant_migration.sql"
    
    if not rollback_file.exists():
        print("ERROR: Rollback file not found")
        return
    
    conn = get_connection()
    
    try:
        print("\n→ Running rollback...")
        
        with open(rollback_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        with conn.cursor() as cursor:
            cursor.execute(sql_content)
        
        conn.commit()
        
        # Clear migration history
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS schema_migrations")
        
        conn.commit()
        
        print("✓ Rollback completed successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Rollback failed: {e}")
        
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Migration Runner")
    parser.add_argument(
        "command",
        choices=["migrate", "status", "rollback"],
        help="Command to run"
    )
    
    args = parser.parse_args()
    
    if args.command == "migrate":
        run_all_migrations()
    elif args.command == "status":
        show_migration_status()
    elif args.command == "rollback":
        rollback_migrations()
