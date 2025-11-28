"""
Tenant model - represents a tenant/organization in the system.
"""
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..db.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    
    # Contact information
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(50))
    password_hash = Column(String(255))  # Hashed password for email/password login
    
    # Logo/branding
    logo_url = Column(String(500), nullable=True)
    logo_filename = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    
    # Settings and configuration
    settings = Column(JSON, default=dict)
    # Example settings structure:
    # {
    #     "max_storage_bytes": 10737418240,  # 10GB
    #     "max_queries_per_day": 1000,
    #     "max_queries_per_month": 30000,
    #     "max_documents": 10000,
    #     "max_db_connections": 5,
    #     "features": ["rag", "db_chat", "custom_embeddings"],
    #     "billing_tier": "professional",
    #     "region": "us-east-1"
    # }
    
    # Billing information
    billing_tier = Column(String(50), default="free")  # free, starter, professional, enterprise
    billing_status = Column(String(50), default="active")  # active, suspended, cancelled
    
    # Relationships
    databases = relationship("TenantDatabase", back_populates="tenant", cascade="all, delete-orphan")
    knowledge_bases = relationship("TenantKnowledgeBase", back_populates="tenant", cascade="all, delete-orphan")
    users = relationship("TenantUser", back_populates="tenant", cascade="all, delete-orphan")
    api_keys = relationship("TenantAPIKey", back_populates="tenant", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tenant(id={self.id}, name={self.name}, slug={self.slug})>"
    
    def to_dict(self):
        """Convert tenant to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "email": self.email,
            "phone": self.phone,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "settings": self.settings,
            "billing_tier": self.billing_tier,
            "billing_status": self.billing_status
        }
