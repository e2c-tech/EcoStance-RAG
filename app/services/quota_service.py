"""
Quota Service - Manages tenant resource quotas and usage tracking.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


class QuotaExceededException(Exception):
    """Exception raised when a tenant exceeds their quota."""
    def __init__(self, message: str, quota_type: str, current: int, limit: int):
        self.message = message
        self.quota_type = quota_type
        self.current = current
        self.limit = limit
        super().__init__(self.message)


class QuotaService:
    """Service for managing tenant quotas and usage tracking."""
    
    # Default quota values by tier
    TIER_QUOTAS = {
        "free": {
            "max_queries_per_day": 100,
            "max_queries_per_month": 3000,
            "max_documents": 1000,
            "max_storage_bytes": 1073741824,  # 1GB
            "max_db_connections": 2,
            "max_concurrent_queries": 3,
            "max_api_calls_per_minute": 10,
            "max_api_calls_per_hour": 600,
        },
        "starter": {
            "max_queries_per_day": 1000,
            "max_queries_per_month": 30000,
            "max_documents": 10000,
            "max_storage_bytes": 10737418240,  # 10GB
            "max_db_connections": 5,
            "max_concurrent_queries": 10,
            "max_api_calls_per_minute": 60,
            "max_api_calls_per_hour": 3600,
        },
        "professional": {
            "max_queries_per_day": 10000,
            "max_queries_per_month": 300000,
            "max_documents": 100000,
            "max_storage_bytes": 107374182400,  # 100GB
            "max_db_connections": 20,
            "max_concurrent_queries": 50,
            "max_api_calls_per_minute": 300,
            "max_api_calls_per_hour": 18000,
        },
        "enterprise": {
            "max_queries_per_day": -1,  # Unlimited
            "max_queries_per_month": -1,
            "max_documents": -1,
            "max_storage_bytes": -1,
            "max_db_connections": 100,
            "max_concurrent_queries": 200,
            "max_api_calls_per_minute": 1000,
            "max_api_calls_per_hour": 60000,
        }
    }
    
    def __init__(self, db: Session):
        """Initialize quota service with database session."""
        self.db = db
    
    def get_tenant_quotas(self, tenant_id: str) -> Dict[str, int]:
        """
        Get quota limits for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dictionary of quota limits
        """
        # Get tenant to determine tier
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Check if custom quotas exist in database
        result = self.db.execute(
            text("SELECT * FROM tenant_quotas WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        ).fetchone()
        
        if result:
            return {
                "max_queries_per_day": result[2],
                "max_queries_per_month": result[3],
                "max_documents": result[4],
                "max_storage_bytes": result[5],
                "max_db_connections": result[6],
                "max_concurrent_queries": result[7],
                "max_api_calls_per_minute": result[8],
                "max_api_calls_per_hour": result[9],
            }
        
        # Return default quotas based on tier
        tier = tenant.billing_tier or "free"
        return self.TIER_QUOTAS.get(tier, self.TIER_QUOTAS["free"])
    
    def get_current_usage(self, tenant_id: str, period_type: str = "daily") -> Dict[str, int]:
        """
        Get current usage for a tenant in the specified period.
        
        Args:
            tenant_id: Tenant identifier
            period_type: 'daily', 'monthly', or 'hourly'
            
        Returns:
            Dictionary of current usage values
        """
        # Calculate period boundaries
        now = datetime.utcnow()
        if period_type == "daily":
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period_type == "monthly":
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period_type == "hourly":
            period_start = now.replace(minute=0, second=0, microsecond=0)
        else:
            raise ValueError(f"Invalid period_type: {period_type}")
        
        # Query usage from database
        result = self.db.execute(
            text("""
            SELECT query_count, document_count, storage_bytes, 
                   active_db_connections, concurrent_queries, api_calls_count
            FROM tenant_quota_usage
            WHERE tenant_id = :tenant_id AND period_type = :period_type AND period_start = :period_start
            """),
            {"tenant_id": tenant_id, "period_type": period_type, "period_start": period_start}
        ).fetchone()
        
        if result:
            return {
                "query_count": result[0] or 0,
                "document_count": result[1] or 0,
                "storage_bytes": result[2] or 0,
                "active_db_connections": result[3] or 0,
                "concurrent_queries": result[4] or 0,
                "api_calls_count": result[5] or 0,
            }
        
        return {
            "query_count": 0,
            "document_count": 0,
            "storage_bytes": 0,
            "active_db_connections": 0,
            "concurrent_queries": 0,
            "api_calls_count": 0,
        }
    
    def check_query_quota(self, tenant_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if tenant can execute a query within quota limits.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Tuple of (allowed: bool, error_message: Optional[str])
        """
        quotas = self.get_tenant_quotas(tenant_id)
        daily_usage = self.get_current_usage(tenant_id, "daily")
        monthly_usage = self.get_current_usage(tenant_id, "monthly")
        
        # Check daily quota
        daily_limit = quotas["max_queries_per_day"]
        if daily_limit > 0 and daily_usage["query_count"] >= daily_limit:
            return False, f"Daily query quota exceeded ({daily_usage['query_count']}/{daily_limit})"
        
        # Check monthly quota
        monthly_limit = quotas["max_queries_per_month"]
        if monthly_limit > 0 and monthly_usage["query_count"] >= monthly_limit:
            return False, f"Monthly query quota exceeded ({monthly_usage['query_count']}/{monthly_limit})"
        
        return True, None
    
    def check_document_quota(self, tenant_id: str, additional_docs: int = 1) -> Tuple[bool, Optional[str]]:
        """
        Check if tenant can add more documents within quota limits.
        
        Args:
            tenant_id: Tenant identifier
            additional_docs: Number of documents to add
            
        Returns:
            Tuple of (allowed: bool, error_message: Optional[str])
        """
        quotas = self.get_tenant_quotas(tenant_id)
        usage = self.get_current_usage(tenant_id, "daily")
        
        doc_limit = quotas["max_documents"]
        if doc_limit > 0 and (usage["document_count"] + additional_docs) > doc_limit:
            return False, f"Document quota exceeded ({usage['document_count'] + additional_docs}/{doc_limit})"
        
        return True, None
    
    def check_storage_quota(self, tenant_id: str, additional_bytes: int = 0) -> Tuple[bool, Optional[str]]:
        """
        Check if tenant has enough storage quota.
        
        Args:
            tenant_id: Tenant identifier
            additional_bytes: Additional bytes to store
            
        Returns:
            Tuple of (allowed: bool, error_message: Optional[str])
        """
        quotas = self.get_tenant_quotas(tenant_id)
        usage = self.get_current_usage(tenant_id, "daily")
        
        storage_limit = quotas["max_storage_bytes"]
        if storage_limit > 0 and (usage["storage_bytes"] + additional_bytes) > storage_limit:
            used_gb = (usage["storage_bytes"] + additional_bytes) / (1024**3)
            limit_gb = storage_limit / (1024**3)
            return False, f"Storage quota exceeded ({used_gb:.2f}GB/{limit_gb:.2f}GB)"
        
        return True, None
    
    def check_connection_quota(self, tenant_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if tenant can create more database connections.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Tuple of (allowed: bool, error_message: Optional[str])
        """
        quotas = self.get_tenant_quotas(tenant_id)
        usage = self.get_current_usage(tenant_id, "daily")
        
        conn_limit = quotas["max_db_connections"]
        if conn_limit > 0 and usage["active_db_connections"] >= conn_limit:
            return False, f"Database connection quota exceeded ({usage['active_db_connections']}/{conn_limit})"
        
        return True, None
    
    def check_api_rate_limit(self, tenant_id: str, period: str = "minute") -> Tuple[bool, Optional[str]]:
        """
        Check if tenant is within API rate limits.
        
        Args:
            tenant_id: Tenant identifier
            period: 'minute' or 'hour'
            
        Returns:
            Tuple of (allowed: bool, error_message: Optional[str])
        """
        quotas = self.get_tenant_quotas(tenant_id)
        usage = self.get_current_usage(tenant_id, "hourly")
        
        if period == "minute":
            # For minute-based rate limiting, we'd need more granular tracking
            # For now, use hourly data as approximation
            limit = quotas["max_api_calls_per_minute"]
            current = usage["api_calls_count"] / 60  # Rough estimate
            if limit > 0 and current >= limit:
                return False, f"API rate limit exceeded ({int(current)}/{limit} per minute)"
        elif period == "hour":
            limit = quotas["max_api_calls_per_hour"]
            current = usage["api_calls_count"]
            if limit > 0 and current >= limit:
                return False, f"API rate limit exceeded ({current}/{limit} per hour)"
        
        return True, None
    
    def increment_usage(
        self,
        tenant_id: str,
        usage_type: str,
        amount: int = 1,
        period_type: str = "daily"
    ) -> None:
        """
        Increment usage counter for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            usage_type: Type of usage ('query', 'document', 'storage', 'connection', 'api_call')
            amount: Amount to increment
            period_type: 'daily', 'monthly', or 'hourly'
        """
        now = datetime.utcnow()
        
        # Calculate period boundaries
        if period_type == "daily":
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)
        elif period_type == "monthly":
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Calculate next month
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)
        elif period_type == "hourly":
            period_start = now.replace(minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(hours=1)
        else:
            raise ValueError(f"Invalid period_type: {period_type}")
        
        # Map usage_type to column name
        column_map = {
            "query": "query_count",
            "document": "document_count",
            "storage": "storage_bytes",
            "connection": "active_db_connections",
            "concurrent_query": "concurrent_queries",
            "api_call": "api_calls_count",
        }
        
        column = column_map.get(usage_type)
        if not column:
            raise ValueError(f"Invalid usage_type: {usage_type}")
        
        # Insert or update usage record
        self.db.execute(
            text(f"""
            INSERT INTO tenant_quota_usage 
                (tenant_id, period_type, period_start, period_end, {column}, updated_at)
            VALUES (:tenant_id, :period_type, :period_start, :period_end, :amount, :now)
            ON CONFLICT(tenant_id, period_type, period_start) 
            DO UPDATE SET 
                {column} = {column} + :amount2,
                updated_at = :now2
            """),
            {"tenant_id": tenant_id, "period_type": period_type, "period_start": period_start, 
             "period_end": period_end, "amount": amount, "now": now, "amount2": amount, "now2": now}
        )
        self.db.commit()
        
        logger.debug(f"Incremented {usage_type} usage for tenant {tenant_id} by {amount}")
    
    def get_quota_status(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get comprehensive quota status for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dictionary with quota limits, current usage, and percentages
        """
        quotas = self.get_tenant_quotas(tenant_id)
        daily_usage = self.get_current_usage(tenant_id, "daily")
        monthly_usage = self.get_current_usage(tenant_id, "monthly")
        
        def calc_percentage(current: int, limit: int) -> float:
            if limit <= 0:  # Unlimited
                return 0.0
            return (current / limit) * 100
        
        return {
            "tenant_id": tenant_id,
            "quotas": quotas,
            "daily_usage": {
                "queries": {
                    "current": daily_usage["query_count"],
                    "limit": quotas["max_queries_per_day"],
                    "percentage": calc_percentage(daily_usage["query_count"], quotas["max_queries_per_day"])
                },
                "api_calls": {
                    "current": daily_usage["api_calls_count"],
                    "limit": quotas["max_api_calls_per_hour"] * 24,
                    "percentage": calc_percentage(daily_usage["api_calls_count"], quotas["max_api_calls_per_hour"] * 24)
                }
            },
            "monthly_usage": {
                "queries": {
                    "current": monthly_usage["query_count"],
                    "limit": quotas["max_queries_per_month"],
                    "percentage": calc_percentage(monthly_usage["query_count"], quotas["max_queries_per_month"])
                }
            },
            "storage": {
                "current_bytes": daily_usage["storage_bytes"],
                "limit_bytes": quotas["max_storage_bytes"],
                "current_gb": daily_usage["storage_bytes"] / (1024**3),
                "limit_gb": quotas["max_storage_bytes"] / (1024**3) if quotas["max_storage_bytes"] > 0 else -1,
                "percentage": calc_percentage(daily_usage["storage_bytes"], quotas["max_storage_bytes"])
            },
            "connections": {
                "current": daily_usage["active_db_connections"],
                "limit": quotas["max_db_connections"],
                "percentage": calc_percentage(daily_usage["active_db_connections"], quotas["max_db_connections"])
            },
            "documents": {
                "current": daily_usage["document_count"],
                "limit": quotas["max_documents"],
                "percentage": calc_percentage(daily_usage["document_count"], quotas["max_documents"])
            }
        }
    
    def update_tenant_quotas(self, tenant_id: str, quotas: Dict[str, int]) -> None:
        """
        Update quota limits for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            quotas: Dictionary of quota values to update
        """
        # Verify tenant exists
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Build update query
        valid_fields = [
            "max_queries_per_day", "max_queries_per_month", "max_documents",
            "max_storage_bytes", "max_db_connections", "max_concurrent_queries",
            "max_api_calls_per_minute", "max_api_calls_per_hour"
        ]
        
        updates = []
        params = {"tenant_id": tenant_id, "updated_at": datetime.utcnow()}
        
        for field, value in quotas.items():
            if field in valid_fields:
                updates.append(f"{field} = :{field}")
                params[field] = value
        
        if not updates:
            return
        
        # Build placeholders for INSERT
        field_placeholders = ', '.join([f":{f}" for f in valid_fields])
        
        # Update or insert quotas
        self.db.execute(
            text(f"""
            INSERT INTO tenant_quotas (tenant_id, {', '.join(valid_fields)}, updated_at)
            VALUES (:tenant_id, {field_placeholders}, :updated_at)
            ON CONFLICT(tenant_id) 
            DO UPDATE SET {', '.join(updates)}, updated_at = :updated_at
            """),
            {**params, **{f: quotas.get(f, 0) for f in valid_fields}}
        )
        self.db.commit()
        
        logger.info(f"Updated quotas for tenant {tenant_id}")
