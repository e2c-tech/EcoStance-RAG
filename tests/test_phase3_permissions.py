"""
Test Phase 3: Permissions and Roles (Standalone)
Tests permission definitions without requiring FastAPI or database.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import directly from module file
import importlib.util
spec = importlib.util.spec_from_file_location("permissions", "app/auth/permissions.py")
permissions_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(permissions_module)

Permission = permissions_module.Permission
Role = permissions_module.Role
get_role_permissions = permissions_module.get_role_permissions
has_permission = permissions_module.has_permission


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


def test_role_hierarchy():
    """Test that role hierarchy is correct."""
    print("\n=== Testing Role Hierarchy ===")
    
    # Viewer < User < Manager < Admin < Super Admin
    viewer_perms = get_role_permissions(Role.VIEWER)
    user_perms = get_role_permissions(Role.USER)
    manager_perms = get_role_permissions(Role.MANAGER)
    admin_perms = get_role_permissions(Role.ADMIN)
    super_admin_perms = get_role_permissions(Role.SUPER_ADMIN)
    
    # Check hierarchy
    assert len(viewer_perms) < len(user_perms)
    assert len(user_perms) < len(manager_perms)
    assert len(manager_perms) < len(admin_perms)
    assert len(admin_perms) < len(super_admin_perms)
    
    print(f"✓ Viewer: {len(viewer_perms)} permissions")
    print(f"✓ User: {len(user_perms)} permissions")
    print(f"✓ Manager: {len(manager_perms)} permissions")
    print(f"✓ Admin: {len(admin_perms)} permissions")
    print(f"✓ Super Admin: {len(super_admin_perms)} permissions")
    print("✓ Role hierarchy verified")


def test_permission_categories():
    """Test permission categories."""
    print("\n=== Testing Permission Categories ===")
    
    kb_perms = [p for p in Permission if p.value.startswith("kb:")]
    db_perms = [p for p in Permission if p.value.startswith("db:")]
    file_perms = [p for p in Permission if p.value.startswith("file:")]
    tenant_perms = [p for p in Permission if p.value.startswith("tenant:")]
    admin_perms = [p for p in Permission if p.value.startswith("admin:")]
    
    print(f"✓ Knowledge Base permissions: {len(kb_perms)}")
    print(f"✓ Database permissions: {len(db_perms)}")
    print(f"✓ File permissions: {len(file_perms)}")
    print(f"✓ Tenant permissions: {len(tenant_perms)}")
    print(f"✓ Admin permissions: {len(admin_perms)}")
    
    total = len(kb_perms) + len(db_perms) + len(file_perms) + len(tenant_perms) + len(admin_perms)
    print(f"✓ Total permissions: {total}")


def run_all_tests():
    """Run all permission tests."""
    print("=" * 60)
    print("PHASE 3: PERMISSIONS & ROLES TESTS")
    print("=" * 60)
    
    try:
        test_permissions()
        test_role_hierarchy()
        test_permission_categories()
        
        print("\n" + "=" * 60)
        print("✓ ALL PERMISSION TESTS PASSED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
