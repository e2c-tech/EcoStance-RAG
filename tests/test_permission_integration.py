"""
Integration tests for RBAC permission checks on all endpoints.
Tests that endpoints properly enforce permissions based on user roles.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db
from app.models.tenant import Tenant, TenantUser
from app.auth.permissions import Role
from app.auth.jwt_handler import create_access_token
from sqlalchemy.orm import Session
import uuid

client = TestClient(app)


def create_test_tenant(db: Session, name: str = "Test Tenant") -> Tenant:
    """Create a test tenant."""
    tenant = Tenant(
        name=name,
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        is_active=True,
        settings={}
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def create_test_user(db: Session, tenant_id: str, role: Role) -> tuple[str, str]:
    """
    Create a test user with specified role.
    Returns (user_id, token).
    """
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    
    # Create tenant user
    tenant_user = TenantUser(
        tenant_id=tenant_id,
        user_id=user_id,
        role=role.value
    )
    db.add(tenant_user)
    db.commit()
    
    # Generate token
    token = create_access_token(
        data={"user_id": user_id, "tenant_id": tenant_id}
    )
    
    return user_id, token


def test_upload_requires_file_upload_permission():
    """Test that upload endpoint requires FILE_UPLOAD permission."""
    print("\n=== Testing Upload Permission ===")
    
    db: Session = next(get_db())
    
    try:
        # Create test tenant
        tenant = create_test_tenant(db)
        
        # Create viewer (no upload permission)
        viewer_id, viewer_token = create_test_user(db, tenant.id, Role.VIEWER)
        
        # Attempt upload as viewer
        response = client.post(
            "/api/v1/upload/",
            headers={"Authorization": f"Bearer {viewer_token}"},
            files={"file": ("test.txt", b"test content", "text/plain")}
        )
        
        # Should be denied
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert "Permission denied" in response.json()["detail"]
        print("✓ Viewer correctly denied upload permission")
        
        # Create user (has upload permission)
        user_id, user_token = create_test_user(db, tenant.id, Role.USER)
        
        # Attempt upload as user
        response = client.post(
            "/api/v1/upload/",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("test.txt", b"test content", "text/plain")}
        )
        
        # Should succeed
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ User correctly allowed upload permission")
        
        # Cleanup
        db.query(TenantUser).filter(
            TenantUser.user_id.in_([viewer_id, user_id])
        ).delete()
        db.query(Tenant).filter(Tenant.id == tenant.id).delete()
        db.commit()
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def test_query_requires_kb_query_permission():
    """Test that query endpoint requires KB_QUERY permission."""
    print("\n=== Testing Query Permission ===")
    
    db: Session = next(get_db())
    
    try:
        # Create test tenant
        tenant = create_test_tenant(db)
        
        # Create viewer (has query permission)
        viewer_id, viewer_token = create_test_user(db, tenant.id, Role.VIEWER)
        
        # Attempt query as viewer (should succeed - viewers can query)
        response = client.post(
            "/api/v1/query/",
            headers={"Authorization": f"Bearer {viewer_token}"},
            data={
                "kb_name": "test_kb",
                "query": "test query",
                "chat_history": []
            }
        )
        
        # May fail due to KB not existing, but should not be permission error
        if response.status_code == 403:
            print(f"✗ Viewer incorrectly denied query permission")
            assert False, "Viewer should have query permission"
        else:
            print("✓ Viewer correctly allowed query permission")
        
        # Cleanup
        db.query(TenantUser).filter(TenantUser.user_id == viewer_id).delete()
        db.query(Tenant).filter(Tenant.id == tenant.id).delete()
        db.commit()
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def test_delete_kb_requires_kb_delete_permission():
    """Test that delete KB endpoint requires KB_DELETE permission."""
    print("\n=== Testing Delete KB Permission ===")
    
    db: Session = next(get_db())
    
    try:
        # Create test tenant
        tenant = create_test_tenant(db)
        
        # Create user (no delete permission)
        user_id, user_token = create_test_user(db, tenant.id, Role.USER)
        
        # Attempt delete as user
        response = client.delete(
            "/api/v1/manage/knowledge-bases/test_kb",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        # Should be denied
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert "Permission denied" in response.json()["detail"]
        print("✓ User correctly denied delete KB permission")
        
        # Create manager (has delete permission)
        manager_id, manager_token = create_test_user(db, tenant.id, Role.MANAGER)
        
        # Attempt delete as manager
        response = client.delete(
            "/api/v1/manage/knowledge-bases/test_kb",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        # May fail due to KB not existing, but should not be permission error
        if response.status_code == 403:
            print(f"✗ Manager incorrectly denied delete KB permission")
            assert False, "Manager should have delete KB permission"
        else:
            print("✓ Manager correctly allowed delete KB permission")
        
        # Cleanup
        db.query(TenantUser).filter(
            TenantUser.user_id.in_([user_id, manager_id])
        ).delete()
        db.query(Tenant).filter(Tenant.id == tenant.id).delete()
        db.commit()
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def test_file_download_requires_permission():
    """Test that file download requires FILE_DOWNLOAD permission."""
    print("\n=== Testing File Download Permission ===")
    
    db: Session = next(get_db())
    
    try:
        # Create test tenant
        tenant = create_test_tenant(db)
        
        # Create viewer (no download permission)
        viewer_id, viewer_token = create_test_user(db, tenant.id, Role.VIEWER)
        
        # Attempt download as viewer
        response = client.get(
            "/api/v1/files/test.txt",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        
        # Should be denied
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Viewer correctly denied file download permission")
        
        # Create user (has download permission)
        user_id, user_token = create_test_user(db, tenant.id, Role.USER)
        
        # Attempt download as user
        response = client.get(
            "/api/v1/files/test.txt",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        # May fail due to file not existing, but should not be permission error
        if response.status_code == 403:
            print(f"✗ User incorrectly denied file download permission")
            assert False, "User should have download permission"
        else:
            print("✓ User correctly allowed file download permission")
        
        # Cleanup
        db.query(TenantUser).filter(
            TenantUser.user_id.in_([viewer_id, user_id])
        ).delete()
        db.query(Tenant).filter(Tenant.id == tenant.id).delete()
        db.commit()
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def test_db_execute_requires_permission():
    """Test that DB execute requires DB_EXECUTE permission."""
    print("\n=== Testing DB Execute Permission ===")
    
    db: Session = next(get_db())
    
    try:
        # Create test tenant
        tenant = create_test_tenant(db)
        
        # Create user (no execute permission)
        user_id, user_token = create_test_user(db, tenant.id, Role.USER)
        
        # Attempt execute as user
        response = client.post(
            "/api/v1/db/execute-query",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"query": "SELECT 1", "db_id": "default"}
        )
        
        # Should be denied
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert "Permission denied" in response.json()["detail"]
        print("✓ User correctly denied DB execute permission")
        
        # Create manager (has execute permission)
        manager_id, manager_token = create_test_user(db, tenant.id, Role.MANAGER)
        
        # Attempt execute as manager
        response = client.post(
            "/api/v1/db/execute-query",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={"query": "SELECT 1", "db_id": "default"}
        )
        
        # May fail due to DB not connected, but should not be permission error
        if response.status_code == 403:
            print(f"✗ Manager incorrectly denied DB execute permission")
            assert False, "Manager should have execute permission"
        else:
            print("✓ Manager correctly allowed DB execute permission")
        
        # Cleanup
        db.query(TenantUser).filter(
            TenantUser.user_id.in_([user_id, manager_id])
        ).delete()
        db.query(Tenant).filter(Tenant.id == tenant.id).delete()
        db.commit()
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def run_all_tests():
    """Run all permission integration tests."""
    print("=" * 60)
    print("PERMISSION INTEGRATION TESTS")
    print("=" * 60)
    
    try:
        test_upload_requires_file_upload_permission()
        test_query_requires_kb_query_permission()
        test_delete_kb_requires_kb_delete_permission()
        test_file_download_requires_permission()
        test_db_execute_requires_permission()
        
        print("\n" + "=" * 60)
        print("✓ ALL PERMISSION TESTS PASSED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
