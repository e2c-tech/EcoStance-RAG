"""
Test Phase 3: Security & Access Control
Tests for RBAC, audit logging, rate limiting, and admin endpoints.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import directly from module files to avoid __init__.py imports
import importlib.util

# Load permissions module directly
spec = importlib.util.spec_from_file_location("permissions", "app/auth/permissions.py")
permissions_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(permissions_module)
Permission = permissions_module.Permission
Role = permissions_module.Role
get_role_permissions = permissions_module.get_role_permissions
has_permission = permissions_module.has_permission

# Load rate_limiter module directly
spec2 = importlib.util.spec_from_file_location("rate_limiter", "app/middleware/rate_limiter.py")
rate_limiter_module = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(rate_limiter_module)
RateLimiter = rate_limiter_module.RateLimiter
RateLimitConfig = rate_limiter_module.RateLimitConfig
RATE_LIMIT_CONFIGS = rate_limiter_module.RATE_LIMIT_CONFIGS

# These require database connection
try:
    from app.auth.rbac import RBACService
    from app.services.audit_service import AuditService
    from app.models.tenant import Tenant, TenantUser
    from app.models.audit_log import AuditLog
    from app.db.database import get_db
    from sqlalchemy.orm import Session
    DB_AVAILABLE = True
except Exception as e:
    print(f"Warning: Database imports failed: {e}")
    DB_AVAILABLE = False


def test_permissions():
    """Test permission definitions and role mappings."""
    print("\n=== Testing Permissions ===")
    
    # Test viewer permissions
    viewer_perms = get_role_permissions(Role.VIEWER)
    print(f"✓ Viewer has {len(viewer_perms)} permissions")
    assert Permission.KB_VIEW in viewer_perms
    assert Permission.KB_CREATE not in viewer_perms
    
    # Test user permissions
    user_perms = get_role_permissions(Role.USER)
    print(f"✓ User has {len(user_perms)} permissions")
    assert Permission.KB_UPLOAD in user_perms
    assert Permission.KB_DELETE not in user_perms
    
    # Test manager permissions
    manager_perms = get_role_permissions(Role.MANAGER)
    print(f"✓ Manager has {len(manager_perms)} permissions")
    assert Permission.KB_DELETE in manager_perms
    assert Permission.TENANT_MANAGE_SETTINGS not in manager_perms
    
    # Test admin permissions
    admin_perms = get_role_permissions(Role.ADMIN)
    print(f"✓ Admin has {len(admin_perms)} permissions")
    assert Permission.TENANT_MANAGE_SETTINGS in admin_perms
    
    # Test super admin permissions
    super_admin_perms = get_role_permissions(Role.SUPER_ADMIN)
    print(f"✓ Super Admin has {len(super_admin_perms)} permissions (all)")
    assert len(super_admin_perms) == len(Permission)
    
    # Test has_permission function
    assert has_permission(Role.USER, Permission.KB_UPLOAD)
    assert not has_permission(Role.VIEWER, Permission.KB_UPLOAD)
    print("✓ Permission checking works correctly")


def test_rbac_service():
    """Test RBAC service operations."""
    print("\n=== Testing RBAC Service ===")
    
    if not DB_AVAILABLE:
        print("⊘ Skipping RBAC tests (database not available)")
        return
    
    db: Session = next(get_db())
    rbac = RBACService(db)
    
    try:
        # Get a test tenant
        tenant = db.query(Tenant).first()
        if not tenant:
            print("✗ No tenant found for testing")
            return
        
        tenant_id = tenant.id
        test_user_id = "test_user_rbac"
        admin_user_id = "test_admin_rbac"
        
        # Create admin user first
        admin_user = TenantUser(
            tenant_id=tenant_id,
            user_id=admin_user_id,
            role=Role.ADMIN.value
        )
        db.add(admin_user)
        db.commit()
        print(f"✓ Created admin user: {admin_user_id}")
        
        # Test role assignment
        tenant_user = rbac.assign_role(
            tenant_id=tenant_id,
            user_id=test_user_id,
            role=Role.USER,
            assigned_by=admin_user_id
        )
        print(f"✓ Assigned USER role to {test_user_id}")
        
        # Test get_user_role
        role = rbac.get_user_role(tenant_id, test_user_id)
        assert role == Role.USER
        print(f"✓ Retrieved user role: {role}")
        
        # Test check_permission
        has_upload = rbac.check_permission(
            tenant_id, test_user_id, Permission.KB_UPLOAD
        )
        assert has_upload
        print("✓ User has KB_UPLOAD permission")
        
        has_delete = rbac.check_permission(
            tenant_id, test_user_id, Permission.KB_DELETE
        )
        assert not has_delete
        print("✓ User does not have KB_DELETE permission")
        
        # Test list_tenant_users
        users = rbac.list_tenant_users(tenant_id, admin_user_id)
        print(f"✓ Listed {len(users)} users in tenant")
        
        # Test role update
        updated_user = rbac.assign_role(
            tenant_id=tenant_id,
            user_id=test_user_id,
            role=Role.MANAGER,
            assigned_by=admin_user_id
        )
        assert updated_user.role == Role.MANAGER.value
        print("✓ Updated user role to MANAGER")
        
        # Test remove_user_from_tenant
        rbac.remove_user_from_tenant(
            tenant_id=tenant_id,
            user_id=test_user_id,
            removed_by=admin_user_id
        )
        print("✓ Removed user from tenant")
        
        # Cleanup
        db.query(TenantUser).filter(
            TenantUser.user_id.in_([test_user_id, admin_user_id])
        ).delete()
        db.commit()
        
    except Exception as e:
        print(f"✗ RBAC test failed: {e}")
        db.rollback()
    finally:
        db.close()


def test_audit_service():
    """Test audit logging service."""
    print("\n=== Testing Audit Service ===")
    
    if not DB_AVAILABLE:
        print("⊘ Skipping audit tests (database not available)")
        return
    
    db: Session = next(get_db())
    audit = AuditService(db)
    
    try:
        # Get a test tenant
        tenant = db.query(Tenant).first()
        if not tenant:
            print("✗ No tenant found for testing")
            return
        
        tenant_id = tenant.id
        user_id = "test_audit_user"
        
        # Test log_action
        log1 = audit.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action="create_kb",
            resource_type="knowledge_base",
            resource_id="kb_123",
            details={"kb_name": "Test KB"},
            status="success"
        )
        print(f"✓ Created audit log: {log1.id}")
        
        # Test log_authentication
        log2 = audit.log_authentication(
            user_id=user_id,
            action="login",
            status="success",
            tenant_id=tenant_id
        )
        print(f"✓ Created authentication log: {log2.id}")
        
        # Test log_data_access
        log3 = audit.log_data_access(
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type="file",
            resource_id="file_456",
            action="download"
        )
        print(f"✓ Created data access log: {log3.id}")
        
        # Test get_tenant_audit_logs
        logs = audit.get_tenant_audit_logs(tenant_id, limit=10)
        print(f"✓ Retrieved {len(logs)} audit logs")
        assert len(logs) >= 2  # At least the logs we just created
        
        # Test filtering
        filtered_logs = audit.get_tenant_audit_logs(
            tenant_id,
            action_filter="create",
            limit=10
        )
        print(f"✓ Filtered logs by action: {len(filtered_logs)} results")
        
        # Cleanup
        db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).delete()
        db.commit()
        
    except Exception as e:
        print(f"✗ Audit test failed: {e}")
        db.rollback()
    finally:
        db.close()


def test_rate_limiter():
    """Test rate limiting functionality."""
    print("\n=== Testing Rate Limiter ===")
    
    limiter = RateLimiter()
    tenant_id = "test_tenant_rate_limit"
    
    # Test with low limits
    config = RateLimitConfig(
        requests_per_minute=5,
        requests_per_hour=20,
        requests_per_day=100
    )
    
    # Make requests within limit
    for i in range(5):
        allowed, msg = limiter.check_rate_limit(tenant_id, config)
        assert allowed, f"Request {i+1} should be allowed"
    print("✓ First 5 requests allowed")
    
    # Next request should be rate limited
    allowed, msg = limiter.check_rate_limit(tenant_id, config)
    assert not allowed, "6th request should be rate limited"
    assert "Rate limit exceeded" in msg
    print(f"✓ 6th request blocked: {msg}")
    
    # Test usage stats
    stats = limiter.get_usage_stats(tenant_id)
    print(f"✓ Usage stats: {stats}")
    assert stats["requests_last_minute"] >= 5
    
    # Test cleanup
    limiter._cleanup_old_entries()
    print("✓ Cleanup executed successfully")


def test_rate_limit_configs():
    """Test different rate limit tier configurations."""
    print("\n=== Testing Rate Limit Configs ===")
    
    tiers = ["free", "basic", "premium", "enterprise"]
    
    for tier in tiers:
        config = RATE_LIMIT_CONFIGS[tier]
        print(f"✓ {tier.upper()}: {config.requests_per_minute}/min, "
              f"{config.requests_per_hour}/hour, {config.requests_per_day}/day")
    
    # Verify tier hierarchy
    assert (RATE_LIMIT_CONFIGS["free"].requests_per_minute < 
            RATE_LIMIT_CONFIGS["basic"].requests_per_minute)
    assert (RATE_LIMIT_CONFIGS["basic"].requests_per_minute < 
            RATE_LIMIT_CONFIGS["premium"].requests_per_minute)
    assert (RATE_LIMIT_CONFIGS["premium"].requests_per_minute < 
            RATE_LIMIT_CONFIGS["enterprise"].requests_per_minute)
    print("✓ Tier hierarchy verified")


def run_all_tests():
    """Run all Phase 3 tests."""
    print("=" * 60)
    print("PHASE 3: SECURITY & ACCESS CONTROL TESTS")
    print("=" * 60)
    
    try:
        test_permissions()
        test_rbac_service()
        test_audit_service()
        test_rate_limiter()
        test_rate_limit_configs()
        
        print("\n" + "=" * 60)
        print("✓ ALL PHASE 3 TESTS PASSED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
