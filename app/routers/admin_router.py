"""
Admin Router - API endpoints for administrative tasks.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel

from app.db.database import get_db
from app.auth.dependencies import require_admin
from app.services.cleanup_service import CleanupService
from app.config import QDRANT_URL, QDRANT_API_KEY
from qdrant_client import QdrantClient

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class TenantDeletionRequest(BaseModel):
    """Request model for tenant deletion."""
    soft_delete: bool = True
    confirm: bool = False


class DataExportRequest(BaseModel):
    """Request model for data export."""
    export_path: str | None = None


def get_qdrant_client():
    """Get Qdrant client instance."""
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    request: TenantDeletionRequest,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Delete a tenant and all associated data (admin only).
    
    Args:
        tenant_id: Tenant to delete
        request: Deletion options
    """
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deletion must be confirmed by setting 'confirm' to true"
        )
    
    try:
        qdrant_client = get_qdrant_client()
        cleanup_service = CleanupService(db, qdrant_client)
        
        results = cleanup_service.delete_tenant_data(
            tenant_id=tenant_id,
            soft_delete=request.soft_delete
        )
        
        if results["errors"]:
            return {
                "success": False,
                "message": "Tenant deletion completed with errors",
                "data": results
            }
        
        return {
            "success": True,
            "message": f"Tenant {tenant_id} {'soft' if request.soft_delete else 'hard'} deleted successfully",
            "data": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tenant: {str(e)}"
        )


@router.post("/tenants/{tenant_id}/export")
async def export_tenant_data(
    tenant_id: str,
    request: DataExportRequest,
    background_tasks: BackgroundTasks,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Export all data for a tenant (admin only).
    
    Args:
        tenant_id: Tenant to export
        request: Export options
    """
    try:
        import os
        from datetime import datetime
        
        # Generate export path if not provided
        export_path = request.export_path or os.path.join(
            "exports",
            tenant_id,
            datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        )
        
        qdrant_client = get_qdrant_client()
        cleanup_service = CleanupService(db, qdrant_client)
        
        # Run export in background
        def run_export():
            results = cleanup_service.export_tenant_data(tenant_id, export_path)
            # Could send notification when complete
        
        background_tasks.add_task(run_export)
        
        return {
            "success": True,
            "message": f"Export started for tenant {tenant_id}",
            "export_path": export_path,
            "status": "in_progress"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start export: {str(e)}"
        )


@router.get("/tenants/{tenant_id}/storage")
async def get_tenant_storage(
    tenant_id: str,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get storage usage for a tenant (admin only).
    
    Args:
        tenant_id: Tenant to check
    """
    try:
        qdrant_client = get_qdrant_client()
        cleanup_service = CleanupService(db, qdrant_client)
        
        storage_info = cleanup_service.get_tenant_storage_usage(tenant_id)
        
        return {
            "success": True,
            "data": storage_info
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get storage info: {str(e)}"
        )


@router.post("/cleanup/sessions")
async def cleanup_sessions(
    max_age_hours: int = 24,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Clean up expired sessions (admin only).
    
    Args:
        max_age_hours: Maximum age of sessions in hours
    """
    try:
        qdrant_client = get_qdrant_client()
        cleanup_service = CleanupService(db, qdrant_client)
        
        deleted_count = cleanup_service.cleanup_expired_sessions(max_age_hours)
        
        return {
            "success": True,
            "message": f"Cleaned up {deleted_count} expired sessions",
            "deleted_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup sessions: {str(e)}"
        )


@router.post("/cleanup/temp-files")
async def cleanup_temp_files(
    max_age_days: int = 7,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Clean up old temporary files (admin only).
    
    Args:
        max_age_days: Maximum age of temp files in days
    """
    try:
        qdrant_client = get_qdrant_client()
        cleanup_service = CleanupService(db, qdrant_client)
        
        deleted_count = cleanup_service.cleanup_temporary_files(max_age_days)
        
        return {
            "success": True,
            "message": f"Cleaned up {deleted_count} temporary files",
            "deleted_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup temp files: {str(e)}"
        )


@router.post("/cleanup/audit-logs")
async def archive_audit_logs(
    max_age_days: int = 90,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Archive old audit logs (admin only).
    
    Args:
        max_age_days: Maximum age of logs to keep
    """
    try:
        qdrant_client = get_qdrant_client()
        cleanup_service = CleanupService(db, qdrant_client)
        
        archived_count = cleanup_service.archive_old_audit_logs(max_age_days)
        
        return {
            "success": True,
            "message": f"Archived {archived_count} audit logs",
            "archived_count": archived_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive audit logs: {str(e)}"
        )


@router.post("/cleanup/all")
async def run_daily_cleanup(
    background_tasks: BackgroundTasks,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Run all daily cleanup tasks (admin only).
    """
    try:
        qdrant_client = get_qdrant_client()
        cleanup_service = CleanupService(db, qdrant_client)
        
        # Run cleanup in background
        def run_cleanup():
            results = cleanup_service.run_daily_cleanup()
            # Could send notification when complete
        
        background_tasks.add_task(run_cleanup)
        
        return {
            "success": True,
            "message": "Daily cleanup tasks started",
            "status": "in_progress"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start cleanup: {str(e)}"
        )


@router.get("/health/system")
async def get_system_health(
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get system-wide health metrics (admin only).
    """
    try:
        from app.models.tenant import Tenant
        
        # Get tenant counts
        total_tenants = db.query(Tenant).count()
        active_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
        
        # Get total storage usage
        qdrant_client = get_qdrant_client()
        cleanup_service = CleanupService(db, qdrant_client)
        
        total_storage = 0
        tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
        for tenant in tenants:
            storage_info = cleanup_service.get_tenant_storage_usage(tenant.id)
            total_storage += storage_info["total_bytes"]
        
        # Get recent metrics
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        recent_api_calls = db.execute(
            "SELECT COUNT(*) FROM api_usage WHERE timestamp >= ?",
            (cutoff,)
        ).fetchone()[0]
        
        recent_errors = db.execute(
            "SELECT COUNT(*) FROM api_usage WHERE timestamp >= ? AND status_code >= 400",
            (cutoff,)
        ).fetchone()[0]
        
        error_rate = (recent_errors / recent_api_calls * 100) if recent_api_calls > 0 else 0
        
        return {
            "success": True,
            "data": {
                "tenants": {
                    "total": total_tenants,
                    "active": active_tenants,
                    "inactive": total_tenants - active_tenants
                },
                "storage": {
                    "total_bytes": total_storage,
                    "total_gb": total_storage / (1024**3)
                },
                "api": {
                    "calls_24h": recent_api_calls,
                    "errors_24h": recent_errors,
                    "error_rate": error_rate
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system health: {str(e)}"
        )


# ============================================================================
# PHASE 5: Enhanced Admin Endpoints
# ============================================================================

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get admin dashboard summary statistics.
    Provides high-level overview of system status.
    """
    try:
        from app.models.tenant import Tenant
        from app.models.api_key import TenantAPIKey
        from datetime import datetime, timedelta
        
        # Tenant statistics
        total_tenants = db.query(Tenant).count()
        active_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
        
        # User statistics (if user model exists)
        try:
            from app.models.user import TenantUser
            total_users = db.query(TenantUser).count()
        except:
            total_users = 0
        
        # Storage statistics
        qdrant_client = get_qdrant_client()
        cleanup_service = CleanupService(db, qdrant_client)
        
        total_storage = 0
        tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
        for tenant in tenants:
            try:
                storage_info = cleanup_service.get_tenant_storage_usage(tenant.id)
                total_storage += storage_info.get("total_bytes", 0)
            except:
                pass
        
        # API usage today
        today = datetime.utcnow().date()
        try:
            total_queries_today = db.execute(
                "SELECT COUNT(*) FROM api_usage WHERE DATE(timestamp) = ?",
                (today,)
            ).fetchone()[0]
            
            total_api_calls_today = db.execute(
                "SELECT COUNT(*) FROM api_usage WHERE DATE(timestamp) = ?",
                (today,)
            ).fetchone()[0]
        except:
            total_queries_today = 0
            total_api_calls_today = 0
        
        # Recent alerts (last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        try:
            from app.models.alert import Alert
            recent_alerts = db.query(Alert).filter(
                Alert.created_at >= cutoff
            ).order_by(Alert.created_at.desc()).limit(5).all()
            
            alert_list = [
                {
                    "id": alert.id,
                    "tenant_id": alert.tenant_id,
                    "type": alert.alert_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "created_at": alert.created_at.isoformat()
                }
                for alert in recent_alerts
            ]
        except:
            alert_list = []
        
        # System health
        error_count = 0
        try:
            error_count = db.execute(
                "SELECT COUNT(*) FROM api_usage WHERE timestamp >= ? AND status_code >= 400",
                (cutoff,)
            ).fetchone()[0]
        except:
            pass
        
        system_health = "healthy" if error_count < 100 else "degraded" if error_count < 500 else "critical"
        
        return {
            "success": True,
            "data": {
                "total_tenants": total_tenants,
                "active_tenants": active_tenants,
                "total_users": total_users,
                "total_storage_gb": round(total_storage / (1024**3), 2),
                "total_queries_today": total_queries_today,
                "total_api_calls_today": total_api_calls_today,
                "system_health": system_health,
                "recent_alerts": alert_list,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard summary: {str(e)}"
        )


@router.get("/tenants/search")
async def search_tenants(
    q: str,
    limit: int = 20,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Search tenants by name, email, or slug.
    Returns matching tenants with basic info.
    """
    try:
        from app.models.tenant import Tenant
        
        # Search by name, email, or slug
        search_pattern = f"%{q}%"
        tenants = db.query(Tenant).filter(
            (Tenant.name.ilike(search_pattern)) |
            (Tenant.email.ilike(search_pattern)) |
            (Tenant.slug.ilike(search_pattern))
        ).limit(limit).all()
        
        results = [
            {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
                "email": tenant.email,
                "is_active": tenant.is_active,
                "billing_tier": tenant.billing_tier,
                "billing_status": tenant.billing_status,
                "created_at": tenant.created_at.isoformat()
            }
            for tenant in tenants
        ]
        
        return {
            "success": True,
            "data": {
                "query": q,
                "count": len(results),
                "tenants": results
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search tenants: {str(e)}"
        )


@router.patch("/tenants/{tenant_id}/tier")
async def update_tenant_tier(
    tenant_id: str,
    tier: str,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update tenant billing tier and adjust quotas accordingly.
    Valid tiers: free, starter, professional, enterprise
    """
    try:
        from app.models.tenant import Tenant
        from datetime import datetime
        
        # Validate tier
        valid_tiers = ["free", "starter", "professional", "enterprise"]
        if tier not in valid_tiers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier. Must be one of: {', '.join(valid_tiers)}"
            )
        
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Update tier
        old_tier = tenant.billing_tier
        tenant.billing_tier = tier
        
        # Update quotas based on tier
        tier_quotas = {
            "free": {
                "max_storage_bytes": 10 * 1024**3,  # 10GB
                "max_queries_per_day": 1000,
                "max_queries_per_month": 30000,
                "max_documents": 10000,
                "max_db_connections": 5
            },
            "starter": {
                "max_storage_bytes": 50 * 1024**3,  # 50GB
                "max_queries_per_day": 5000,
                "max_queries_per_month": 150000,
                "max_documents": 50000,
                "max_db_connections": 10
            },
            "professional": {
                "max_storage_bytes": 200 * 1024**3,  # 200GB
                "max_queries_per_day": 20000,
                "max_queries_per_month": 600000,
                "max_documents": 200000,
                "max_db_connections": 25
            },
            "enterprise": {
                "max_storage_bytes": 1000 * 1024**3,  # 1TB
                "max_queries_per_day": 100000,
                "max_queries_per_month": 3000000,
                "max_documents": 1000000,
                "max_db_connections": 100
            }
        }
        
        settings = tenant.settings or {}
        settings.update(tier_quotas[tier])
        tenant.settings = settings
        tenant.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(tenant)
        
        return {
            "success": True,
            "message": f"Tenant tier updated from {old_tier} to {tier}",
            "data": {
                "tenant_id": tenant_id,
                "old_tier": old_tier,
                "new_tier": tier,
                "quotas": tier_quotas[tier]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tenant tier: {str(e)}"
        )


@router.post("/tenants/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: str,
    reason: str,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Suspend a tenant account.
    Prevents all API access until reactivated.
    """
    try:
        from app.models.tenant import Tenant
        from datetime import datetime
        
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Suspend tenant
        tenant.is_active = False
        tenant.billing_status = "suspended"
        tenant.updated_at = datetime.utcnow()
        
        # Log suspension reason in settings
        settings = tenant.settings or {}
        settings["suspension"] = {
            "reason": reason,
            "suspended_at": datetime.utcnow().isoformat(),
            "suspended_by": admin_tenant_id
        }
        tenant.settings = settings
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Tenant {tenant_id} suspended",
            "data": {
                "tenant_id": tenant_id,
                "reason": reason,
                "suspended_at": datetime.utcnow().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to suspend tenant: {str(e)}"
        )


@router.post("/tenants/{tenant_id}/reactivate")
async def reactivate_tenant(
    tenant_id: str,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Reactivate a suspended tenant account.
    Restores full API access.
    """
    try:
        from app.models.tenant import Tenant
        from datetime import datetime
        
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Reactivate tenant
        tenant.is_active = True
        tenant.billing_status = "active"
        tenant.updated_at = datetime.utcnow()
        
        # Log reactivation in settings
        settings = tenant.settings or {}
        if "suspension" in settings:
            settings["suspension"]["reactivated_at"] = datetime.utcnow().isoformat()
            settings["suspension"]["reactivated_by"] = admin_tenant_id
        tenant.settings = settings
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Tenant {tenant_id} reactivated",
            "data": {
                "tenant_id": tenant_id,
                "reactivated_at": datetime.utcnow().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reactivate tenant: {str(e)}"
        )


@router.get("/tenants/{tenant_id}/activity")
async def get_tenant_activity(
    tenant_id: str,
    days: int = 7,
    admin_tenant_id: str = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get tenant activity log for the specified number of days.
    Returns API usage, errors, and other activity metrics.
    """
    try:
        from app.models.tenant import Tenant
        from datetime import datetime, timedelta
        
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Get API usage
        try:
            api_calls = db.execute(
                "SELECT COUNT(*) FROM api_usage WHERE tenant_id = ? AND timestamp >= ?",
                (tenant_id, cutoff)
            ).fetchone()[0]
            
            errors = db.execute(
                "SELECT COUNT(*) FROM api_usage WHERE tenant_id = ? AND timestamp >= ? AND status_code >= 400",
                (tenant_id, cutoff)
            ).fetchone()[0]
        except:
            api_calls = 0
            errors = 0
        
        # Get recent activity
        try:
            recent_activity = db.execute(
                """
                SELECT endpoint, method, status_code, timestamp 
                FROM api_usage 
                WHERE tenant_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 50
                """,
                (tenant_id, cutoff)
            ).fetchall()
            
            activity_list = [
                {
                    "endpoint": row[0],
                    "method": row[1],
                    "status_code": row[2],
                    "timestamp": row[3]
                }
                for row in recent_activity
            ]
        except:
            activity_list = []
        
        return {
            "success": True,
            "data": {
                "tenant_id": tenant_id,
                "period_days": days,
                "summary": {
                    "total_api_calls": api_calls,
                    "total_errors": errors,
                    "error_rate": (errors / api_calls * 100) if api_calls > 0 else 0
                },
                "recent_activity": activity_list
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant activity: {str(e)}"
        )
