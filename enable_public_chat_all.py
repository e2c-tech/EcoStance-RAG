"""
Enable public chat for all tenants.
"""
from app.db.database import SessionLocal
from app.models.public_chat import PublicChatConfig
from app.models.tenant import Tenant
from datetime import datetime

def main():
    db = SessionLocal()
    
    try:
        print("Enabling public chat for all tenants...")
        print("=" * 60)
        
        # Get all configs
        configs = db.query(PublicChatConfig).all()
        
        enabled_count = 0
        for config in configs:
            if not config.enabled:
                config.enabled = True
                config.updated_at = datetime.utcnow()
                config.updated_by = "admin_script"
                enabled_count += 1
                print(f"✓ Enabled for tenant: {config.tenant_id}")
            else:
                print(f"  Already enabled for tenant: {config.tenant_id}")
        
        db.commit()
        
        print("=" * 60)
        print(f"✓ Enabled public chat for {enabled_count} tenant(s)")
        print(f"  Total configs: {len(configs)}")
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
