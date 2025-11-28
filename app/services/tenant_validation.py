"""
Tenant validation service with caching for performance.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models.tenant import Tenant

logger = logging.getLogger(__name__)


class TenantValidationService:
    """
    Service for validating tenant existence, status, and permissions.
    Includes caching to reduce database queries.
    """
    
    def __init__(self, cache_ttl_seconds: int = 300):
        """
        Initialize tenant validation service.
        
        Args:
            cache_ttl_seconds: Time-to-live for cached tenant data (default 5 minutes)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)
    
    def _get_from_cache(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get tenant data from cache if not expired.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Cached tenant data or None if expired/not found
        """
        if tenant_id in self._cache:
            cached_data = self._cache[tenant_id]
            if datetime.utcnow() < cached_data["expires_at"]:
                logger.debug(f"Cache hit for tenant {tenant_id}")
                return cached_data["data"]
            else:
                # Remove expired entry
                del self._cache[tenant_id]
                logger.debug(f"Cache expired for tenant {tenant_id}")
        
        return None
    
    def _add_to_cache(self, tenant_id: str, tenant_data: Dict[str, Any]) -> None:
        """
        Add tenant data to cache.
        
        Args:
            tenant_id: Tenant ID
            tenant_data: Tenant data to cache
        """
        self._cache[tenant_id] = {
            "data": tenant_data,
            "expires_at": datetime.utcnow() + self._cache_ttl
        }
        logger.debug(f"Cached tenant {tenant_id}")
    
    def invalidate_cache(self, tenant_id: Optional[str] = None) -> None:
        """
        Invalidate cache for a specific tenant or all tenants.
        
        Args:
            tenant_id: Specific tenant ID to invalidate, or None for all
        """
        if tenant_id:
            if tenant_id in self._cache:
                del self._cache[tenant_id]
                logger.info(f"Invalidated cache for tenant {tenant_id}")
        else:
            self._cache.clear()
            logger.info("Invalidated all tenant cache")
    
    def validate_tenant_exists(self, tenant_id: str, db: Session) -> Tenant:
        """
        Check if tenant exists in database.
        
        Args:
            tenant_id: Tenant ID to validate
            db: Database session
            
        Returns:
            Tenant object
            
        Raises:
            HTTPException: If tenant not found
        """
        # Check cache first
        cached_data = self._get_from_cache(tenant_id)
        if cached_data:
            # Return a Tenant-like object from cache
            tenant = Tenant(**cached_data)
            return tenant
        
        # Query database
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        
        if not tenant:
            logger.warning(f"Tenant not found: {tenant_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found"
            )
        
        # Cache tenant data
        tenant_data = {
            "id": tenant.id,
            "name": tenant.name,
            "is_active": tenant.is_active,
            "settings": tenant.settings,
            "created_at": tenant.created_at
        }
        self._add_to_cache(tenant_id, tenant_data)
        
        return tenant
    
    def validate_tenant_active(self, tenant_id: str, db: Session) -> Tenant:
        """
        Check if tenant exists and is active.
        
        Args:
            tenant_id: Tenant ID to validate
            db: Database session
            
        Returns:
            Tenant object
            
        Raises:
            HTTPException: If tenant not found or inactive
        """
        tenant = self.validate_tenant_exists(tenant_id, db)
        
        if not tenant.is_active:
            logger.warning(f"Tenant inactive: {tenant_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tenant {tenant_id} is inactive"
            )
        
        return tenant
    
    def validate_tenant_permission(
        self,
        tenant_id: str,
        permission: str,
        db: Session
    ) -> bool:
        """
        Validate if tenant has a specific permission.
        
        Args:
            tenant_id: Tenant ID
            permission: Permission to check (e.g., "upload", "query", "admin")
            db: Database session
            
        Returns:
            True if tenant has permission
            
        Raises:
            HTTPException: If tenant not found, inactive, or lacks permission
        """
        tenant = self.validate_tenant_active(tenant_id, db)
        
        # Check permissions in tenant settings
        settings = tenant.settings or {}
        permissions = settings.get("permissions", [])
        
        # Admin tenants have all permissions
        if "admin" in permissions:
            return True
        
        if permission not in permissions:
            logger.warning(
                f"Tenant {tenant_id} lacks permission: {permission}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tenant does not have '{permission}' permission"
            )
        
        return True
    
    def check_tenant_feature_flag(
        self,
        tenant_id: str,
        feature: str,
        db: Session
    ) -> bool:
        """
        Check if a feature flag is enabled for tenant.
        
        Args:
            tenant_id: Tenant ID
            feature: Feature flag name
            db: Database session
            
        Returns:
            True if feature is enabled, False otherwise
        """
        tenant = self.validate_tenant_active(tenant_id, db)
        
        settings = tenant.settings or {}
        feature_flags = settings.get("feature_flags", {})
        
        return feature_flags.get(feature, False)


# Global instance
tenant_validation_service = TenantValidationService()
