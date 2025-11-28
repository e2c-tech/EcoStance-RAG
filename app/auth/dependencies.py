"""
FastAPI dependencies for tenant context extraction and validation.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .jwt_handler import verify_token
from ..models.tenant import Tenant
from ..db.database import get_db

security = HTTPBearer()


async def get_tenant_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_tenant_id: Optional[str] = Header(None)
) -> str:
    """
    Extract tenant_id from JWT token or X-Tenant-ID header.
    
    Priority:
    1. JWT token tenant_id claim
    2. X-Tenant-ID header (fallback)
    
    Args:
        request: FastAPI request object
        credentials: Bearer token from Authorization header
        x_tenant_id: Optional tenant ID from X-Tenant-ID header
        
    Returns:
        Tenant ID string
        
    Raises:
        HTTPException: If tenant_id cannot be extracted
    """
    # Try to get tenant_id from JWT token first
    if credentials:
        try:
            payload = verify_token(credentials.credentials)
            tenant_id = payload.get("tenant_id")
            if tenant_id:
                return tenant_id
        except HTTPException:
            # If token is invalid, try fallback
            pass
    
    # Fallback to X-Tenant-ID header
    if x_tenant_id:
        return x_tenant_id
    
    # No tenant_id found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tenant ID not found. Provide valid JWT token or X-Tenant-ID header",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_tenant_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Tenant:
    """
    Extract and validate tenant from JWT token.
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        Tenant object
        
    Raises:
        HTTPException: If token is invalid or tenant not found/inactive
    """
    payload = verify_token(credentials.credentials)
    tenant_id = payload.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant ID not found in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Query tenant from database
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is inactive"
        )
    
    return tenant


async def get_current_tenant(
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
) -> Tenant:
    """
    Get current tenant from tenant_id (supports both JWT and header).
    
    Args:
        tenant_id: Tenant ID from get_tenant_id dependency
        db: Database session
        
    Returns:
        Tenant object
        
    Raises:
        HTTPException: If tenant not found or inactive
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is inactive"
        )
    
    return tenant


def get_optional_tenant_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_tenant_id: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Extract tenant_id but don't raise exception if not found.
    Useful for endpoints that support both authenticated and unauthenticated access.
    
    Args:
        request: FastAPI request object
        credentials: Bearer token from Authorization header
        x_tenant_id: Optional tenant ID from X-Tenant-ID header
        
    Returns:
        Tenant ID string or None
    """
    try:
        if credentials:
            payload = verify_token(credentials.credentials)
            tenant_id = payload.get("tenant_id")
            if tenant_id:
                return tenant_id
    except HTTPException:
        pass
    
    if x_tenant_id:
        return x_tenant_id
    
    return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_tenant_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get current authenticated user information.
    Returns a dictionary with tenant_id and user_id.
    
    This is a compatibility function for endpoints that expect user context.
    
    Args:
        request: FastAPI request object
        credentials: Bearer token from Authorization header
        x_tenant_id: Optional tenant ID from X-Tenant-ID header
        db: Database session
        
    Returns:
        Dictionary with tenant_id and user_id
        
    Raises:
        HTTPException: If authentication fails
    """
    # Try to get tenant_id from JWT token first
    tenant_id = None
    user_id = None
    
    if credentials:
        try:
            payload = verify_token(credentials.credentials)
            tenant_id = payload.get("tenant_id")
            user_id = payload.get("user_id", "system")  # Default to "system" if not provided
        except HTTPException:
            pass
    
    # Fallback to X-Tenant-ID header
    if not tenant_id and x_tenant_id:
        tenant_id = x_tenant_id
        user_id = "system"  # Default user for header-based auth
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide valid JWT token or X-Tenant-ID header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify tenant exists and is active
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is inactive or suspended"
        )
    
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "tenant": tenant
    }



async def require_admin(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> str:
    """
    Require admin authentication.
    
    For now, this is a placeholder that validates the tenant exists.
    In production, you should implement proper admin role checking.
    
    Args:
        request: FastAPI request object
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        Tenant ID string (admin tenant)
        
    Raises:
        HTTPException: If authentication fails or user is not admin
    """
    # Get tenant_id from token
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = verify_token(credentials.credentials)
        tenant_id = payload.get("tenant_id")
        
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify tenant exists and is active
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        if not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant account is inactive"
            )
        
        # TODO: Add proper admin role checking here
        # For now, we'll allow any authenticated tenant to access admin endpoints
        # In production, check if tenant has admin role:
        # if tenant.role != "admin":
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Admin access required"
        #     )
        
        return tenant_id
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
            headers={"WWW-Authenticate": "Bearer"},
        )
