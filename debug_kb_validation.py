"""
Debug script to check KB validation issue.
"""
from app.db.database import SessionLocal
from app.models.tenant_knowledge_base import TenantKnowledgeBase
from sqlalchemy import and_

def main():
    db = SessionLocal()
    
    try:
        tenant_id = "badcd123-6cc6-4011-b01b-d33d1153f10d"
        
        # Get all KBs for this tenant
        kbs = db.query(TenantKnowledgeBase).filter(
            TenantKnowledgeBase.tenant_id == tenant_id
        ).all()
        
        print(f"Found {len(kbs)} KBs for tenant {tenant_id}")
        print("=" * 80)
        
        for kb in kbs:
            print(f"\nKB ID: {kb.id}")
            print(f"  KB Name: {kb.kb_name}")
            print(f"  Collection Name: {kb.collection_name}")
            print(f"  Tenant ID: {kb.tenant_id}")
        
        print("\n" + "=" * 80)
        print("\nTesting validation with collection names:")
        
        # Test collection names from frontend
        test_names = [
            "tenant_badcd123-6cc6-4011-b01b-d33d1153f10d_test-demo-3",
            "tenant_badcd123-6cc6-4011-b01b-d33d1153f10d_test-3",
            "tenant_badcd123-6cc6-4011-b01b-d33d1153f10d_test-4",
            "tenant_badcd123-6cc6-4011-b01b-d33d1153f10d_test-demo2"
        ]
        
        for name in test_names:
            kb_count = db.query(TenantKnowledgeBase).filter(
                and_(
                    TenantKnowledgeBase.tenant_id == tenant_id,
                    TenantKnowledgeBase.collection_name == name
                )
            ).count()
            print(f"  {name}: {'✓ FOUND' if kb_count > 0 else '✗ NOT FOUND'}")
        
        print("\n" + "=" * 80)
        print("\nTesting with .in_() query:")
        kb_count = db.query(TenantKnowledgeBase).filter(
            and_(
                TenantKnowledgeBase.tenant_id == tenant_id,
                TenantKnowledgeBase.collection_name.in_(test_names)
            )
        ).count()
        print(f"Found {kb_count} out of {len(test_names)} KBs")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
