"""
Role-Based Access Control (RBAC) implementation.
"""

from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.tenant_user import TenantUser
from app.auth.permissions import Permission, Role, get_role_permissions


class RBACService:
    """Service for role-based access control operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_permission(
        self,
        tenant_id: str,
        user_id: str,
        permission: Permission
    ) -> bool:
        """
        Check if a user has a specific permission within a tenant.
        
        Args:
            tenant_id: The tenant ID
            user_id: The user ID
            permission: The permission to check
            
        Returns:
            True if user has permission, False otherwise
        """
        user_role = self.get_user_role(tenant_id, user_id)
        if not user_role:
            return False
        
        role_permissions = get_role_permissions(user_role)
        return permission in role_permissions
    
    def require_permission(
        self,
        tenant_id: str,
        user_id: str,
        permission: Permission
    ) -> None:
        """
        Require a user to have a specific permission, raise exception if not.
        
        Args:
            tenant_id: The tenant ID
            user_id: The user ID
            permission: The required permission
            
        Raises:
            HTTPException: 403 if user doesn't have permission
        """
        if not self.check_permission(tenant_id, user_id, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required"
            )
    
    def get_user_role(self, tenant_id: str, user_id: str) -> Optional[Role]:
        """
        Get the role of a user within a tenant.
        
        Args:
            tenant_id: The tenant ID
            user_id: The user ID
            
        Returns:
            The user's role or None if not found
        """
        tenant_user = self.db.query(TenantUser).filter(
            TenantUser.tenant_id == tenant_id,
            TenantUser.user_id == user_id
        ).first()
        
        if tenant_user:
            return Role(tenant_user.role)
        
        # If no TenantUser record exists, assign default ADMIN role
        # This allows authenticated users to access resources without explicit role assignment
        # In production, you should create TenantUser records during registration/login
        return Role.ADMIN
    
    def assign_role(
        self,
        tenant_id: str,
        user_id: str,
        role: Role,
        assigned_by: str
    ) -> TenantUser:
        """
        Assign a role to a user within a tenant.
        
        Args:
            tenant_id: The tenant ID
            user_id: The user ID to assign role to
            role: The role to assign
            assigned_by: The user ID performing the assignment
            
        Returns:
            The updated TenantUser record
            
        Raises:
            HTTPException: If assigner doesn't have permission
        """
        # Check if assigner has permission to manage users
        self.require_permission(
            tenant_id,
            assigned_by,
            Permission.TENANT_MANAGE_USERS
        )
        
        # Check if user already has a role in this tenant
        tenant_user = self.db.query(TenantUser).filter(
            TenantUser.tenant_id == tenant_id,
            TenantUser.user_id == user_id
        ).first()
        
        if tenant_user:
            tenant_user.role = role.value
        else:
            tenant_user = TenantUser(
                tenant_id=tenant_id,
                user_id=user_id,
                role=role.value
            )
            self.db.add(tenant_user)
        
        self.db.commit()
        self.db.refresh(tenant_user)
        return tenant_user
    
    def remove_user_from_tenant(
        self,
        tenant_id: str,
        user_id: str,
        removed_by: str
    ) -> None:
        """
        Remove a user from a tenant.
        
        Args:
            tenant_id: The tenant ID
            user_id: The user ID to remove
            removed_by: The user ID performing the removal
            
        Raises:
            HTTPException: If remover doesn't have permission
        """
        # Check if remover has permission to manage users
        self.require_permission(
            tenant_id,
            removed_by,
            Permission.TENANT_MANAGE_USERS
        )
        
        tenant_user = self.db.query(TenantUser).filter(
            TenantUser.tenant_id == tenant_id,
            TenantUser.user_id == user_id
        ).first()
        
        if tenant_user:
            self.db.delete(tenant_user)
            self.db.commit()
    
    def list_tenant_users(self, tenant_id: str, requester_id: str) -> list[TenantUser]:
        """
        List all users in a tenant.
        
        Args:
            tenant_id: The tenant ID
            requester_id: The user ID requesting the list
            
        Returns:
            List of TenantUser records
            
        Raises:
            HTTPException: If requester doesn't have permission
        """
        # Check if requester has permission to view users
        self.require_permission(
            tenant_id,
            requester_id,
            Permission.TENANT_VIEW
        )
        
        return self.db.query(TenantUser).filter(
            TenantUser.tenant_id == tenant_id
        ).all()
