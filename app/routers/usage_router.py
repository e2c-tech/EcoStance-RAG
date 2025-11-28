"""
Usage Analytics Router - endpoints for viewing API usage statistics.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from ..db.database import get_db
from ..services.usage_tracking_service import UsageTrackingService
from ..auth.dependencies import get_current_tenant


router = APIRouter(prefix="/api/v1/usage", tags=["Usage Analytics"])


# Response Models
class UsageStatsResponse(BaseModel):
    """Response model for usage statistics."""
    total_requests: int
    status_codes: dict
    avg_response_time_ms: float
    error_count: int
    error_rate_percent: float
    top_endpoints: List[dict]
    period: dict


class EndpointStatsResponse(BaseModel):
    """Response model for endpoint statistics."""
    endpoint: str
    total_requests: int
    response_times: dict


@router.get("/stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze (1-90)"),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get usage statistics for the current tenant.
    
    Returns:
    - Total request count
    - Breakdown by status code
    - Average response time
    - Error rate
    - Top 10 most used endpoints
    
    **days**: Number of days to analyze (default: 7, max: 90)
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        stats = UsageTrackingService.get_usage_stats(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage stats: {str(e)}"
        )


@router.get("/endpoint/{endpoint:path}", response_model=EndpointStatsResponse)
async def get_endpoint_stats(
    endpoint: str,
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze (1-90)"),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get detailed statistics for a specific endpoint.
    
    Returns:
    - Total requests
    - Response time percentiles (p50, p95, p99)
    - Min/max response times
    
    **endpoint**: Endpoint path (e.g., /api/v1/query)
    **days**: Number of days to analyze (default: 7, max: 90)
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Prepend slash if not present
        if not endpoint.startswith('/'):
            endpoint = f'/{endpoint}'
        
        stats = UsageTrackingService.get_endpoint_stats(
            db=db,
            tenant_id=tenant_id,
            endpoint=endpoint,
            start_date=start_date,
            end_date=end_date
        )
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get endpoint stats: {str(e)}"
        )


@router.get("/export")
async def export_usage_data(
    days: int = Query(30, ge=1, le=365, description="Number of days to export (1-365)"),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Export usage data for the current tenant.
    
    Returns raw usage data in JSON format for the specified time period.
    
    **days**: Number of days to export (default: 30, max: 365)
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        data = UsageTrackingService.export_usage_data(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            format="json"
        )
        
        return {
            "tenant_id": tenant_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_records": len(data),
            "data": data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export usage data: {str(e)}"
        )
