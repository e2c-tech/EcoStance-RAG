"""
Usage tracking middleware - automatically logs all API requests.
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..services.usage_tracking_service import UsageTrackingService
from ..db.database import SessionLocal

logger = logging.getLogger(__name__)


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically track all API requests.
    
    Logs:
    - Request details (endpoint, method, tenant)
    - Response details (status code, response time)
    - Authentication method
    - Errors (if any)
    """
    
    # Paths to exclude from tracking
    EXCLUDED_PATHS = [
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico"
    ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Track request and response details.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint handler
            
        Returns:
            Response from the endpoint
        """
        # Skip tracking for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        start_time = time.time()
        
        # Extract request details
        tenant_id = getattr(request.state, "tenant_id", None)
        auth_method = getattr(request.state, "auth_method", None)
        api_key_id = getattr(request.state, "api_key_id", None)
        
        endpoint = request.url.path
        method = request.method
        user_agent = request.headers.get("user-agent")
        ip_address = request.client.host if request.client else None
        
        # Get request size
        request_size = None
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                request_size = int(content_length)
            except ValueError:
                pass
        
        # Process request
        error_type = None
        error_message = None
        response = None
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Capture error details for 4xx and 5xx responses
            if status_code >= 400:
                error_type = f"HTTP_{status_code}"
                # Error message would be in response body, but we can't easily access it here
                
        except Exception as e:
            status_code = 500
            error_type = type(e).__name__
            error_message = str(e)
            logger.error(f"Request failed: {endpoint} - {error_message}")
            raise
        
        finally:
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Get response size (if available)
            response_size = None
            if response and hasattr(response, "headers"):
                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        response_size = int(content_length)
                    except ValueError:
                        pass
            
            # Log to database (async, don't block response)
            try:
                db = SessionLocal()
                try:
                    UsageTrackingService.log_request(
                        db=db,
                        tenant_id=tenant_id,
                        endpoint=endpoint,
                        method=method,
                        status_code=status_code,
                        response_time_ms=response_time_ms,
                        auth_method=auth_method,
                        api_key_id=api_key_id,
                        error_type=error_type,
                        error_message=error_message,
                        user_agent=user_agent,
                        ip_address=ip_address,
                        request_size=request_size,
                        response_size=response_size
                    )
                finally:
                    db.close()
            except Exception as e:
                # Don't fail the request if logging fails
                logger.error(f"Failed to log usage: {str(e)}")
        
        return response
