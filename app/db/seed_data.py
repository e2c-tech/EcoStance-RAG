"""
Seed script to create initial data including a default tenant.
"""
from sqlalchemy.orm import Session
from .database import SessionLocal
from ..models import Tenant, TenantQuota
import uuid


def create_default_tenant(db: Session):
    """
    Create a default tenant for backward compatibility.
    """
    # Check if default tenant already exists
    default_tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
    
    if default_tenant:
        print("✓ Default tenant already exists")
        return default_tenant
    
    # Create default tenant
    tenant_id = str(uuid.uuid4())
    default_tenant = Tenant(
        id=tenant_id,
        name="Default Organization",
        slug="default",
        email="admin@example.com",
        is_active=True,
        billing_tier="enterprise",
        billing_status="active",
        settings={
            "max_storage_bytes": 107374182400,  # 100GB
            "max_queries_per_day": 10000,
            "max_queries_per_month": 300000,
            "max_documents": 100000,
            "max_db_connections": 20,
            "features": ["rag", "db_chat", "custom_embeddings", "admin"],
            "billing_tier": "enterprise",
            "region": "us-east-1"
        }
    )
    
    db.add(default_tenant)
    db.commit()
    db.refresh(default_tenant)
    
    # Create quota for default tenant
    quota = TenantQuota(
        tenant_id=tenant_id,
        storage_limit=107374182400,  # 100GB
        queries_limit_daily=10000,
        queries_limit_monthly=300000,
        documents_limit=100000,
        db_connections_limit=20
    )
    
    db.add(quota)
    db.commit()
    
    print(f"✓ Created default tenant with ID: {tenant_id}")
    return default_tenant


def seed_database():
    """
    Seed the database with initial data.
    """
    print("Seeding database...")
    
    db = SessionLocal()
    try:
        # Create default tenant
        default_tenant = create_default_tenant(db)
        
        print("\n✓ Database seeded successfully!")
        print(f"\nDefault Tenant Details:")
        print(f"  ID: {default_tenant.id}")
        print(f"  Name: {default_tenant.name}")
        print(f"  Slug: {default_tenant.slug}")
        print(f"  Tier: {default_tenant.billing_tier}")
        
    except Exception as e:
        print(f"✗ Error seeding database: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
