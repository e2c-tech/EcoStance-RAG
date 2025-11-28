"""
Add all knowledge bases to public chat configuration for all tenants.
"""
from app.db.database import SessionLocal
from app.models.public_chat import PublicChatConfig
from app.models.tenant_knowledge_base import TenantKnowledgeBase
import json
from datetime import datetime

def main():
    db = SessionLocal()
    
    try:
        print("Adding knowledge bases to public chat...")
        print("=" * 60)
        
        # Get all configs
        configs = db.query(PublicChatConfig).all()
        
        for config in configs:
            # Get all KBs for this tenant
            kbs = db.query(TenantKnowledgeBase).filter(
                TenantKnowledgeBase.tenant_id == config.tenant_id
            ).all()
            
            if kbs:
                kb_names = [kb.collection_name for kb in kbs]
                config.allowed_kbs = json.dumps(kb_names)
                config.updated_at = datetime.utcnow()
                config.updated_by = "admin_script"
                
                print(f"✓ Tenant {config.tenant_id[:8]}...")
                print(f"  Added {len(kb_names)} KB(s): {', '.join(kb_names)}")
            else:
                print(f"  No KBs found for tenant {config.tenant_id[:8]}...")
        
        db.commit()
        
        print("=" * 60)
        print("✓ Knowledge bases added to public chat configs")
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
