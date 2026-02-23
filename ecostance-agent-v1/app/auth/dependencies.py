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
    Extract and validate tenant_id. 
    If JWT is present, it is the single source of truth.
    """
    jwt_tenant_id = None
    if credentials:
        try:
            payload = verify_token(credentials.credentials)
            jwt_tenant_id = payload.get("tenant_id")
        except HTTPException:
            pass
    
    # If both present, they must match
    if jwt_tenant_id and x_tenant_id and jwt_tenant_id != x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant ID mismatch between JWT and header"
        )
    
    tenant_id = jwt_tenant_id or x_tenant_id
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant ID not found. Provide valid JWT token or X-Tenant-ID header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return tenant_id


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
    Get current authenticated user and enforce tenant membership.
    """
    payload = None
    if credentials:
        try:
            payload = verify_token(credentials.credentials)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 1. Determine target tenant
    jwt_tenant_id = payload.get("tenant_id") if payload else None
    
    if jwt_tenant_id and x_tenant_id and jwt_tenant_id != x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security violation: Header tenant_id does not match JWT tenant_id"
        )
        
    target_tenant_id = jwt_tenant_id or x_tenant_id
    user_id = payload.get("user_id") if payload else "system"
    
    if not target_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant Identification required"
        )

    # 2. Verify Tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == target_tenant_id).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is inactive or does not exist"
        )

    # 3. Verify User-Tenant relationship
    from ..models.tenant_user import TenantUser
    tenant_user = db.query(TenantUser).filter(
        TenantUser.tenant_id == target_tenant_id,
        TenantUser.user_id == user_id
    ).first()

    if not tenant_user and user_id != "system":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this tenant"
        )

    return {
        "tenant_id": target_tenant_id,
        "user_id": user_id,
        "tenant_user_id": tenant_user.id if tenant_user else None,
        "tenant": tenant,
        "user": tenant_user,
        "system_role": tenant_user.system_role if tenant_user else None
    }



async def require_admin(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> str:
    """
    Require administrative privileges (Super Admin or Tenant Admin).
    Returns the tenant_id of the administrator.
    """
    user_context = await get_current_user(request, credentials, None, db)
    system_role = user_context.get("system_role")
    from .permissions import SystemRole
    
    if system_role not in [SystemRole.SUPER_ADMIN, SystemRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative access required"
        )
        
    return user_context["tenant_id"]


async def require_super_admin(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> str:
    """
    Require Super Admin privileges (System-wide administrator).
    """
    user_context = await get_current_user(request, credentials, None, db)
    system_role = user_context.get("system_role")
    from .permissions import SystemRole
    
    if system_role != SystemRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin access required for this system-level operation"
        )
        
    return user_context["tenant_id"]
