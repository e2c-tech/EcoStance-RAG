"""
Rate limiting middleware for API endpoints.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import time


class RateLimitConfig:
    """Configuration for rate limiting."""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day


class RateLimiter:
    """In-memory rate limiter with sliding window."""
    
    def __init__(self):
        # Store: {tenant_id: [(timestamp, count)]}
        self.request_history: Dict[str, list] = defaultdict(list)
        self.cleanup_interval = 3600  # Clean up old entries every hour
        self.last_cleanup = time.time()
    
    def check_rate_limit(
        self,
        tenant_id: str,
        config: RateLimitConfig
    ) -> tuple[bool, Optional[str]]:
        """
        Check if request is within rate limits.
        
        Args:
            tenant_id: The tenant ID
            config: Rate limit configuration
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        now = datetime.utcnow()
        
        # Clean up old entries periodically
        if time.time() - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries()
        
        # Get request history for tenant
        history = self.request_history[tenant_id]
        
        # Remove entries older than 24 hours
        cutoff_day = now - timedelta(days=1)
        history = [entry for entry in history if entry > cutoff_day]
        self.request_history[tenant_id] = history
        
        # Check daily limit
        if len(history) >= config.requests_per_day:
            return False, "Daily rate limit exceeded"
        
        # Check hourly limit
        cutoff_hour = now - timedelta(hours=1)
        recent_hour = [entry for entry in history if entry > cutoff_hour]
        if len(recent_hour) >= config.requests_per_hour:
            return False, "Hourly rate limit exceeded"
        
        # Check minute limit
        cutoff_minute = now - timedelta(minutes=1)
        recent_minute = [entry for entry in history if entry > cutoff_minute]
        if len(recent_minute) >= config.requests_per_minute:
            return False, "Rate limit exceeded. Please try again later."
        
        # Add current request
        history.append(now)
        
        return True, None
    
    def _cleanup_old_entries(self):
        """Remove entries older than 24 hours from all tenants."""
        cutoff = datetime.utcnow() - timedelta(days=1)
        for tenant_id in list(self.request_history.keys()):
            history = self.request_history[tenant_id]
            self.request_history[tenant_id] = [
                entry for entry in history if entry > cutoff
            ]
            # Remove tenant if no recent requests
            if not self.request_history[tenant_id]:
                del self.request_history[tenant_id]
        
        self.last_cleanup = time.time()
    
    def get_usage_stats(self, tenant_id: str) -> Dict[str, int]:
        """
        Get current usage statistics for a tenant.
        
        Args:
            tenant_id: The tenant ID
            
        Returns:
            Dictionary with usage counts
        """
        now = datetime.utcnow()
        history = self.request_history.get(tenant_id, [])
        
        cutoff_minute = now - timedelta(minutes=1)
        cutoff_hour = now - timedelta(hours=1)
        cutoff_day = now - timedelta(days=1)
        
        return {
            "requests_last_minute": len([e for e in history if e > cutoff_minute]),
            "requests_last_hour": len([e for e in history if e > cutoff_hour]),
            "requests_last_day": len([e for e in history if e > cutoff_day]),
        }


# Global rate limiter instance
rate_limiter = RateLimiter()

# Default rate limit configurations by tier
RATE_LIMIT_CONFIGS = {
    "free": RateLimitConfig(
        requests_per_minute=10,
        requests_per_hour=100,
        requests_per_day=1000
    ),
    "basic": RateLimitConfig(
        requests_per_minute=30,
        requests_per_hour=500,
        requests_per_day=5000
    ),
    "premium": RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        requests_per_day=10000
    ),
    "enterprise": RateLimitConfig(
        requests_per_minute=120,
        requests_per_hour=5000,
        requests_per_day=50000
    ),
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits per tenant."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get tenant ID from request state (set by auth middleware)
        tenant_id = getattr(request.state, "tenant_id", None)
        
        if tenant_id:
            # Get tenant's rate limit config (default to basic)
            # In production, this should be fetched from tenant settings
            config = RATE_LIMIT_CONFIGS.get("basic")
            
            # Check rate limit
            is_allowed, error_message = rate_limiter.check_rate_limit(
                tenant_id, config
            )
            
            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=error_message,
                    headers={"Retry-After": "60"}
                )
        
        response = await call_next(request)
        return response
