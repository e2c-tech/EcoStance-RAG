"""
TenantDatabase model - represents database connections owned by a tenant.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..db.database import Base


class TenantDatabase(Base):
    __tablename__ = "tenant_databases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Database information
    name = Column(String(255), nullable=False)  # Friendly name
    db_type = Column(String(50), nullable=False)  # sqlite, postgresql, mysql, mongodb
    
    # Encrypted connection string
    db_uri_encrypted = Column(Text, nullable=False)
    
    # Connection metadata
    host = Column(String(255))
    port = Column(String(10))
    database_name = Column(String(255))
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_connected_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="databases")
    
    def __repr__(self):
        return f"<TenantDatabase(id={self.id}, tenant_id={self.tenant_id}, name={self.name}, type={self.db_type})>"
    
    def to_dict(self):
        """Convert to dictionary (excluding encrypted URI)."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "db_type": self.db_type,
            "host": self.host,
            "port": self.port,
            "database_name": self.database_name,
            "is_active": self.is_active,
            "last_connected_at": self.last_connected_at.isoformat() if self.last_connected_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
