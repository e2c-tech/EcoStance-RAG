"""
TenantAPIKey model - represents API keys for tenant authentication.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, JSON, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..db.database import Base


class TenantAPIKey(Base):
    __tablename__ = "tenant_api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # API Key information
    name = Column(String(255), nullable=False)  # Friendly name for the key
    key_hash = Column(String(255), nullable=False, unique=True, index=True)  # Hashed API key
    key_prefix = Column(String(20), nullable=False)  # First few chars for identification (e.g., "sk_live_abc...")
    
    # Permissions
    permissions = Column(JSON, default=list)
    # Example: ["upload:files", "query:kb", "manage:db", "admin:*"]
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys")
    
    def __repr__(self):
        return f"<TenantAPIKey(id={self.id}, tenant_id={self.tenant_id}, name={self.name}, prefix={self.key_prefix})>"
    
    def to_dict(self):
        """Convert to dictionary (excluding key_hash)."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "key_prefix": self.key_prefix,
            "permissions": self.permissions,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "usage_count": self.usage_count,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_expired(self):
        """Check if the API key has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
