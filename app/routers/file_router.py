"""
File Management Router with tenant-based access control.
Provides endpoints for listing, downloading, and deleting tenant files.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from typing import List, Dict, Any
import os
import logging

from ..services.file_access_service import get_file_access_service
from ..auth.dependencies import get_current_user, get_tenant_id
from ..auth.rbac import RBACService
from ..auth.permissions import Permission
from ..services.audit_service import AuditService
from ..db.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/files/")
async def list_files(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    List all files for the authenticated tenant.
    
    Requires: FILE_VIEW permission
    
    Returns:
        List of file information dictionaries
    """
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.FILE_VIEW)
    try:
        file_service = get_file_access_service()
        files = file_service.list_tenant_files(tenant_id)
        
        logger.info(f"Listed {len(files)} files for tenant {tenant_id}")
        
        return files
        
    except Exception as e:
        logger.error(f"Error listing files for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{filename}")
async def download_file(
    filename: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download a file. Only accessible by the owning tenant.
    
    Requires: FILE_DOWNLOAD permission
    
    Args:
        filename: Name of file to download
        
    Returns:
        File response with the requested file
    """
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.FILE_DOWNLOAD)
    
    try:
        file_service = get_file_access_service()
        
        # Get safe file path
        file_path = file_service.get_safe_file_path(tenant_id, filename)
        
        # Verify file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Verify tenant owns file
        if not file_service.verify_tenant_owns_file(tenant_id, file_path):
            logger.warning(
                f"Access denied: Tenant {tenant_id} attempted to download "
                f"file they don't own: {filename}"
            )
            raise HTTPException(
                status_code=403,
                detail="Access denied: You don't have permission to access this file"
            )
        
        logger.info(f"File downloaded by tenant {tenant_id}: {filename}")
        
        # Log data access
        audit = AuditService(db)
        audit.log_data_access(
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type="file",
            resource_id=filename,
            action="download",
            request=request
        )
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{filename}")
async def delete_file(
    filename: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a file. Only accessible by the owning tenant.
    
    Requires: FILE_DELETE permission
    
    Args:
        filename: Name of file to delete
        
    Returns:
        Success message
    """
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.FILE_DELETE)
    try:
        file_service = get_file_access_service()
        
        success = file_service.delete_tenant_file(tenant_id, filename)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="File not found or could not be deleted"
            )
        
        logger.info(f"File deleted by tenant {tenant_id}: {filename}")
        
        # Log successful deletion
        audit = AuditService(db)
        audit.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action="delete_file",
            resource_type="file",
            resource_id=filename,
            status="success",
            request=request
        )
        
        return {
            "message": f"File '{filename}' deleted successfully",
            "tenant_id": tenant_id,
            "filename": filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/storage/usage")
async def get_storage_usage(tenant_id: str = Depends(get_tenant_id)):
    """
    Get storage usage statistics for the authenticated tenant.
    
    Returns:
        Storage usage information
    """
    try:
        file_service = get_file_access_service()
        usage = file_service.get_tenant_storage_usage(tenant_id)
        
        logger.info(
            f"Storage usage for tenant {tenant_id}: "
            f"{usage['total_mb']} MB ({usage['total_files']} files)"
        )
        
        return usage
        
    except Exception as e:
        logger.error(f"Error getting storage usage for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/storage/check-quota")
async def check_storage_quota(
    file_size_mb: float,
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Check if uploading a file would exceed storage quota.
    
    Args:
        file_size_mb: Size of file to check in megabytes
        
    Returns:
        Quota check results
    """
    try:
        file_service = get_file_access_service()
        
        # TODO: Get quota from tenant settings in database
        # For now, use default quota of 10GB
        default_quota_mb = 10000
        
        file_size_bytes = int(file_size_mb * 1024 * 1024)
        
        quota_check = file_service.check_storage_quota(
            tenant_id,
            default_quota_mb,
            file_size_bytes
        )
        
        logger.info(
            f"Quota check for tenant {tenant_id}: "
            f"{quota_check['usage_percent']}% used"
        )
        
        return quota_check
        
    except Exception as e:
        logger.error(f"Error checking quota for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/")
async def delete_all_files(tenant_id: str = Depends(get_tenant_id)):
    """
    Delete all files for the authenticated tenant.
    Use with caution!
    
    Returns:
        Number of files deleted
    """
    try:
        file_service = get_file_access_service()
        
        count = file_service.delete_all_tenant_files(tenant_id)
        
        logger.warning(f"All files deleted for tenant {tenant_id}: {count} files")
        
        return {
            "message": f"Deleted {count} file(s)",
            "tenant_id": tenant_id,
            "count": count
        }
        
    except Exception as e:
        logger.error(f"Error deleting all files for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
