"""
Usage Tracking Service - tracks API usage, response times, and errors per tenant.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Index
from sqlalchemy import func, and_

from ..db.database import Base

logger = logging.getLogger(__name__)


class APIUsage(Base):
    """Model for tracking API usage."""
    __tablename__ = "api_usage"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    
    # Request details
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE
    
    # Authentication
    auth_method = Column(String(50))  # jwt, api_key, header
    api_key_id = Column(String(36), nullable=True)  # If authenticated via API key
    
    # Response details
    status_code = Column(Integer, nullable=False, index=True)
    response_time_ms = Column(Float, nullable=False)  # Response time in milliseconds
    
    # Error tracking
    error_type = Column(String(100), nullable=True)
    error_message = Column(String(500), nullable=True)
    
    # Additional metadata
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(50), nullable=True)
    request_size_bytes = Column(Integer, nullable=True)
    response_size_bytes = Column(Integer, nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_tenant_timestamp', 'tenant_id', 'timestamp'),
        Index('idx_tenant_endpoint', 'tenant_id', 'endpoint'),
        Index('idx_tenant_status', 'tenant_id', 'status_code'),
    )


class UsageTrackingService:
    """Service for tracking and analyzing API usage."""
    
    @staticmethod
    def log_request(
        db: Session,
        tenant_id: Optional[str],
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        auth_method: Optional[str] = None,
        api_key_id: Optional[str] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None
    ) -> None:
        """
        Log an API request for usage tracking.
        
        Args:
            db: Database session
            tenant_id: Tenant ID (can be None for unauthenticated requests)
            endpoint: API endpoint path
            method: HTTP method
            status_code: Response status code
            response_time_ms: Response time in milliseconds
            auth_method: Authentication method used
            api_key_id: API key ID if authenticated via API key
            error_type: Error type if request failed
            error_message: Error message if request failed
            user_agent: User agent string
            ip_address: Client IP address
            request_size: Request size in bytes
            response_size: Response size in bytes
        """
        try:
            usage = APIUsage(
                tenant_id=tenant_id or "anonymous",
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                auth_method=auth_method,
                api_key_id=api_key_id,
                error_type=error_type,
                error_message=error_message[:500] if error_message else None,
                user_agent=user_agent[:255] if user_agent else None,
                ip_address=ip_address,
                request_size_bytes=request_size,
                response_size_bytes=response_size
            )
            
            db.add(usage)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log API usage: {str(e)}")
            db.rollback()
    
    @staticmethod
    def get_usage_stats(
        db: Session,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a tenant.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            start_date: Start date for stats (optional)
            end_date: End date for stats (optional)
            
        Returns:
            Dictionary with usage statistics
        """
        query = db.query(APIUsage).filter(APIUsage.tenant_id == tenant_id)
        
        if start_date:
            query = query.filter(APIUsage.timestamp >= start_date)
        if end_date:
            query = query.filter(APIUsage.timestamp <= end_date)
        
        # Total requests
        total_requests = query.count()
        
        # Requests by status code
        status_counts = db.query(
            APIUsage.status_code,
            func.count(APIUsage.id).label('count')
        ).filter(APIUsage.tenant_id == tenant_id)
        
        if start_date:
            status_counts = status_counts.filter(APIUsage.timestamp >= start_date)
        if end_date:
            status_counts = status_counts.filter(APIUsage.timestamp <= end_date)
        
        status_counts = status_counts.group_by(APIUsage.status_code).all()
        
        # Average response time
        avg_response_time = db.query(
            func.avg(APIUsage.response_time_ms)
        ).filter(APIUsage.tenant_id == tenant_id)
        
        if start_date:
            avg_response_time = avg_response_time.filter(APIUsage.timestamp >= start_date)
        if end_date:
            avg_response_time = avg_response_time.filter(APIUsage.timestamp <= end_date)
        
        avg_response_time = avg_response_time.scalar() or 0
        
        # Error rate
        error_count = query.filter(APIUsage.status_code >= 400).count()
        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
        
        # Most used endpoints
        top_endpoints = db.query(
            APIUsage.endpoint,
            func.count(APIUsage.id).label('count')
        ).filter(APIUsage.tenant_id == tenant_id)
        
        if start_date:
            top_endpoints = top_endpoints.filter(APIUsage.timestamp >= start_date)
        if end_date:
            top_endpoints = top_endpoints.filter(APIUsage.timestamp <= end_date)
        
        top_endpoints = top_endpoints.group_by(
            APIUsage.endpoint
        ).order_by(
            func.count(APIUsage.id).desc()
        ).limit(10).all()
        
        return {
            "total_requests": total_requests,
            "status_codes": {str(code): count for code, count in status_counts},
            "avg_response_time_ms": round(avg_response_time, 2),
            "error_count": error_count,
            "error_rate_percent": round(error_rate, 2),
            "top_endpoints": [
                {"endpoint": endpoint, "count": count}
                for endpoint, count in top_endpoints
            ],
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            }
        }
    
    @staticmethod
    def get_endpoint_stats(
        db: Session,
        tenant_id: str,
        endpoint: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get detailed statistics for a specific endpoint.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            endpoint: Endpoint path
            start_date: Start date for stats (optional)
            end_date: End date for stats (optional)
            
        Returns:
            Dictionary with endpoint statistics
        """
        query = db.query(APIUsage).filter(
            and_(
                APIUsage.tenant_id == tenant_id,
                APIUsage.endpoint == endpoint
            )
        )
        
        if start_date:
            query = query.filter(APIUsage.timestamp >= start_date)
        if end_date:
            query = query.filter(APIUsage.timestamp <= end_date)
        
        total_requests = query.count()
        
        # Response time percentiles
        response_times = [r.response_time_ms for r in query.all()]
        response_times.sort()
        
        def percentile(data, p):
            if not data:
                return 0
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = f + 1 if f < len(data) - 1 else f
            return data[f] + (k - f) * (data[c] - data[f])
        
        return {
            "endpoint": endpoint,
            "total_requests": total_requests,
            "response_times": {
                "avg_ms": round(sum(response_times) / len(response_times), 2) if response_times else 0,
                "p50_ms": round(percentile(response_times, 50), 2),
                "p95_ms": round(percentile(response_times, 95), 2),
                "p99_ms": round(percentile(response_times, 99), 2),
                "min_ms": round(min(response_times), 2) if response_times else 0,
                "max_ms": round(max(response_times), 2) if response_times else 0
            }
        }
    
    @staticmethod
    def export_usage_data(
        db: Session,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = "json"
    ) -> list:
        """
        Export usage data for a tenant.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            start_date: Start date (optional)
            end_date: End date (optional)
            format: Export format (json or csv)
            
        Returns:
            List of usage records
        """
        query = db.query(APIUsage).filter(APIUsage.tenant_id == tenant_id)
        
        if start_date:
            query = query.filter(APIUsage.timestamp >= start_date)
        if end_date:
            query = query.filter(APIUsage.timestamp <= end_date)
        
        query = query.order_by(APIUsage.timestamp.desc())
        
        records = []
        for usage in query.all():
            records.append({
                "timestamp": usage.timestamp.isoformat(),
                "endpoint": usage.endpoint,
                "method": usage.method,
                "status_code": usage.status_code,
                "response_time_ms": usage.response_time_ms,
                "auth_method": usage.auth_method,
                "error_type": usage.error_type,
                "error_message": usage.error_message
            })
        
        return records
