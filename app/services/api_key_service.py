"""
API Key Service - handles API key generation, validation, and management.
"""
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from passlib.hash import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.tenant_api_key import TenantAPIKey
from ..models.tenant import Tenant


class APIKeyService:
    """Service for managing tenant API keys."""
    
    # Configuration
    KEY_PREFIX = "sk_live_"
    KEY_LENGTH = 32  # Total length including prefix
    MAX_KEYS_PER_TENANT = 10
    BCRYPT_ROUNDS = 12
    
    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a secure random API key.
        
        Format: sk_live_<24_random_chars>
        
        Returns:
            Generated API key string
        """
        # Generate 24 random characters (alphanumeric)
        random_length = APIKeyService.KEY_LENGTH - len(APIKeyService.KEY_PREFIX)
        random_chars = ''.join(
            secrets.choice(string.ascii_letters + string.digits)
            for _ in range(random_length)
        )
        return f"{APIKeyService.KEY_PREFIX}{random_chars}"
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Hash an API key using bcrypt.
        
        Args:
            api_key: Plain API key string
            
        Returns:
            Hashed API key
        """
        return bcrypt.hash(api_key, rounds=APIKeyService.BCRYPT_ROUNDS)
    
    @staticmethod
    def verify_api_key(api_key: str, key_hash: str) -> bool:
        """
        Verify an API key against its hash.
        
        Args:
            api_key: Plain API key string
            key_hash: Hashed API key from database
            
        Returns:
            True if key matches, False otherwise
        """
        try:
            return bcrypt.verify(api_key, key_hash)
        except Exception:
            return False
    
    @staticmethod
    def get_key_prefix(api_key: str) -> str:
        """
        Extract display prefix from API key.
        
        Shows first 12 chars and last 4 chars: sk_live_abc...xyz
        
        Args:
            api_key: Full API key
            
        Returns:
            Display prefix
        """
        if len(api_key) <= 16:
            return api_key
        return f"{api_key[:12]}...{api_key[-4:]}"
    
    @staticmethod
    def create_api_key(
        db: Session,
        tenant_id: str,
        name: str,
        expires_in_days: Optional[int] = None,
        permissions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new API key for a tenant.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            name: Friendly name for the key
            expires_in_days: Optional expiration in days
            permissions: Optional list of permissions (defaults to tenant permissions)
            
        Returns:
            Dictionary with key details (includes full key - only shown once!)
            
        Raises:
            ValueError: If tenant not found or max keys reached
        """
        # Verify tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        if not tenant.is_active:
            raise ValueError(f"Tenant {tenant_id} is not active")
        
        # Check max keys limit
        active_keys_count = db.query(TenantAPIKey).filter(
            and_(
                TenantAPIKey.tenant_id == tenant_id,
                TenantAPIKey.is_active == True
            )
        ).count()
        
        if active_keys_count >= APIKeyService.MAX_KEYS_PER_TENANT:
            raise ValueError(
                f"Maximum API keys limit reached ({APIKeyService.MAX_KEYS_PER_TENANT}). "
                "Please revoke an existing key first."
            )
        
        # Generate API key
        api_key = APIKeyService.generate_api_key()
        key_hash = APIKeyService.hash_api_key(api_key)
        key_prefix = APIKeyService.get_key_prefix(api_key)
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Create API key record
        api_key_record = TenantAPIKey(
            tenant_id=tenant_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=permissions or [],
            expires_at=expires_at,
            is_active=True
        )
        
        db.add(api_key_record)
        db.commit()
        db.refresh(api_key_record)
        
        # Return key details (including full key - only time it's shown!)
        return {
            "id": api_key_record.id,
            "api_key": api_key,  # IMPORTANT: Only returned here!
            "key_prefix": key_prefix,
            "name": name,
            "tenant_id": tenant_id,
            "permissions": api_key_record.permissions,
            "expires_at": api_key_record.expires_at.isoformat() if api_key_record.expires_at else None,
            "created_at": api_key_record.created_at.isoformat(),
            "message": "Save this API key securely. It will not be shown again."
        }
    
    @staticmethod
    def validate_api_key(db: Session, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate an API key and return tenant information.
        
        Args:
            db: Database session
            api_key: API key to validate
            
        Returns:
            Dictionary with tenant_id and permissions if valid, None otherwise
        """
        # Get all active API keys (we need to check hashes)
        active_keys = db.query(TenantAPIKey).filter(
            TenantAPIKey.is_active == True
        ).all()
        
        for key_record in active_keys:
            # Check if key matches
            if APIKeyService.verify_api_key(api_key, key_record.key_hash):
                # Check expiration
                if key_record.is_expired():
                    return None
                
                # Update last used
                key_record.last_used_at = datetime.utcnow()
                key_record.usage_count += 1
                db.commit()
                
                # Return tenant info
                return {
                    "tenant_id": key_record.tenant_id,
                    "api_key_id": key_record.id,
                    "permissions": key_record.permissions,
                    "key_name": key_record.name
                }
        
        return None
    
    @staticmethod
    def list_api_keys(db: Session, tenant_id: str) -> List[Dict[str, Any]]:
        """
        List all API keys for a tenant.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            
        Returns:
            List of API key details (without full keys)
        """
        keys = db.query(TenantAPIKey).filter(
            TenantAPIKey.tenant_id == tenant_id
        ).order_by(TenantAPIKey.created_at.desc()).all()
        
        return [key.to_dict() for key in keys]
    
    @staticmethod
    def revoke_api_key(db: Session, tenant_id: str, key_id: str) -> bool:
        """
        Revoke (deactivate) an API key.
        
        Args:
            db: Database session
            tenant_id: Tenant ID (for authorization)
            key_id: API key ID to revoke
            
        Returns:
            True if revoked, False if not found
        """
        key = db.query(TenantAPIKey).filter(
            and_(
                TenantAPIKey.id == key_id,
                TenantAPIKey.tenant_id == tenant_id
            )
        ).first()
        
        if not key:
            return False
        
        key.is_active = False
        key.updated_at = datetime.utcnow()
        db.commit()
        
        return True
    
    @staticmethod
    def delete_api_key(db: Session, tenant_id: str, key_id: str) -> bool:
        """
        Permanently delete an API key.
        
        Args:
            db: Database session
            tenant_id: Tenant ID (for authorization)
            key_id: API key ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        key = db.query(TenantAPIKey).filter(
            and_(
                TenantAPIKey.id == key_id,
                TenantAPIKey.tenant_id == tenant_id
            )
        ).first()
        
        if not key:
            return False
        
        db.delete(key)
        db.commit()
        
        return True
    
    @staticmethod
    def rotate_api_key(
        db: Session,
        tenant_id: str,
        old_key_id: str,
        new_key_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rotate an API key (create new, revoke old).
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            old_key_id: ID of key to rotate
            new_key_name: Optional name for new key
            
        Returns:
            New API key details
            
        Raises:
            ValueError: If old key not found
        """
        # Get old key
        old_key = db.query(TenantAPIKey).filter(
            and_(
                TenantAPIKey.id == old_key_id,
                TenantAPIKey.tenant_id == tenant_id
            )
        ).first()
        
        if not old_key:
            raise ValueError(f"API key {old_key_id} not found")
        
        # Create new key with same settings
        new_name = new_key_name or f"{old_key.name} (rotated)"
        expires_in_days = None
        if old_key.expires_at:
            days_remaining = (old_key.expires_at - datetime.utcnow()).days
            expires_in_days = max(days_remaining, 1)
        
        new_key = APIKeyService.create_api_key(
            db=db,
            tenant_id=tenant_id,
            name=new_name,
            expires_in_days=expires_in_days,
            permissions=old_key.permissions
        )
        
        # Revoke old key
        old_key.is_active = False
        old_key.updated_at = datetime.utcnow()
        db.commit()
        
        new_key["rotated_from"] = old_key_id
        return new_key
