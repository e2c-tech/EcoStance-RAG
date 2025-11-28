"""
Migration: Add password_hash column to tenants table
"""
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

def run_migration():
    """Add password_hash column to tenants table"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    print("=" * 60)
    print("Migration: Add password_hash to tenants table")
    print("=" * 60)
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='tenants' AND column_name='password_hash'
            """))
            
            if result.fetchone():
                print("✅ Column 'password_hash' already exists")
                return True
            
            # Add password_hash column
            print("\n1. Adding password_hash column...")
            conn.execute(text("""
                ALTER TABLE tenants 
                ADD COLUMN password_hash VARCHAR(255)
            """))
            conn.commit()
            print("✅ Column added successfully")
            
            # Make email unique if not already
            print("\n2. Making email column unique...")
            try:
                conn.execute(text("""
                    ALTER TABLE tenants 
                    ADD CONSTRAINT tenants_email_unique UNIQUE (email)
                """))
                conn.commit()
                print("✅ Email constraint added")
            except Exception as e:
                if "already exists" in str(e):
                    print("✅ Email constraint already exists")
                else:
                    print(f"⚠️ Could not add email constraint: {e}")
            
            print("\n" + "=" * 60)
            print("Migration completed successfully!")
            print("=" * 60)
            return True
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)
