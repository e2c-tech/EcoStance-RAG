"""
Permission decorators for cleaner endpoint authorization.
"""

from functools import wraps
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Callable

from .permissions import Permission
from .rbac import RBACService
from .dependencies import get_current_user
from ..db.database import get_db
from ..services.audit_service import AuditService


def require_permission(permission: Permission, audit_action: str = None):
    """
    Decorator to require a specific permission for an endpoint.
    
    Args:
        permission: The required permission
        audit_action: Optional action name for audit logging
        
    Usage:
        @router.get("/endpoint")
        @require_permission(Permission.KB_VIEW)
        async def endpoint(current_user: dict = Depends(get_current_user)):
            # Your code here
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies from kwargs
            current_user = kwargs.get('current_user')
            db = kwargs.get('db')
            request = kwargs.get('request')
            
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Missing required dependencies (current_user, db)"
                )
            
            tenant_id = current_user["tenant_id"]
            user_id = current_user["user_id"]
            
            # Check permission
            rbac = RBACService(db)
            try:
                rbac.require_permission(tenant_id, user_id, permission)
            except HTTPException as e:
                # Log permission denial
                if audit_action and request:
                    audit = AuditService(db)
                    audit.log_action(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        action=audit_action,
                        status="failure",
                        error_message=f"Permission denied: {permission.value}",
                        request=request
                    )
                raise e
            
            # Call the original function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_any_permission(*permissions: Permission):
    """
    Decorator to require any one of multiple permissions.
    
    Args:
        *permissions: Variable number of permissions (user needs at least one)
        
    Usage:
        @router.get("/endpoint")
        @require_any_permission(Permission.KB_VIEW, Permission.ADMIN_VIEW_ALL)
        async def endpoint(current_user: dict = Depends(get_current_user)):
            # Your code here
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            db = kwargs.get('db')
            
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Missing required dependencies"
                )
            
            tenant_id = current_user["tenant_id"]
            user_id = current_user["user_id"]
            
            # Check if user has any of the permissions
            rbac = RBACService(db)
            has_permission = False
            
            for perm in permissions:
                if rbac.check_permission(tenant_id, user_id, perm):
                    has_permission = True
                    break
            
            if not has_permission:
                perm_list = ", ".join([p.value for p in permissions])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: requires one of [{perm_list}]"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_all_permissions(*permissions: Permission):
    """
    Decorator to require all specified permissions.
    
    Args:
        *permissions: Variable number of permissions (user needs all of them)
        
    Usage:
        @router.post("/endpoint")
        @require_all_permissions(Permission.KB_CREATE, Permission.FILE_UPLOAD)
        async def endpoint(current_user: dict = Depends(get_current_user)):
            # Your code here
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            db = kwargs.get('db')
            
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Missing required dependencies"
                )
            
            tenant_id = current_user["tenant_id"]
            user_id = current_user["user_id"]
            
            # Check if user has all permissions
            rbac = RBACService(db)
            
            for perm in permissions:
                rbac.require_permission(tenant_id, user_id, perm)
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
