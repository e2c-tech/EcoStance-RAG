"""
TenantQuota model - tracks resource usage and quotas for tenants.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..db.database import Base


class TenantQuota(Base):
    __tablename__ = "tenant_quotas"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Storage usage (in bytes)
    storage_used = Column(BigInteger, default=0)
    storage_limit = Column(BigInteger, default=10737418240)  # 10GB default
    
    # Query counts
    queries_today = Column(Integer, default=0)
    queries_this_month = Column(Integer, default=0)
    queries_limit_daily = Column(Integer, default=1000)
    queries_limit_monthly = Column(Integer, default=30000)
    
    # Document counts
    documents_count = Column(Integer, default=0)
    documents_limit = Column(Integer, default=10000)
    
    # Database connections
    db_connections_count = Column(Integer, default=0)
    db_connections_limit = Column(Integer, default=5)
    
    # API calls
    api_calls_today = Column(Integer, default=0)
    api_calls_this_month = Column(Integer, default=0)
    
    # Reset tracking
    last_daily_reset = Column(DateTime, default=datetime.utcnow)
    last_monthly_reset = Column(DateTime, default=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant")
    
    def __repr__(self):
        return f"<TenantQuota(tenant_id={self.tenant_id}, storage={self.storage_used}/{self.storage_limit})>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "storage": {
                "used": self.storage_used,
                "limit": self.storage_limit,
                "percentage": round((self.storage_used / self.storage_limit * 100), 2) if self.storage_limit > 0 else 0
            },
            "queries": {
                "today": self.queries_today,
                "this_month": self.queries_this_month,
                "daily_limit": self.queries_limit_daily,
                "monthly_limit": self.queries_limit_monthly
            },
            "documents": {
                "count": self.documents_count,
                "limit": self.documents_limit
            },
            "db_connections": {
                "count": self.db_connections_count,
                "limit": self.db_connections_limit
            },
            "api_calls": {
                "today": self.api_calls_today,
                "this_month": self.api_calls_this_month
            },
            "last_daily_reset": self.last_daily_reset.isoformat() if self.last_daily_reset else None,
            "last_monthly_reset": self.last_monthly_reset.isoformat() if self.last_monthly_reset else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_storage_exceeded(self):
        """Check if storage quota is exceeded."""
        return self.storage_used >= self.storage_limit
    
    def is_daily_query_exceeded(self):
        """Check if daily query quota is exceeded."""
        return self.queries_today >= self.queries_limit_daily
    
    def is_monthly_query_exceeded(self):
        """Check if monthly query quota is exceeded."""
        return self.queries_this_month >= self.queries_limit_monthly
