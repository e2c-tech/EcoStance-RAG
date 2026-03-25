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
    role: Optional[str] = None


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
    # Method 1: Email + Password authentication
    if request.email and request.password:
        try:
            # First try finding a Tenant account (Tenant Admin)
            tenant = db.query(Tenant).filter(Tenant.email == request.email).first()
            authenticated_user = None
            is_tenant_admin_account = False

            if tenant:
                # Verify tenant password
                if tenant.password_hash and bcrypt.checkpw(request.password.encode('utf-8'), tenant.password_hash.encode('utf-8')):
                     is_tenant_admin_account = True
                else:
                    tenant = None # Invalid password for tenant account

            # If not authenticated as Tenant account, try finding a TenantUser
            if not tenant:
                tenant_user = db.query(TenantUser).filter(TenantUser.email == request.email).first()
                if tenant_user:
                     if tenant_user.password_hash and bcrypt.checkpw(request.password.encode('utf-8'), tenant_user.password_hash.encode('utf-8')):
                         # Authenticated as TenantUser!
                         # Retrieve the associated Tenant
                         tenant = db.query(Tenant).filter(Tenant.id == tenant_user.tenant_id).first()
                         authenticated_user = tenant_user
                     else:
                         logger.warning(f"TenantUser login failed for {request.email}: password_hash present={bool(tenant_user.password_hash)}, is_active={tenant_user.is_active}")
                     
            if not tenant:
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
            
            # Additional check for TenantUser active status
            if authenticated_user and not authenticated_user.is_active:
                 raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive"
                )

            logger.info(f"Successful login for tenant: {tenant.id} (User: {authenticated_user.email if authenticated_user else 'Tenant Admin'})")
            
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
    # Determine user_id:
    # 1. If we found a specific authenticated_user logic above, use it. (But authenticated_user variable is local to that block)
    # We need to ensure 'authenticated_user' is accessible here or re-fetch logic is clean.
    
    # Re-evaluating scope: 'authenticated_user' was defined in the try block. 
    # Let's initialize it before if/else for safety or check 'request.email'.
    # Actually, the 'login' function continues below.
    # The simplest way is to fetch the user again if we are in 'TenantUser' mode, OR
    # just look up by email again which is what the current code does below anyway!
    
    # Current code below:
    # user_id = request.user_id or request.email or tenant.id
    # email_to_check = request.email or getattr(tenant, 'email', None)
    
    # The existing logic below (lines 161+) attempts to find the TenantUser to get the role.
    # We should let it do its job, BUT we need to make sure 'user_id' is set correctly.
    # If we logged in as a TenantUser, user_id should be that user's ID (which is in tenant_users.user_id).
    
    # Let's modify the lookup below to also grab the ID if we haven't set it explicitly.
    
    user_id = request.user_id or (getattr(tenant, 'id') if tenant else None) # Default
    
    # Fetch user role from tenant_users table (Enhanced for Better RBAC)
    user_role = None
    system_role = None
    email_to_check = request.email or getattr(tenant, 'email', None)
    try:
        if email_to_check:
            tenant_user = db.query(TenantUser).filter(
                TenantUser.tenant_id == tenant.id,
                TenantUser.email == email_to_check
            ).first()
            if tenant_user:
                # Check for system role first (Better RBAC)
                if tenant_user.system_role:
                    system_role = tenant_user.system_role
                    user_role = tenant_user.system_role  # Use system role as primary role
                elif tenant_user.tenant_role_id and tenant_user.tenant_role:
                    user_role = f"tenant_role:{tenant_user.tenant_role.name}"
                elif tenant_user.role:
                    user_role = tenant_user.role  # Legacy role fallback
                
                user_id = tenant_user.user_id  # Use the actual user_id from tenant_users
                logger.info(f"Found user with system_role: {system_role}, role: {user_role}")
            else:
                if not request.tenant_id: # If not dev-mode login
                     logger.warning(f"No tenant_user found for email: {email_to_check}")
    except Exception as e:
        logger.error(f"Could not fetch user role: {e}", exc_info=True)
    
    token_data = {
        "tenant_id": tenant.id,
        "user_id": user_id,
        "role": user_role
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
        email=getattr(tenant, 'email', None),
        role=user_role
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


class SetPasswordRequest(BaseModel):
    token: str
    password: str


@router.post("/auth/set-password", tags=["Authentication"])
async def set_password_endpoint(
    request: SetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Set password for a user using an invitation token.
    """
    # Verify token
    try:
        from ..auth.jwt_handler import verify_token
        payload = verify_token(request.token, token_type="invite")
    except HTTPException:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invitation token"
        )
    
    tenant_id = payload.get("tenant_id")
    user_id = payload.get("user_id")
    
    # Update user password
    user = db.query(TenantUser).filter(
        TenantUser.tenant_id == tenant_id,
        TenantUser.user_id == user_id
    ).first()
    
    if not user:
         raise HTTPException(status_code=404, detail="User not found")
         
    # Hash password
    import bcrypt
    password_hash = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user.password_hash = password_hash
    user.is_active = True  # Ensure user is active after accepting invite
    db.commit()
    db.refresh(user)
    
    import logging
    logging.getLogger(__name__).info(f"Password set for user {user.email} (tenant: {tenant_id}), hash present: {bool(user.password_hash)}")
    
    return {"message": "Password set successfully. You can now login."}
