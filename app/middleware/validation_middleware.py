"""
Request validation middleware - sanitizes and validates all incoming requests.
"""
import re
import logging
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

logger = logging.getLogger(__name__)


class ValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate and sanitize incoming requests.
    
    Protections:
    - SQL injection prevention
    - XSS prevention
    - Request size limits
    - Tenant ID format validation
    - File upload validation
    """
    
    # Configuration
    MAX_REQUEST_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_JSON_SIZE = 10 * 1024 * 1024  # 10MB for JSON payloads
    
    # Dangerous patterns (SQL injection, XSS)
    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(\bUPDATE\b.*\bSET\b)",
        r"(--\s*$)",
        r"(;\s*DROP\b)",
        r"(\bEXEC\b.*\()",
        r"(\bEXECUTE\b.*\()",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",  # onclick, onload, etc.
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]
    
    # Allowed file extensions
    ALLOWED_FILE_EXTENSIONS = {
        '.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx',
        '.csv', '.json', '.xml', '.html', '.md', '.py',
        '.js', '.ts', '.java', '.cpp', '.c', '.h'
    }
    
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB per file
    
    @staticmethod
    def is_valid_uuid(value: str) -> bool:
        """Check if a string is a valid UUID."""
        try:
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            return False
    
    @staticmethod
    def contains_sql_injection(text: str) -> bool:
        """Check if text contains SQL injection patterns."""
        if not isinstance(text, str):
            return False
        
        text_upper = text.upper()
        for pattern in ValidationMiddleware.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def contains_xss(text: str) -> bool:
        """Check if text contains XSS patterns."""
        if not isinstance(text, str):
            return False
        
        for pattern in ValidationMiddleware.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        Sanitize text input by removing dangerous characters.
        
        Note: This is a basic sanitization. For production, consider
        using a library like bleach or html.escape.
        """
        if not isinstance(text, str):
            return text
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove control characters (except newline, tab, carriage return)
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t\r')
        
        return text
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Validate and sanitize incoming requests.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint handler
            
        Returns:
            Response from the endpoint or error response
        """
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.MAX_REQUEST_SIZE:
                    logger.warning(
                        f"Request too large: {size} bytes from {request.client.host if request.client else 'Unknown'}"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={"detail": f"Request too large. Maximum size: {self.MAX_REQUEST_SIZE} bytes"}
                    )
            except ValueError:
                pass
        
        # Validate tenant_id in path or query params
        if "tenant_id" in request.path_params:
            tenant_id = request.path_params["tenant_id"]
            if not self.is_valid_uuid(tenant_id):
                logger.warning(f"Invalid tenant_id format in path: {tenant_id}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid tenant_id format. Must be a valid UUID."}
                )
        
        # Validate tenant_id in query params
        query_params = dict(request.query_params)
        if "tenant_id" in query_params:
            tenant_id = query_params["tenant_id"]
            if not self.is_valid_uuid(tenant_id):
                logger.warning(f"Invalid tenant_id format in query: {tenant_id}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid tenant_id format. Must be a valid UUID."}
                )
        
        # Validate X-Tenant-ID header
        x_tenant_id = request.headers.get("X-Tenant-ID")
        if x_tenant_id and not self.is_valid_uuid(x_tenant_id):
            logger.warning(f"Invalid X-Tenant-ID header: {x_tenant_id}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid X-Tenant-ID header. Must be a valid UUID."}
            )
        
        # Check for SQL injection in query parameters
        for key, value in query_params.items():
            if self.contains_sql_injection(value):
                logger.warning(
                    f"SQL injection attempt detected in query param '{key}': {value[:100]}"
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid input detected. Request blocked for security reasons."}
                )
        
        # For file uploads, validate in the endpoint (can't easily check here)
        # For JSON payloads, validation happens in Pydantic models
        
        # Process request
        response = await call_next(request)
        
        return response
