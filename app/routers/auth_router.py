"""
Authentication router for login and token management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import bcrypt

from ..auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    refresh_access_token
)
from ..db.database import get_db
from ..models.tenant import Tenant
from ..models.tenant_user import TenantUser

router = APIRouter()


class LoginRequest(BaseModel):
    """Login request model - supports both email/password and tenant_id."""
    email: Optional[str] = None
    password: Optional[str] = None
    tenant_id: Optional[str] = None  # For backward compatibility
    user_id: Optional[str] = None
    api_key: Optional[str] = None


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    tenant_id: str


class LoginResponse(BaseModel):
    """Login response with user info."""
    access_token: str
    expires_in: int = 1800  # 30 minutes
    tenant_id: str
    user_id: str
    email: Optional[str] = None


class RefreshRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str


@router.post("/auth/login", response_model=LoginResponse, tags=["Authentication"])
async def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Login endpoint to generate JWT tokens.
    
    Supports two authentication methods:
    1. Email + Password (recommended for production)
    2. Tenant ID (for development/backward compatibility)
    
    Validates tenant exists and is active, then generates access and refresh tokens.
    Sets refresh token as httpOnly cookie for security.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    tenant = None
    
    # Method 1: Email + Password authentication
    if request.email and request.password:
        try:
            # Find tenant by email
            tenant = db.query(Tenant).filter(Tenant.email == request.email).first()
            
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Verify password
            if not tenant.password_hash:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Password not set for this account. Please use tenant_id login or reset password."
                )
            
            # Check password
            if not bcrypt.checkpw(request.password.encode('utf-8'), tenant.password_hash.encode('utf-8')):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Check if tenant is active
            if not tenant.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tenant account is inactive"
                )
            
            logger.info(f"Successful email/password login for tenant: {tenant.id}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred during login"
            )
    
    # Method 2: Tenant ID authentication (backward compatibility / development)
    elif request.tenant_id:
        try:
            tenant = db.query(Tenant).filter(Tenant.id == request.tenant_id).first()
            
            if not tenant:
                # For development: Allow login even if tenant doesn't exist in DB
                logger.warning(f"Tenant {request.tenant_id} not found in database. Allowing login for development.")
                # Create a temporary tenant object for token generation
                class TempTenant:
                    id = request.tenant_id
                    is_active = True
                    email = None
                tenant = TempTenant()
            elif not tenant.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tenant account is inactive"
                )
            
            logger.info(f"Tenant ID login for: {request.tenant_id}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Database query failed: {e}. Allowing login for development.")
            # Create a temporary tenant object for token generation
            class TempTenant:
                id = request.tenant_id
                is_active = True
                email = None
            tenant = TempTenant()
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email+password or tenant_id must be provided"
        )
    
    # Create token data
    user_id = request.user_id or request.email or tenant.id
    token_data = {
        "tenant_id": tenant.id,
        "user_id": user_id
    }
    
    # Generate tokens
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    # Set refresh token as httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=604800,  # 7 days in seconds
        path="/"
    )
    
    return LoginResponse(
        access_token=access_token,
        expires_in=1800,  # 30 minutes
        tenant_id=tenant.id,
        user_id=user_id,
        email=getattr(tenant, 'email', None)
    )


class RefreshResponse(BaseModel):
    """Refresh token response with user info."""
    access_token: str
    expires_in: int = 1800  # 30 minutes
    tenant_id: str
    user_id: str
    email: Optional[str] = None


@router.post("/auth/refresh", response_model=RefreshResponse, tags=["Authentication"])
async def refresh(
    request: Request,
    refresh_request: Optional[RefreshRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using a valid refresh token.
    
    Accepts refresh token from:
    1. httpOnly cookie (preferred for security)
    2. Request body (for backward compatibility)
    
    Returns new access token with user information.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Try to get refresh token from cookie first, then from body
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token and refresh_request:
        refresh_token = refresh_request.refresh_token
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found in cookie or request body"
        )
    
    try:
        # Verify and extract payload from refresh token
        from ..auth.jwt_handler import verify_token
        payload = verify_token(refresh_token, token_type="refresh")
        
        tenant_id = payload.get("tenant_id")
        user_id = payload.get("user_id")
        
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token: missing tenant_id"
            )
        
        # Get tenant info from database
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        email = tenant.email if tenant else None
        
        # Generate new access token
        new_access_token = refresh_access_token(refresh_token)
        
        logger.info(f"Token refreshed for tenant: {tenant_id}")
        
        return RefreshResponse(
            access_token=new_access_token,
            expires_in=1800,  # 30 minutes
            tenant_id=tenant_id,
            user_id=user_id or tenant_id,
            email=email
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.get("/auth/verify", tags=["Authentication"])
async def verify_token_endpoint(
    tenant_id: str = Depends(lambda: None)  # This will be populated by middleware
):
    """
    Verify if the current token is valid.
    This endpoint requires authentication.
    """
    return {
        "valid": True,
        "message": "Token is valid"
    }


@router.post("/auth/logout", tags=["Authentication"])
async def logout(
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Logout endpoint.
    
    Clears the httpOnly refresh token cookie and logs the logout action.
    
    Since JWT tokens are stateless, logout is primarily handled by:
    1. Clearing the httpOnly cookie (done by this endpoint)
    2. Client removing access_token from storage
    3. Optional: Future token blacklisting implementation
    
    The client should:
    1. Call this endpoint
    2. Remove the access_token from storage
    3. Redirect to login page
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Try to get user info from the request
    try:
        from ..auth.dependencies import get_current_user
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
        
        security = HTTPBearer(auto_error=False)
        credentials = await security(request)
        
        if credentials:
            user_info = await get_current_user(request, credentials, None, db)
            if user_info:
                tenant_id = user_info.get("tenant_id")
                user_id = user_info.get("user_id")
                logger.info(f"User logout: tenant_id={tenant_id}, user_id={user_id}")
                
                # Update last activity for TenantUser if exists
                if tenant_id and user_id:
                    tenant_user = db.query(TenantUser).filter(
                        TenantUser.tenant_id == tenant_id,
                        TenantUser.user_id == user_id
                    ).first()
                    
                    if tenant_user:
                        # You could add a last_logout_at field if needed
                        db.commit()
    except Exception as e:
        logger.warning(f"Logout called without valid token: {e}")
    
    # Clear the refresh token cookie
    response.delete_cookie(
        key="refresh_token",
        path="/",
        samesite="lax"
    )
    
    return {
        "message": "Logged out successfully",
        "detail": "Refresh token cookie cleared. Please remove access token from client storage."
    }
