from sqlalchemy import Column, String, DateTime, Text
from datetime import datetime
import uuid
from ..db.database import Base

class CustomCRMEmail(Base):
    """
    Tracks emails ingested from the Custom CRM to prevent invalid duplicates.
    This table maps the CRM's email ID to the Tenant's workspace.
    """
    __tablename__ = "custom_crm_emails"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    
    # The ID from the Custom CRM (Gmail Message ID or internal UUID)
    crm_email_id = Column(String(255), index=True, nullable=False)
    
    # Metadata for display/history
    subject = Column(String(500), nullable=True)
    sender = Column(String(255), nullable=True)
    received_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
