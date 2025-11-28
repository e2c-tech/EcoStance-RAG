"""
Tests for Quota Service.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.quota_service import QuotaService, QuotaExceededException
from app.models.tenant import Tenant
from app.db.database import Base


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    # Create quota tables
    with engine.connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tenant_quotas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                max_queries_per_day INTEGER DEFAULT 1000,
                max_queries_per_month INTEGER DEFAULT 30000,
                max_documents INTEGER DEFAULT 10000,
                max_storage_bytes INTEGER DEFAULT 10737418240,
                max_db_connections INTEGER DEFAULT 5,
                max_concurrent_queries INTEGER DEFAULT 10,
                max_api_calls_per_minute INTEGER DEFAULT 60,
                max_api_calls_per_hour INTEGER DEFAULT 3600,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tenant_id)
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tenant_quota_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                period_type TEXT NOT NULL,
                period_start TIMESTAMP NOT NULL,
                period_end TIMESTAMP NOT NULL,
                query_count INTEGER DEFAULT 0,
                document_count INTEGER DEFAULT 0,
                storage_bytes INTEGER DEFAULT 0,
                active_db_connections INTEGER DEFAULT 0,
                concurrent_queries INTEGER DEFAULT 0,
                api_calls_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tenant_id, period_type, period_start)
            )
        """)
        conn.commit()
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create test tenant
    tenant = Tenant(
        id="test-tenant-1",
        name="Test Tenant",
        slug="test-tenant",
        email="test@example.com",
        billing_tier="starter"
    )
    session.add(tenant)
    session.commit()
    
    yield session
    
    session.close()


def test_get_tenant_quotas_default(db_session):
    """Test getting default quotas based on tier."""
    service = QuotaService(db_session)
    quotas = service.get_tenant_quotas("test-tenant-1")
    
    # Should return starter tier quotas
    assert quotas["max_queries_per_day"] == 1000
    assert quotas["max_queries_per_month"] == 30000
    assert quotas["max_documents"] == 10000
    assert quotas["max_storage_bytes"] == 10737418240  # 10GB


def test_check_query_quota_allowed(db_session):
    """Test query quota check when within limits."""
    service = QuotaService(db_session)
    allowed, error = service.check_query_quota("test-tenant-1")
    
    assert allowed is True
    assert error is None


def test_check_query_quota_exceeded(db_session):
    """Test query quota check when limit exceeded."""
    service = QuotaService(db_session)
    
    # Set usage to exceed daily limit
    now = datetime.utcnow()
    period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    period_end = period_start + timedelta(days=1)
    
    db_session.execute(
        """
        INSERT INTO tenant_quota_usage 
            (tenant_id, period_type, period_start, period_end, query_count)
        VALUES (?, 'daily', ?, ?, 1001)
        """,
        ("test-tenant-1", period_start, period_end)
    )
    db_session.commit()
    
    allowed, error = service.check_query_quota("test-tenant-1")
    
    assert allowed is False
    assert "quota exceeded" in error.lower()


def test_check_document_quota(db_session):
    """Test document quota check."""
    service = QuotaService(db_session)
    
    # Should allow adding documents
    allowed, error = service.check_document_quota("test-tenant-1", additional_docs=100)
    assert allowed is True
    assert error is None


def test_check_storage_quota(db_session):
    """Test storage quota check."""
    service = QuotaService(db_session)
    
    # Should allow adding storage
    allowed, error = service.check_storage_quota("test-tenant-1", additional_bytes=1024*1024*100)  # 100MB
    assert allowed is True
    assert error is None


def test_increment_usage(db_session):
    """Test incrementing usage counters."""
    service = QuotaService(db_session)
    
    # Increment query count
    service.increment_usage("test-tenant-1", "query", amount=5, period_type="daily")
    
    # Check usage
    usage = service.get_current_usage("test-tenant-1", "daily")
    assert usage["query_count"] == 5


def test_get_quota_status(db_session):
    """Test getting comprehensive quota status."""
    service = QuotaService(db_session)
    
    # Add some usage
    service.increment_usage("test-tenant-1", "query", amount=100, period_type="daily")
    service.increment_usage("test-tenant-1", "storage", amount=1024*1024*1024, period_type="daily")  # 1GB
    
    status = service.get_quota_status("test-tenant-1")
    
    assert status["tenant_id"] == "test-tenant-1"
    assert "quotas" in status
    assert "daily_usage" in status
    assert "monthly_usage" in status
    assert "storage" in status
    
    # Check percentages
    assert status["daily_usage"]["queries"]["percentage"] == 10.0  # 100/1000 = 10%
    assert status["storage"]["percentage"] > 0


def test_update_tenant_quotas(db_session):
    """Test updating tenant quotas."""
    service = QuotaService(db_session)
    
    # Update quotas
    new_quotas = {
        "max_queries_per_day": 5000,
        "max_storage_bytes": 53687091200  # 50GB
    }
    service.update_tenant_quotas("test-tenant-1", new_quotas)
    
    # Verify update
    quotas = service.get_tenant_quotas("test-tenant-1")
    assert quotas["max_queries_per_day"] == 5000
    assert quotas["max_storage_bytes"] == 53687091200


def test_unlimited_quota(db_session):
    """Test unlimited quota (-1 value)."""
    # Update tenant to enterprise tier
    tenant = db_session.query(Tenant).filter(Tenant.id == "test-tenant-1").first()
    tenant.billing_tier = "enterprise"
    db_session.commit()
    
    service = QuotaService(db_session)
    quotas = service.get_tenant_quotas("test-tenant-1")
    
    # Enterprise tier has unlimited queries
    assert quotas["max_queries_per_day"] == -1
    assert quotas["max_queries_per_month"] == -1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
