"""
Script to check and fix public chat configuration in the database.
"""
import sys
from app.db.database import SessionLocal
from app.models.public_chat import PublicChatConfig
from app.models.tenant import Tenant
import json

def main():
    # Create database connection
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("PUBLIC CHAT CONFIGURATION CHECK")
        print("=" * 60)
        
        # Get all tenants
        tenants = db.query(Tenant).all()
        print(f"\nFound {len(tenants)} tenant(s)")
        
        for tenant in tenants:
            print(f"\n--- Tenant: {tenant.name} (ID: {tenant.id}) ---")
            
            # Check if config exists
            config = db.query(PublicChatConfig).filter(
                PublicChatConfig.tenant_id == tenant.id
            ).first()
            
            if config:
                print(f"✓ Config exists")
                print(f"  - Enabled: {config.enabled}")
                print(f"  - Allowed KBs: {config.allowed_kbs}")
                print(f"  - Welcome Message: {config.welcome_message[:50]}...")
                print(f"  - Updated At: {config.updated_at}")
                print(f"  - Updated By: {config.updated_by}")
            else:
                print(f"✗ No config found - creating default config...")
                
                # Create default config
                config = PublicChatConfig(
                    tenant_id=tenant.id,
                    enabled=False,
                    allowed_kbs="[]",
                    welcome_message="Hi! How can I help you today?",
                    suggested_questions="[]",
                    branding=json.dumps({
                        "primary_color": "#0066CC",
                        "company_name": tenant.name
                    }),
                    rate_limit=json.dumps({
                        "queries_per_minute": 10,
                        "max_messages_per_session": 50
                    }),
                    features=json.dumps({
                        "show_sources": True,
                        "allow_feedback": True,
                        "show_suggested_questions": True
                    })
                )
                db.add(config)
                db.commit()
                print(f"✓ Created default config")
        
        print("\n" + "=" * 60)
        print("CONFIGURATION CHECK COMPLETE")
        print("=" * 60)
        
        # Ask if user wants to enable public chat
        print("\nWould you like to enable public chat for a tenant? (y/n): ", end="")
        response = input().strip().lower()
        
        if response == 'y':
            if len(tenants) == 1:
                selected_tenant = tenants[0]
            else:
                print("\nSelect tenant:")
                for i, tenant in enumerate(tenants):
                    print(f"{i + 1}. {tenant.name} ({tenant.id})")
                print("Enter number: ", end="")
                idx = int(input().strip()) - 1
                selected_tenant = tenants[idx]
            
            config = db.query(PublicChatConfig).filter(
                PublicChatConfig.tenant_id == selected_tenant.id
            ).first()
            
            if config:
                config.enabled = True
                db.commit()
                print(f"\n✓ Public chat ENABLED for {selected_tenant.name}")
                print(f"  Config ID: {config.id}")
                print(f"  Tenant ID: {config.tenant_id}")
                print(f"  Enabled: {config.enabled}")
            else:
                print(f"\n✗ Config not found for tenant {selected_tenant.id}")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
