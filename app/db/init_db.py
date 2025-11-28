"""
Database initialization script.
Run this to create all tables in the database.
"""
from .database import Base, engine, init_db
from ..models import (
    Tenant,
    TenantDatabase,
    TenantKnowledgeBase,
    TenantUser,
    TenantAPIKey
)
from ..models.tenant_quota import TenantQuota
from ..models.audit_log import AuditLog


def create_tables():
    """
    Create all tables in the database.
    """
    print("Creating database tables...")
    
    # Import all models to ensure they're registered with Base
    # This is already done above
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("✓ Database tables created successfully!")
    print("\nCreated tables:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")


def drop_tables():
    """
    Drop all tables from the database.
    WARNING: This will delete all data!
    """
    print("WARNING: This will delete all data!")
    confirm = input("Type 'yes' to confirm: ")
    
    if confirm.lower() == 'yes':
        print("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        print("✓ All tables dropped!")
    else:
        print("Operation cancelled.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--drop":
        drop_tables()
    else:
        create_tables()
