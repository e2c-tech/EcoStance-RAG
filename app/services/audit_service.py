"""
Audit logging service for tracking tenant operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Request

from app.models.audit_log import AuditLog


class AuditService:
    """Service for audit logging operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_action(
        self,
        tenant_id: str,
        user_id: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        request: Optional[Request] = None
    ) -> AuditLog:
        """
        Log an audit event.
        
        Args:
            tenant_id: The tenant ID
            user_id: The user ID performing the action
            action: The action being performed (e.g., "create_kb", "upload_file")
            resource_type: Type of resource (e.g., "knowledge_base", "file")
            resource_id: ID of the resource being acted upon
            details: Additional details about the action
            status: Status of the action (success, failure, error)
            error_message: Error message if status is failure/error
            request: FastAPI request object for IP and user agent
            
        Returns:
            The created AuditLog record
        """
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
        
        audit_log = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
            timestamp=datetime.utcnow()
        )
        
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        
        return audit_log
    
    def log_authentication(
        self,
        user_id: str,
        action: str,
        status: str,
        tenant_id: Optional[str] = None,
        error_message: Optional[str] = None,
        request: Optional[Request] = None
    ) -> AuditLog:
        """
        Log an authentication event.
        
        Args:
            user_id: The user ID
            action: The authentication action (e.g., "login", "logout", "token_refresh")
            status: Status of the action
            tenant_id: Optional tenant ID
            error_message: Error message if failed
            request: FastAPI request object
            
        Returns:
            The created AuditLog record
        """
        return self.log_action(
            tenant_id=tenant_id or "system",
            user_id=user_id,
            action=f"auth_{action}",
            resource_type="authentication",
            status=status,
            error_message=error_message,
            request=request
        )
    
    def log_data_access(
        self,
        tenant_id: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str = "access",
        request: Optional[Request] = None
    ) -> AuditLog:
        """
        Log a data access event.
        
        Args:
            tenant_id: The tenant ID
            user_id: The user ID
            resource_type: Type of resource accessed
            resource_id: ID of the resource
            action: The access action (e.g., "view", "download")
            request: FastAPI request object
            
        Returns:
            The created AuditLog record
        """
        return self.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action=f"{action}_{resource_type}",
            resource_type=resource_type,
            resource_id=resource_id,
            status="success",
            request=request
        )
    
    def get_tenant_audit_logs(
        self,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
        action_filter: Optional[str] = None,
        user_filter: Optional[str] = None
    ) -> list[AuditLog]:
        """
        Get audit logs for a tenant.
        
        Args:
            tenant_id: The tenant ID
            limit: Maximum number of logs to return
            offset: Number of logs to skip
            action_filter: Optional action filter
            user_filter: Optional user ID filter
            
        Returns:
            List of AuditLog records
        """
        query = self.db.query(AuditLog).filter(
            AuditLog.tenant_id == tenant_id
        )
        
        if action_filter:
            query = query.filter(AuditLog.action.like(f"%{action_filter}%"))
        
        if user_filter:
            query = query.filter(AuditLog.user_id == user_filter)
        
        return query.order_by(
            AuditLog.timestamp.desc()
        ).limit(limit).offset(offset).all()
