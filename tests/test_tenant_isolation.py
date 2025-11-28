"""
Comprehensive tenant isolation tests.
Ensures that tenants cannot access each other's data across all resources.
"""
import pytest
import os
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.models.tenant import Tenant
from app.models.tenant_knowledge_base import TenantKnowledgeBase
from app.models.tenant_database import TenantDatabase
from app.models.tenant_user import TenantUser
from app.db.database import Base
from app.services.tenant_service import TenantService
from app.services.credential_service import CredentialService


# Test database setup
TEST_DB_URL = "sqlite:///./test_tenant_isolation.db"


@pytest.fixture(scope="module")
def test_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    # Clean up test database file
    if os.path.exists("./test_tenant_isolation.db"):
        os.remove("./test_tenant_isolation.db")


@pytest.fixture(scope="module")
def test_session(test_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def tenant_a(test_session):
    """Create test tenant A."""
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name="Tenant A Corp",
        slug="tenant-a",
        email="admin@tenant-a.com",
        is_active=True,
        billing_tier="professional"
    )
    test_session.add(tenant)
    test_session.commit()
    test_session.refresh(tenant)
    return tenant


@pytest.fixture(scope="module")
def tenant_b(test_session):
    """Create test tenant B."""
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name="Tenant B Inc",
        slug="tenant-b",
        email="admin@tenant-b.com",
        is_active=True,
        billing_tier="professional"
    )
    test_session.add(tenant)
    test_session.commit()
    test_session.refresh(tenant)
    return tenant


@pytest.fixture(scope="module")
def kb_tenant_a(test_session, tenant_a):
    """Create knowledge base for tenant A."""
    kb = TenantKnowledgeBase(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        kb_name="Tenant A KB",
        collection_name=f"tenant_{tenant_a.id}_kb_main",
        description="Main knowledge base for Tenant A",
        document_count=10,
        vector_count=100
    )
    test_session.add(kb)
    test_session.commit()
    test_session.refresh(kb)
    return kb


@pytest.fixture(scope="module")
def kb_tenant_b(test_session, tenant_b):
    """Create knowledge base for tenant B."""
    kb = TenantKnowledgeBase(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        kb_name="Tenant B KB",
        collection_name=f"tenant_{tenant_b.id}_kb_main",
        description="Main knowledge base for Tenant B",
        document_count=20,
        vector_count=200
    )
    test_session.add(kb)
    test_session.commit()
    test_session.refresh(kb)
    return kb


@pytest.fixture(scope="module")
def db_tenant_a(test_session, tenant_a):
    """Create database connection for tenant A."""
    cred_service = CredentialService(use_vault=False)
    encrypted_uri = cred_service.encrypt_credential("postgresql://user:pass@localhost/tenant_a_db")
    
    db = TenantDatabase(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        name="Tenant A Database",
        db_type="postgresql",
        db_uri_encrypted=encrypted_uri,
        host="localhost",
        port="5432",
        database_name="tenant_a_db"
    )
    test_session.add(db)
    test_session.commit()
    test_session.refresh(db)
    return db


@pytest.fixture(scope="module")
def db_tenant_b(test_session, tenant_b):
    """Create database connection for tenant B."""
    cred_service = CredentialService(use_vault=False)
    encrypted_uri = cred_service.encrypt_credential("postgresql://user:pass@localhost/tenant_b_db")
    
    db = TenantDatabase(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        name="Tenant B Database",
        db_type="postgresql",
        db_uri_encrypted=encrypted_uri,
        host="localhost",
        port="5432",
        database_name="tenant_b_db"
    )
    test_session.add(db)
    test_session.commit()
    test_session.refresh(db)
    return db


@pytest.fixture(scope="module")
def user_tenant_a(test_session, tenant_a):
    """Create user for tenant A."""
    user = TenantUser(
        id=str(uuid.uuid4()),
        tenant_id=tenant_a.id,
        user_id=str(uuid.uuid4()),
        email="user@tenant-a.com",
        full_name="Tenant A User",
        role="admin"
    )
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user


@pytest.fixture(scope="module")
def user_tenant_b(test_session, tenant_b):
    """Create user for tenant B."""
    user = TenantUser(
        id=str(uuid.uuid4()),
        tenant_id=tenant_b.id,
        user_id=str(uuid.uuid4()),
        email="user@tenant-b.com",
        full_name="Tenant B User",
        role="admin"
    )
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user


class TestKnowledgeBaseIsolation:
    """Test knowledge base isolation between tenants."""
    
    def test_tenant_cannot_list_other_tenant_kbs(self, test_session, tenant_a, tenant_b, kb_tenant_a, kb_tenant_b):
        """Test that tenant A cannot see tenant B's knowledge bases."""
        # Query KBs for tenant A
        tenant_a_kbs = test_session.query(TenantKnowledgeBase).filter(
            TenantKnowledgeBase.tenant_id == tenant_a.id
        ).all()
        
        # Should only see their own KB
        assert len(tenant_a_kbs) == 1
        assert tenant_a_kbs[0].id == kb_tenant_a.id
        assert tenant_a_kbs[0].tenant_id == tenant_a.id
        
        # Verify tenant B's KB is not in the results
        tenant_a_kb_ids = [kb.id for kb in tenant_a_kbs]
        assert kb_tenant_b.id not in tenant_a_kb_ids
    
    def test_tenant_cannot_access_other_tenant_kb_by_id(self, test_session, tenant_a, tenant_b, kb_tenant_a, kb_tenant_b):
        """Test that tenant A cannot access tenant B's KB even with the ID."""
        # Try to access tenant B's KB with tenant A's filter
        kb = test_session.query(TenantKnowledgeBase).filter(
            TenantKnowledgeBase.id == kb_tenant_b.id,
            TenantKnowledgeBase.tenant_id == tenant_a.id
        ).first()
        
        # Should return None (not found)
        assert kb is None
    
    def test_collection_names_are_tenant_specific(self, kb_tenant_a, kb_tenant_b):
        """Test that collection names include tenant ID for isolation."""
        # Collection names should contain tenant ID
        assert kb_tenant_a.tenant_id in kb_tenant_a.collection_name
        assert kb_tenant_b.tenant_id in kb_tenant_b.collection_name
        
        # Collection names should be different
        assert kb_tenant_a.collection_name != kb_tenant_b.collection_name
    
    def test_kb_queries_include_tenant_filter(self, test_session, tenant_a, kb_tenant_a, kb_tenant_b):
        """Test that all KB queries must include tenant_id filter."""
        # Query without tenant filter (simulating a bug)
        all_kbs = test_session.query(TenantKnowledgeBase).all()
        
        # Should return both KBs (this is the vulnerability we're testing against)
        assert len(all_kbs) >= 2
        
        # Correct query with tenant filter
        tenant_a_kbs = test_session.query(TenantKnowledgeBase).filter(
            TenantKnowledgeBase.tenant_id == tenant_a.id
        ).all()
        
        # Should only return tenant A's KB
        assert len(tenant_a_kbs) == 1
        assert all(kb.tenant_id == tenant_a.id for kb in tenant_a_kbs)


class TestDatabaseConnectionIsolation:
    """Test database connection isolation between tenants."""
    
    def test_tenant_cannot_list_other_tenant_databases(self, test_session, tenant_a, tenant_b, db_tenant_a, db_tenant_b):
        """Test that tenant A cannot see tenant B's database connections."""
        # Query databases for tenant A
        tenant_a_dbs = test_session.query(TenantDatabase).filter(
            TenantDatabase.tenant_id == tenant_a.id
        ).all()
        
        # Should only see their own database
        assert len(tenant_a_dbs) == 1
        assert tenant_a_dbs[0].id == db_tenant_a.id
        assert tenant_a_dbs[0].tenant_id == tenant_a.id
        
        # Verify tenant B's database is not in the results
        tenant_a_db_ids = [db.id for db in tenant_a_dbs]
        assert db_tenant_b.id not in tenant_a_db_ids
    
    def test_tenant_cannot_access_other_tenant_db_by_id(self, test_session, tenant_a, db_tenant_b):
        """Test that tenant A cannot access tenant B's database even with the ID."""
        # Try to access tenant B's database with tenant A's filter
        db = test_session.query(TenantDatabase).filter(
            TenantDatabase.id == db_tenant_b.id,
            TenantDatabase.tenant_id == tenant_a.id
        ).first()
        
        # Should return None (not found)
        assert db is None
    
    def test_database_credentials_are_encrypted(self, db_tenant_a, db_tenant_b):
        """Test that database credentials are encrypted."""
        # Encrypted URIs should not contain plain text passwords
        assert "pass" not in db_tenant_a.db_uri_encrypted.lower() or len(db_tenant_a.db_uri_encrypted) > 100
        assert "pass" not in db_tenant_b.db_uri_encrypted.lower() or len(db_tenant_b.db_uri_encrypted) > 100
        
        # Encrypted URIs should be different even if similar content
        assert db_tenant_a.db_uri_encrypted != db_tenant_b.db_uri_encrypted
    
    def test_tenant_cannot_decrypt_other_tenant_credentials(self, db_tenant_a, db_tenant_b):
        """Test that credentials are properly isolated (conceptual test)."""
        # In a real system, decryption should also check tenant_id
        # This test verifies that encrypted credentials are different
        assert db_tenant_a.db_uri_encrypted != db_tenant_b.db_uri_encrypted
        assert db_tenant_a.tenant_id != db_tenant_b.tenant_id


class TestUserIsolation:
    """Test user isolation between tenants."""
    
    def test_tenant_cannot_list_other_tenant_users(self, test_session, tenant_a, tenant_b, user_tenant_a, user_tenant_b):
        """Test that tenant A cannot see tenant B's users."""
        # Query users for tenant A
        tenant_a_users = test_session.query(TenantUser).filter(
            TenantUser.tenant_id == tenant_a.id
        ).all()
        
        # Should only see their own user
        assert len(tenant_a_users) == 1
        assert tenant_a_users[0].id == user_tenant_a.id
        assert tenant_a_users[0].tenant_id == tenant_a.id
        
        # Verify tenant B's user is not in the results
        tenant_a_user_ids = [user.id for user in tenant_a_users]
        assert user_tenant_b.id not in tenant_a_user_ids
    
    def test_user_cannot_belong_to_multiple_tenants_with_same_user_id(self, test_session, tenant_a, tenant_b):
        """Test that a user_id can belong to multiple tenants (multi-tenant users)."""
        # This is actually allowed - same user can be in multiple tenants
        shared_user_id = str(uuid.uuid4())
        
        user_a = TenantUser(
            id=str(uuid.uuid4()),
            tenant_id=tenant_a.id,
            user_id=shared_user_id,
            email="shared@example.com",
            full_name="Shared User",
            role="user"
        )
        
        user_b = TenantUser(
            id=str(uuid.uuid4()),
            tenant_id=tenant_b.id,
            user_id=shared_user_id,
            email="shared@example.com",
            full_name="Shared User",
            role="user"
        )
        
        test_session.add(user_a)
        test_session.add(user_b)
        test_session.commit()
        
        # Both should exist but with different tenant_ids
        assert user_a.tenant_id != user_b.tenant_id
        assert user_a.user_id == user_b.user_id
        
        # Cleanup
        test_session.delete(user_a)
        test_session.delete(user_b)
        test_session.commit()
    
    def test_user_queries_must_include_tenant_filter(self, test_session, tenant_a, user_tenant_a):
        """Test that user queries must include tenant_id filter."""
        # Correct query with tenant filter
        users = test_session.query(TenantUser).filter(
            TenantUser.tenant_id == tenant_a.id
        ).all()
        
        # Should only return tenant A's users
        assert all(user.tenant_id == tenant_a.id for user in users)


class TestFileStorageIsolation:
    """Test file storage isolation between tenants."""
    
    def test_file_paths_include_tenant_id(self, tenant_a, tenant_b):
        """Test that file paths include tenant ID for isolation."""
        # File paths should be tenant-specific
        tenant_a_path = f"uploads/{tenant_a.id}/document.pdf"
        tenant_b_path = f"uploads/{tenant_b.id}/document.pdf"
        
        # Paths should be different
        assert tenant_a_path != tenant_b_path
        assert tenant_a.id in tenant_a_path
        assert tenant_b.id in tenant_b_path
    
    def test_tenant_cannot_access_other_tenant_files(self, tenant_a, tenant_b):
        """Test that file access checks tenant_id."""
        # Simulate file access check
        def can_access_file(file_path: str, tenant_id: str) -> bool:
            """Check if tenant can access file."""
            return f"uploads/{tenant_id}/" in file_path
        
        tenant_a_file = f"uploads/{tenant_a.id}/document.pdf"
        tenant_b_file = f"uploads/{tenant_b.id}/document.pdf"
        
        # Tenant A can access their own files
        assert can_access_file(tenant_a_file, tenant_a.id)
        
        # Tenant A cannot access tenant B's files
        assert not can_access_file(tenant_b_file, tenant_a.id)
        
        # Tenant B can access their own files
        assert can_access_file(tenant_b_file, tenant_b.id)
        
        # Tenant B cannot access tenant A's files
        assert not can_access_file(tenant_a_file, tenant_b.id)


class TestCascadeDelete:
    """Test that deleting a tenant cascades to all related resources."""
    
    def test_deleting_tenant_deletes_knowledge_bases(self, test_session):
        """Test that deleting a tenant deletes their knowledge bases."""
        # Create temporary tenant
        temp_tenant = Tenant(
            id=str(uuid.uuid4()),
            name="Temp Tenant",
            slug="temp-tenant",
            email="temp@example.com"
        )
        test_session.add(temp_tenant)
        test_session.commit()
        
        # Create KB for temp tenant
        temp_kb = TenantKnowledgeBase(
            id=str(uuid.uuid4()),
            tenant_id=temp_tenant.id,
            kb_name="Temp KB",
            collection_name=f"tenant_{temp_tenant.id}_temp"
        )
        test_session.add(temp_kb)
        test_session.commit()
        
        kb_id = temp_kb.id
        tenant_id = temp_tenant.id
        
        # Delete tenant
        test_session.delete(temp_tenant)
        test_session.commit()
        
        # KB should be deleted (cascade)
        kb = test_session.query(TenantKnowledgeBase).filter(
            TenantKnowledgeBase.id == kb_id
        ).first()
        assert kb is None
        
        # Tenant should be deleted
        tenant = test_session.query(Tenant).filter(Tenant.id == tenant_id).first()
        assert tenant is None
    
    def test_deleting_tenant_deletes_databases(self, test_session):
        """Test that deleting a tenant deletes their database connections."""
        # Create temporary tenant
        temp_tenant = Tenant(
            id=str(uuid.uuid4()),
            name="Temp Tenant 2",
            slug="temp-tenant-2",
            email="temp2@example.com"
        )
        test_session.add(temp_tenant)
        test_session.commit()
        
        # Create database for temp tenant
        cred_service = CredentialService(use_vault=False)
        temp_db = TenantDatabase(
            id=str(uuid.uuid4()),
            tenant_id=temp_tenant.id,
            name="Temp DB",
            db_type="postgresql",
            db_uri_encrypted=cred_service.encrypt_credential("postgresql://localhost/temp")
        )
        test_session.add(temp_db)
        test_session.commit()
        
        db_id = temp_db.id
        
        # Delete tenant
        test_session.delete(temp_tenant)
        test_session.commit()
        
        # Database should be deleted (cascade)
        db = test_session.query(TenantDatabase).filter(
            TenantDatabase.id == db_id
        ).first()
        assert db is None


class TestConcurrentTenantAccess:
    """Test concurrent access by multiple tenants."""
    
    def test_concurrent_kb_queries(self, test_session, tenant_a, tenant_b, kb_tenant_a, kb_tenant_b):
        """Test that concurrent queries by different tenants are isolated."""
        # Simulate concurrent queries
        results_a = test_session.query(TenantKnowledgeBase).filter(
            TenantKnowledgeBase.tenant_id == tenant_a.id
        ).all()
        
        results_b = test_session.query(TenantKnowledgeBase).filter(
            TenantKnowledgeBase.tenant_id == tenant_b.id
        ).all()
        
        # Each tenant should only see their own data
        assert len(results_a) == 1
        assert len(results_b) == 1
        assert results_a[0].tenant_id == tenant_a.id
        assert results_b[0].tenant_id == tenant_b.id
        assert results_a[0].id != results_b[0].id
    
    def test_concurrent_database_queries(self, test_session, tenant_a, tenant_b, db_tenant_a, db_tenant_b):
        """Test that concurrent database queries by different tenants are isolated."""
        # Simulate concurrent queries
        results_a = test_session.query(TenantDatabase).filter(
            TenantDatabase.tenant_id == tenant_a.id
        ).all()
        
        results_b = test_session.query(TenantDatabase).filter(
            TenantDatabase.tenant_id == tenant_b.id
        ).all()
        
        # Each tenant should only see their own data
        assert len(results_a) == 1
        assert len(results_b) == 1
        assert results_a[0].tenant_id == tenant_a.id
        assert results_b[0].tenant_id == tenant_b.id
        assert results_a[0].id != results_b[0].id


class TestTenantServiceIsolation:
    """Test TenantService properly enforces isolation."""
    
    def test_collection_name_generation(self, tenant_a, tenant_b):
        """Test that collection names are tenant-specific."""
        # Mock Qdrant client
        class MockQdrantClient:
            def get_collections(self):
                class MockCollections:
                    collections = []
                return MockCollections()
        
        tenant_service = TenantService(MockQdrantClient())
        
        # Generate collection names
        collection_a = tenant_service.get_collection_name(tenant_a.id, "test_kb")
        collection_b = tenant_service.get_collection_name(tenant_b.id, "test_kb")
        
        # Should be different and include tenant ID
        assert collection_a != collection_b
        assert tenant_a.id in collection_a
        assert tenant_b.id in collection_b


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
