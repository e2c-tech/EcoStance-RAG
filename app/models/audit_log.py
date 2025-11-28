"""
Audit log model for tracking tenant operations.
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, JSON
from app.db.database import Base


class AuditLog(Base):
    """Model for audit logging of tenant operations."""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    action = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=True, index=True)
    resource_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)  # JSON works with both SQLite and PostgreSQL
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    status = Column(String, nullable=False)  # success, failure, error
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, tenant={self.tenant_id}, action={self.action})>"
