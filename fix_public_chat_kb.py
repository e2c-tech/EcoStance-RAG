"""
Fix public chat configuration to use the correct KB with data.
"""
from app.db.database import SessionLocal
from app.models.public_chat import PublicChatConfig
import json

db = SessionLocal()

try:
    # Get CertifyDigital tenant config
    tenant_id = "badcd123-6cc6-4011-b01b-d33d1153f10d"
    config = db.query(PublicChatConfig).filter(
        PublicChatConfig.tenant_id == tenant_id
    ).first()
    
    if config:
        # Update to use test-demo2 which has the actual data
        config.allowed_kbs = json.dumps(["test-demo2"])
        db.commit()
        print(f"✓ Updated public chat config for CertifyDigital")
        print(f"  Allowed KBs: {config.allowed_kbs}")
    else:
        print("✗ Config not found")
        
finally:
    db.close()
