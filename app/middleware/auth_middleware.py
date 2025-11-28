"""
Authentication middleware for tenant validation and request logging.
"""
import time
import logging
from typing import Callable, Optional
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError

from ..auth.jwt_handler import verify_token
from ..services.api_key_service import APIKeyService
from ..db.database import SessionLocal

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate tenant_id on every request and add logging.
    
    Excludes certain paths from authentication:
    - /docs, /redoc, /openapi.json (API documentation)
    - /health (health check)
    - / (root)
    """
    
    EXCLUDED_PATHS = [
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health"
    ]
    
    def _validate_api_key(self, api_key: str) -> Optional[dict]:
        """
        Validate an API key and return tenant info.
        
        Args:
            api_key: API key to validate
            
        Returns:
            Dictionary with tenant_id and other info, or None if invalid
        """
        db = SessionLocal()
        try:
            return APIKeyService.validate_api_key(db, api_key)
        finally:
            db.close()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process each request, validate tenant, and log with tenant context.
        
        Supports two authentication methods:
        1. JWT Bearer token (Authorization: Bearer <token>)
        2. API Key (Authorization: Bearer <api_key> or X-API-Key: <api_key>)
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint handler
            
        Returns:
            Response from the endpoint
        """
        start_time = time.time()
        
        # Skip authentication for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            response = await call_next(request)
            return response
        
        # Extract tenant_id from token, API key, or header
        tenant_id = None
        auth_method = None
        auth_header = request.headers.get("Authorization")
        x_api_key = request.headers.get("X-API-Key")
        x_tenant_id = request.headers.get("X-Tenant-ID")
        
        # Try JWT token first
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
            # Check if it's a JWT token (contains dots) or API key (starts with sk_)
            if token.startswith("sk_"):
                # It's an API key
                api_key_info = self._validate_api_key(token)
                if api_key_info:
                    tenant_id = api_key_info["tenant_id"]
                    auth_method = "api_key"
                    request.state.api_key_id = api_key_info["api_key_id"]
                    request.state.api_key_name = api_key_info["key_name"]
                else:
                    logger.warning("Invalid API key provided")
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Invalid API key"},
                        headers={"WWW-Authenticate": "Bearer"}
                    )
            else:
                # It's a JWT token
                try:
                    payload = verify_token(token)
                    tenant_id = payload.get("tenant_id")
                    auth_method = "jwt"
                except JWTError as e:
                    logger.warning(f"Invalid JWT token: {str(e)}")
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Invalid authentication token"},
                        headers={"WWW-Authenticate": "Bearer"}
                    )
                except Exception as e:
                    logger.error(f"Token verification error: {str(e)}")
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Authentication error"},
                        headers={"WWW-Authenticate": "Bearer"}
                    )
        
        # Try X-API-Key header
        elif x_api_key:
            api_key_info = self._validate_api_key(x_api_key)
            if api_key_info:
                tenant_id = api_key_info["tenant_id"]
                auth_method = "api_key"
                request.state.api_key_id = api_key_info["api_key_id"]
                request.state.api_key_name = api_key_info["key_name"]
            else:
                logger.warning("Invalid API key in X-API-Key header")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid API key"}
                )
        
        # Fallback to X-Tenant-ID header (for backward compatibility)
        elif x_tenant_id:
            tenant_id = x_tenant_id
            auth_method = "header"
        
        # Log request with tenant context
        logger.info(
            f"Request: {request.method} {request.url.path} | "
            f"Tenant: {tenant_id or 'None'} | "
            f"Auth: {auth_method or 'None'} | "
            f"Client: {request.client.host if request.client else 'Unknown'}"
        )
        
        # Add tenant_id and auth method to request state for easy access in endpoints
        request.state.tenant_id = tenant_id
        request.state.auth_method = auth_method
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(
                f"Request failed: {request.method} {request.url.path} | "
                f"Tenant: {tenant_id or 'None'} | "
                f"Error: {str(e)}"
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"}
            )
        
        # Log response with timing
        process_time = time.time() - start_time
        logger.info(
            f"Response: {request.method} {request.url.path} | "
            f"Status: {response.status_code} | "
            f"Tenant: {tenant_id or 'None'} | "
            f"Time: {process_time:.3f}s"
        )
        
        # Add custom headers
        response.headers["X-Process-Time"] = str(process_time)
        if tenant_id:
            response.headers["X-Tenant-ID"] = tenant_id
        
        return response
