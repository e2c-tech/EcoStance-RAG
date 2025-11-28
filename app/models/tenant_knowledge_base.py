"""
TenantKnowledgeBase model - represents knowledge bases (Qdrant collections) owned by a tenant.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..db.database import Base


class TenantKnowledgeBase(Base):
    __tablename__ = "tenant_knowledge_bases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Knowledge base information
    kb_name = Column(String(255), nullable=False)  # User-friendly name
    collection_name = Column(String(255), nullable=False, unique=True, index=True)  # Qdrant collection name
    description = Column(String(500))
    
    # Statistics
    document_count = Column(Integer, default=0)
    vector_count = Column(Integer, default=0)
    storage_bytes = Column(Integer, default=0)
    
    # Configuration
    embedding_model = Column(String(100), default="all-MiniLM-L6-v2")
    chunk_size = Column(Integer, default=512)
    chunk_overlap = Column(Integer, default=50)
    
    # Additional metadata
    extra_metadata = Column(JSON, default=dict)
    # Example: {"source_types": ["pdf", "docx"], "tags": ["product", "support"]}
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_indexed_at = Column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="knowledge_bases")
    
    def __repr__(self):
        return f"<TenantKnowledgeBase(id={self.id}, tenant_id={self.tenant_id}, name={self.kb_name})>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "kb_name": self.kb_name,
            "collection_name": self.collection_name,
            "description": self.description,
            "document_count": self.document_count,
            "vector_count": self.vector_count,
            "storage_bytes": self.storage_bytes,
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "extra_metadata": self.extra_metadata,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_indexed_at": self.last_indexed_at.isoformat() if self.last_indexed_at else None
        }
