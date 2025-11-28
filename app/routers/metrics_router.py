"""
Metrics Router - API endpoints for tenant metrics and monitoring.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import csv
import io

from app.db.database import get_db
from app.auth.dependencies import get_current_tenant, require_admin
from app.services.metrics_service import MetricsService
from app.services.alerting_service import AlertingService

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/")
async def get_tenant_metrics(
    metric_type: str = Query("daily", regex="^(hourly|daily|monthly)$"),
    days: int = Query(30, ge=1, le=365),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get metrics for the tenant.
    
    Args:
        metric_type: Type of metrics ('hourly', 'daily', 'monthly')
        days: Number of days to look back
    """
    try:
        metrics_service = MetricsService(db)
        metrics = metrics_service.get_tenant_metrics(
            tenant_id=tenant_id,
            metric_type=metric_type,
            limit=days
        )
        
        return {
            "success": True,
            "metric_type": metric_type,
            "days": days,
            "count": len(metrics),
            "data": metrics
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.get("/storage")
async def get_storage_metrics(
    days: int = Query(30, ge=1, le=365),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get storage usage metrics over time.
    
    Args:
        days: Number of days to look back
    """
    try:
        metrics_service = MetricsService(db)
        storage_data = metrics_service.get_storage_usage_over_time(tenant_id, days)
        
        return {
            "success": True,
            "days": days,
            "data": storage_data
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get storage metrics: {str(e)}"
        )


@router.get("/queries")
async def get_query_metrics(
    days: int = Query(7, ge=1, le=90),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get query performance metrics.
    
    Args:
        days: Number of days to analyze
    """
    try:
        metrics_service = MetricsService(db)
        query_metrics = metrics_service.get_query_performance_metrics(tenant_id, days)
        
        return {
            "success": True,
            "days": days,
            "data": query_metrics
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get query metrics: {str(e)}"
        )


@router.get("/errors")
async def get_error_metrics(
    days: int = Query(7, ge=1, le=90),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get error rate metrics.
    
    Args:
        days: Number of days to analyze
    """
    try:
        metrics_service = MetricsService(db)
        error_data = metrics_service.get_error_rate_metrics(tenant_id, days)
        
        return {
            "success": True,
            "days": days,
            "data": error_data
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get error metrics: {str(e)}"
        )


@router.get("/alerts")
async def get_active_alerts(
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get active alerts for the tenant."""
    try:
        alerting_service = AlertingService(db)
        alerts = alerting_service.check_all_alerts(tenant_id)
        
        return {
            "success": True,
            "count": len(alerts),
            "data": alerts
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alerts: {str(e)}"
        )


@router.get("/alerts/history")
async def get_alert_history(
    days: int = Query(7, ge=1, le=90),
    severity: Optional[str] = Query(None, regex="^(info|warning|critical)$"),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get alert history for the tenant.
    
    Args:
        days: Number of days to look back
        severity: Filter by severity level
    """
    try:
        alerting_service = AlertingService(db)
        history = alerting_service.get_alert_history(tenant_id, days, severity)
        
        return {
            "success": True,
            "days": days,
            "severity_filter": severity,
            "count": len(history),
            "data": history
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert history: {str(e)}"
        )


@router.get("/export")
async def export_metrics(
    format: str = Query("csv", regex="^(csv|json)$"),
    days: int = Query(30, ge=1, le=365),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Export metrics data.
    
    Args:
        format: Export format ('csv' or 'json')
        days: Number of days to export
    """
    try:
        metrics_service = MetricsService(db)
        metrics = metrics_service.get_tenant_metrics(
            tenant_id=tenant_id,
            metric_type="daily",
            limit=days
        )
        
        if format == "csv":
            # Create CSV
            output = io.StringIO()
            if metrics:
                fieldnames = ["date", "storage_gb", "document_count", "query_count", 
                             "query_success_rate", "api_calls", "api_success_rate"]
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                
                for metric in metrics:
                    writer.writerow({
                        "date": metric["period_start"],
                        "storage_gb": metric["storage"]["gb"],
                        "document_count": metric["storage"]["document_count"],
                        "query_count": metric["queries"]["total"],
                        "query_success_rate": metric["queries"]["success_rate"],
                        "api_calls": metric["api"]["total_calls"],
                        "api_success_rate": metric["api"]["success_rate"]
                    })
            
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=metrics_{tenant_id}_{datetime.utcnow().date()}.csv"}
            )
        else:  # json
            import json
            return {
                "success": True,
                "format": "json",
                "tenant_id": tenant_id,
                "exported_at": datetime.utcnow().isoformat(),
                "data": metrics
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export metrics: {str(e)}"
        )


# Admin endpoints
@router.get("/admin/all")
async def get_all_tenant_metrics(
    metric_type: str = Query("daily", regex="^(hourly|daily|monthly)$"),
    limit: int = Query(100, ge=1, le=1000),
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get metrics for all tenants (admin only).
    
    Args:
        metric_type: Type of metrics
        limit: Maximum number of records per tenant
    """
    try:
        from app.models.tenant import Tenant
        
        # Get all active tenants
        tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
        
        metrics_service = MetricsService(db)
        all_metrics = {}
        
        for tenant in tenants:
            metrics = metrics_service.get_tenant_metrics(
                tenant_id=tenant.id,
                metric_type=metric_type,
                limit=limit
            )
            all_metrics[tenant.id] = {
                "tenant_name": tenant.name,
                "tenant_tier": tenant.billing_tier,
                "metrics": metrics
            }
        
        return {
            "success": True,
            "metric_type": metric_type,
            "tenant_count": len(all_metrics),
            "data": all_metrics
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get all tenant metrics: {str(e)}"
        )


@router.post("/admin/aggregate")
async def trigger_metrics_aggregation(
    period: str = Query("hourly", regex="^(hourly|daily)$"),
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually trigger metrics aggregation (admin only).
    
    Args:
        period: Period to aggregate ('hourly' or 'daily')
    """
    try:
        from app.models.tenant import Tenant
        
        metrics_service = MetricsService(db)
        tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
        
        aggregated_count = 0
        now = datetime.utcnow()
        
        for tenant in tenants:
            try:
                if period == "hourly":
                    metrics_service.aggregate_hourly_metrics(tenant.id, now)
                else:  # daily
                    metrics_service.aggregate_daily_metrics(tenant.id, now)
                aggregated_count += 1
            except Exception as e:
                logger.error(f"Failed to aggregate metrics for tenant {tenant.id}: {e}")
        
        return {
            "success": True,
            "message": f"Aggregated {period} metrics for {aggregated_count} tenants",
            "period": period,
            "tenant_count": aggregated_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger aggregation: {str(e)}"
        )
