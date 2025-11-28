"""
Quota Router - API endpoints for quota management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel

from app.db.database import get_db
from app.auth.dependencies import get_current_user, get_current_tenant, require_admin
from app.services.quota_service import QuotaService, QuotaExceededException

router = APIRouter(prefix="/api/v1/quota", tags=["quota"])


class QuotaUpdateRequest(BaseModel):
    """Request model for updating quotas."""
    max_queries_per_day: int | None = None
    max_queries_per_month: int | None = None
    max_documents: int | None = None
    max_storage_bytes: int | None = None
    max_db_connections: int | None = None
    max_concurrent_queries: int | None = None
    max_api_calls_per_minute: int | None = None
    max_api_calls_per_hour: int | None = None


@router.get("/status")
async def get_quota_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current quota status for the tenant.
    
    Returns quota limits, current usage, and percentages organized into:
    - Storage (limit_bytes, used_bytes, available_bytes, usage_percent)
    - Queries (daily_limit, daily_used, monthly_limit, monthly_used, daily_percent, monthly_percent)
    - Documents (limit, used, available, usage_percent)
    - Connections (max_connections, active_connections)
    - API Calls (hourly_limit, hourly_used, minute_limit, minute_used)
    """
    try:
        tenant_id = current_user["tenant_id"]
        quota_service = QuotaService(db)
        
        # Get comprehensive status
        status = quota_service.get_quota_status(tenant_id)
        quotas = status["quotas"]
        daily = status["daily_usage"]
        monthly = status["monthly_usage"]
        storage = status["storage"]
        connections = status["connections"]
        documents = status["documents"]
        
        # Format response according to spec
        return {
            "storage": {
                "limit_bytes": quotas["max_storage_bytes"],
                "used_bytes": storage["current_bytes"],
                "available_bytes": max(0, quotas["max_storage_bytes"] - storage["current_bytes"]) if quotas["max_storage_bytes"] > 0 else -1,
                "usage_percent": storage["percentage"]
            },
            "queries": {
                "daily_limit": quotas["max_queries_per_day"],
                "daily_used": daily["queries"]["current"],
                "monthly_limit": quotas["max_queries_per_month"],
                "monthly_used": monthly["queries"]["current"],
                "daily_percent": daily["queries"]["percentage"],
                "monthly_percent": monthly["queries"]["percentage"]
            },
            "documents": {
                "limit": quotas["max_documents"],
                "used": documents["current"],
                "available": max(0, quotas["max_documents"] - documents["current"]) if quotas["max_documents"] > 0 else -1,
                "usage_percent": documents["percentage"]
            },
            "connections": {
                "max_connections": quotas["max_db_connections"],
                "active_connections": connections["current"]
            },
            "api_calls": {
                "hourly_limit": quotas["max_api_calls_per_hour"],
                "hourly_used": daily["api_calls"]["current"],
                "minute_limit": quotas["max_api_calls_per_minute"],
                "minute_used": 0  # Would need more granular tracking
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch quota status: {str(e)}"
        )


@router.get("/limits")
async def get_quota_limits(
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get quota limits for the tenant."""
    try:
        quota_service = QuotaService(db)
        limits = quota_service.get_tenant_quotas(tenant_id)
        return {
            "success": True,
            "data": limits
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quota limits: {str(e)}"
        )


@router.get("/usage")
async def get_quota_usage(
    period: str = "daily",
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current usage for the tenant.
    
    Args:
        period: 'daily', 'monthly', or 'hourly'
    """
    if period not in ["daily", "monthly", "hourly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period. Must be 'daily', 'monthly', or 'hourly'"
        )
    
    try:
        quota_service = QuotaService(db)
        usage = quota_service.get_current_usage(tenant_id, period)
        return {
            "success": True,
            "period": period,
            "data": usage
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quota usage: {str(e)}"
        )


@router.get("/history")
async def get_quota_history(
    days: int = 30,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get quota usage history.
    
    Args:
        days: Number of days to look back (default: 30)
    """
    try:
        # Query usage history from database
        from datetime import datetime, timedelta
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        results = db.execute(
            """
            SELECT period_start, period_type, query_count, document_count, 
                   storage_bytes, api_calls_count
            FROM tenant_quota_usage
            WHERE tenant_id = ? AND period_start >= ? AND period_start <= ?
            ORDER BY period_start DESC
            """,
            (tenant_id, start_date, end_date)
        ).fetchall()
        
        history = [
            {
                "date": row[0],
                "period_type": row[1],
                "query_count": row[2] or 0,
                "document_count": row[3] or 0,
                "storage_bytes": row[4] or 0,
                "storage_gb": (row[4] or 0) / (1024**3),
                "api_calls": row[5] or 0
            }
            for row in results
        ]
        
        return {
            "success": True,
            "days": days,
            "data": history
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quota history: {str(e)}"
        )


# Admin endpoints
@router.put("/admin/tenant/{tenant_id}")
async def update_tenant_quotas(
    tenant_id: str,
    quotas: QuotaUpdateRequest,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update quota limits for a tenant (admin only).
    
    Args:
        tenant_id: Target tenant ID
        quotas: New quota values
    """
    try:
        quota_service = QuotaService(db)
        
        # Build update dictionary (only include non-None values)
        updates = {}
        for field, value in quotas.dict(exclude_none=True).items():
            if value is not None:
                updates[field] = value
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No quota values provided"
            )
        
        quota_service.update_tenant_quotas(tenant_id, updates)
        
        # Get updated status
        new_status = quota_service.get_quota_status(tenant_id)
        
        return {
            "success": True,
            "message": f"Updated quotas for tenant {tenant_id}",
            "data": new_status
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update quotas: {str(e)}"
        )


@router.post("/admin/tenant/{tenant_id}/reset")
async def reset_tenant_quotas(
    tenant_id: str,
    period: str = "daily",
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually reset quota usage for a tenant (admin only).
    
    Args:
        tenant_id: Target tenant ID
        period: Period to reset ('daily', 'monthly', 'hourly')
    """
    if period not in ["daily", "monthly", "hourly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period. Must be 'daily', 'monthly', or 'hourly'"
        )
    
    try:
        from datetime import datetime
        
        # Calculate period start based on type
        now = datetime.utcnow()
        if period == "daily":
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "monthly":
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # hourly
            period_start = now.replace(minute=0, second=0, microsecond=0)
        
        # Reset usage to 0
        db.execute(
            """
            UPDATE tenant_quota_usage
            SET query_count = 0, document_count = 0, storage_bytes = 0,
                active_db_connections = 0, concurrent_queries = 0, api_calls_count = 0,
                updated_at = ?
            WHERE tenant_id = ? AND period_type = ? AND period_start = ?
            """,
            (now, tenant_id, period, period_start)
        )
        db.commit()
        
        return {
            "success": True,
            "message": f"Reset {period} quota usage for tenant {tenant_id}",
            "period": period,
            "period_start": period_start.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset quotas: {str(e)}"
        )
