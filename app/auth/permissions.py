"""
Permission constants and definitions for RBAC system.
"""

from enum import Enum
from typing import Set


class Permission(str, Enum):
    """Permission constants for tenant operations."""
    
    # Knowledge Base permissions
    KB_VIEW = "kb:view"
    KB_CREATE = "kb:create"
    KB_UPDATE = "kb:update"
    KB_DELETE = "kb:delete"
    KB_UPLOAD = "kb:upload"
    KB_QUERY = "kb:query"
    
    # Database permissions
    DB_VIEW = "db:view"
    DB_CONNECT = "db:connect"
    DB_QUERY = "db:query"
    DB_EXECUTE = "db:execute"
    DB_MANAGE = "db:manage"
    
    # File permissions
    FILE_VIEW = "file:view"
    FILE_UPLOAD = "file:upload"
    FILE_DOWNLOAD = "file:download"
    FILE_DELETE = "file:delete"
    
    # Tenant permissions
    TENANT_VIEW = "tenant:view"
    TENANT_UPDATE = "tenant:update"
    TENANT_MANAGE_USERS = "tenant:manage_users"
    TENANT_MANAGE_SETTINGS = "tenant:manage_settings"
    
    # Admin permissions
    ADMIN_VIEW_ALL = "admin:view_all"
    ADMIN_MANAGE_TENANTS = "admin:manage_tenants"
    ADMIN_MANAGE_USERS = "admin:manage_users"
    ADMIN_VIEW_METRICS = "admin:view_metrics"
    ADMIN_MANAGE_QUOTAS = "admin:manage_quotas"


class Role(str, Enum):
    """Role definitions with hierarchical permissions."""
    
    VIEWER = "viewer"
    USER = "user"
    MANAGER = "manager"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.KB_VIEW,
        Permission.KB_QUERY,
        Permission.DB_VIEW,
        Permission.FILE_VIEW,
        Permission.TENANT_VIEW,
    },
    Role.USER: {
        Permission.KB_VIEW,
        Permission.KB_QUERY,
        Permission.KB_UPLOAD,
        Permission.DB_VIEW,
        Permission.DB_CONNECT,
        Permission.DB_QUERY,
        Permission.FILE_VIEW,
        Permission.FILE_UPLOAD,
        Permission.FILE_DOWNLOAD,
        Permission.TENANT_VIEW,
    },
    Role.MANAGER: {
        Permission.KB_VIEW,
        Permission.KB_CREATE,
        Permission.KB_UPDATE,
        Permission.KB_DELETE,
        Permission.KB_UPLOAD,
        Permission.KB_QUERY,
        Permission.DB_VIEW,
        Permission.DB_CONNECT,
        Permission.DB_QUERY,
        Permission.DB_EXECUTE,
        Permission.DB_MANAGE,
        Permission.FILE_VIEW,
        Permission.FILE_UPLOAD,
        Permission.FILE_DOWNLOAD,
        Permission.FILE_DELETE,
        Permission.TENANT_VIEW,
        Permission.TENANT_UPDATE,
        Permission.TENANT_MANAGE_USERS,
    },
    Role.ADMIN: {
        Permission.KB_VIEW,
        Permission.KB_CREATE,
        Permission.KB_UPDATE,
        Permission.KB_DELETE,
        Permission.KB_UPLOAD,
        Permission.KB_QUERY,
        Permission.DB_VIEW,
        Permission.DB_CONNECT,
        Permission.DB_QUERY,
        Permission.DB_EXECUTE,
        Permission.DB_MANAGE,
        Permission.FILE_VIEW,
        Permission.FILE_UPLOAD,
        Permission.FILE_DOWNLOAD,
        Permission.FILE_DELETE,
        Permission.TENANT_VIEW,
        Permission.TENANT_UPDATE,
        Permission.TENANT_MANAGE_USERS,
        Permission.TENANT_MANAGE_SETTINGS,
    },
    Role.SUPER_ADMIN: set(Permission),  # All permissions
}


def get_role_permissions(role: Role) -> Set[Permission]:
    """Get all permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: Role, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())
