"""
Verify tenant data in PostgreSQL.
"""
from dotenv import load_dotenv
from app.db.database import SessionLocal
from app.models import Tenant, TenantQuota

load_dotenv()

db = SessionLocal()

try:
    # Get all tenants
    tenants = db.query(Tenant).all()
    print(f"Total tenants: {len(tenants)}\n")
    
    for tenant in tenants:
        print(f"Tenant: {tenant.name}")
        print(f"  ID: {tenant.id}")
        print(f"  Slug: {tenant.slug}")
        print(f"  Email: {tenant.email}")
        print(f"  Tier: {tenant.billing_tier}")
        print(f"  Status: {tenant.billing_status}")
        print(f"  Active: {tenant.is_active}")
        
        # Get quota
        quota = db.query(TenantQuota).filter(TenantQuota.tenant_id == tenant.id).first()
        if quota:
            print(f"\n  Quota:")
            print(f"    Storage: {quota.storage_used}/{quota.storage_limit} bytes")
            print(f"    Queries (daily): {quota.queries_today}/{quota.queries_limit_daily}")
            print(f"    Queries (monthly): {quota.queries_this_month}/{quota.queries_limit_monthly}")
            print(f"    Documents: {quota.documents_count}/{quota.documents_limit}")
        print()
        
    print("✓ Data verified successfully in PostgreSQL!")
    
except Exception as e:
    print(f"✗ Error: {str(e)}")
finally:
    db.close()
