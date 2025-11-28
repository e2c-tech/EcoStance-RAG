"""
API Key Management Router - endpoints for managing tenant API keys.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from ..db.database import get_db
from ..services.api_key_service import APIKeyService
from ..auth.dependencies import get_current_user
from ..services.audit_service import AuditService


router = APIRouter(prefix="/api/v1/api-keys", tags=["API Keys"])


# Request/Response Models
class CreateAPIKeyRequest(BaseModel):
    """Request model for creating an API key."""
    name: str = Field(..., min_length=1, max_length=255, description="Friendly name for the API key")
    expires_in_days: Optional[int] = Field(None, gt=0, le=365, description="Expiration in days (optional)")
    permissions: Optional[List[str]] = Field(default=None, description="Optional permissions list")


class APIKeyResponse(BaseModel):
    """Response model for API key (without full key)."""
    id: str
    tenant_id: str
    name: str
    key_prefix: str
    permissions: List[str]
    last_used_at: Optional[str]
    usage_count: int
    is_active: bool
    expires_at: Optional[str]
    created_at: str
    updated_at: Optional[str]


class CreateAPIKeyResponse(BaseModel):
    """Response model for newly created API key (includes full key)."""
    id: str
    api_key: str
    key_prefix: str
    name: str
    tenant_id: str
    permissions: List[str]
    expires_at: Optional[str]
    created_at: str
    message: str


class RotateAPIKeyRequest(BaseModel):
    """Request model for rotating an API key."""
    new_key_name: Optional[str] = Field(None, max_length=255, description="Optional name for new key")


@router.post("/", response_model=CreateAPIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API key for the current tenant.
    
    **Important:** The full API key is only shown once in this response.
    Save it securely - you won't be able to retrieve it again.
    
    - **name**: Friendly name to identify this key
    - **expires_in_days**: Optional expiration (e.g., 30, 60, 90 days)
    - **permissions**: Optional permissions list (inherits tenant permissions if not specified)
    """
    try:
        tenant_id = current_user["tenant_id"]
        result = APIKeyService.create_api_key(
            db=db,
            tenant_id=tenant_id,
            name=request.name,
            expires_in_days=request.expires_in_days,
            permissions=request.permissions
        )
        
        # Log audit event
        AuditService.log_event(
            db=db,
            tenant_id=tenant_id,
            action="api_key.created",
            resource_type="api_key",
            resource_id=result["id"],
            details={
                "key_name": request.name,
                "key_prefix": result["key_prefix"],
                "expires_at": result["expires_at"]
            }
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )


@router.get("/", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all API keys for the current tenant.
    
    Returns key metadata without the actual key values.
    Shows key prefix for identification (e.g., "sk_live_abc...xyz").
    """
    try:
        tenant_id = current_user["tenant_id"]
        keys = APIKeyService.list_api_keys(db=db, tenant_id=tenant_id)
        return keys
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list API keys: {str(e)}"
        )


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revoke (deactivate) an API key.
    
    The key will be immediately deactivated and can no longer be used for authentication.
    This action cannot be undone.
    
    - **key_id**: ID of the API key to revoke
    """
    try:
        tenant_id = current_user["tenant_id"]
        success = APIKeyService.revoke_api_key(
            db=db,
            tenant_id=tenant_id,
            key_id=key_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key not found"
            )
        
        # Log audit event
        AuditService.log_event(
            db=db,
            tenant_id=tenant_id,
            action="api_key.revoked",
            resource_type="api_key",
            resource_id=key_id,
            details={"revoked": True}
        )
        
        return {"message": f"API key {key_id} revoked successfully", "key_id": key_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke API key: {str(e)}"
        )


@router.post("/{key_id}/rotate", response_model=CreateAPIKeyResponse)
async def rotate_api_key(
    key_id: str,
    request: RotateAPIKeyRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rotate an API key (create new key and revoke old one).
    
    This creates a new API key with the same settings as the old one,
    then immediately revokes the old key.
    
    **Important:** The new API key is only shown once in this response.
    
    - **key_id**: ID of the API key to rotate
    - **new_key_name**: Optional name for the new key
    """
    try:
        tenant_id = current_user["tenant_id"]
        result = APIKeyService.rotate_api_key(
            db=db,
            tenant_id=tenant_id,
            old_key_id=key_id,
            new_key_name=request.new_key_name
        )
        
        # Log audit event
        AuditService.log_event(
            db=db,
            tenant_id=tenant_id,
            action="api_key.rotated",
            resource_type="api_key",
            resource_id=result["id"],
            details={
                "old_key_id": key_id,
                "new_key_id": result["id"],
                "new_key_prefix": result["key_prefix"]
            }
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rotate API key: {str(e)}"
        )
