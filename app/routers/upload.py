from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
import os
import logging

from ..services.file_upload_service import save_upload_file
from ..services.file_access_service import get_file_access_service
from ..auth.dependencies import get_tenant_id, get_current_user
from ..auth.rbac import RBACService
from ..auth.permissions import Permission
from ..services.audit_service import AuditService
from ..db.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload/")
def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accepts a file upload, saves it to a tenant-specific directory,
    and returns the path to the saved file. This endpoint ONLY handles the upload.
    
    Files are stored in: uploads/{tenant_id}/{filename}
    
    Includes storage quota checking to prevent exceeding limits.
    
    Requires: FILE_UPLOAD permission
    """
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.FILE_UPLOAD)
    
    try:
        file_service = get_file_access_service()
        
        # Get file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        # TODO: Get quota from tenant settings in database
        # For now, use default quota of 10GB
        default_quota_mb = 10000
        
        # Check storage quota
        quota_check = file_service.check_storage_quota(
            tenant_id,
            default_quota_mb,
            file_size
        )
        
        if not quota_check['within_quota']:
            logger.warning(
                f"Upload rejected for tenant {tenant_id}: quota exceeded "
                f"({quota_check['usage_percent']}% used)"
            )
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "Storage quota exceeded",
                    "quota_mb": quota_check['quota_mb'],
                    "current_usage_mb": quota_check['current_usage_mb'],
                    "available_mb": quota_check['available_mb'],
                    "usage_percent": quota_check['usage_percent']
                }
            )
        
        # Create tenant-specific upload directory
        upload_dir = file_service.ensure_tenant_directory(tenant_id)
        file_location = os.path.join(upload_dir, file.filename)
        
        # Save file
        save_upload_file(upload_file=file, destination=file_location)
        
        # Get updated usage
        usage = file_service.get_tenant_storage_usage(tenant_id)
        
        logger.info(
            f"File uploaded for tenant {tenant_id}: {file.filename} "
            f"({round(file_size / (1024 * 1024), 2)} MB)"
        )
        
        # Log successful upload (non-blocking)
        try:
            audit = AuditService(db)
            audit.log_action(
                tenant_id=tenant_id,
                user_id=user_id,
                action="upload_file",
                resource_type="file",
                resource_id=file.filename,
                details={
                    "filename": file.filename,
                    "size_mb": round(file_size / (1024 * 1024), 2)
                },
                status="success",
                request=request
            )
        except Exception as audit_error:
            logger.warning(f"Failed to log audit for file upload: {audit_error}")
        
        return {
            "message": "File uploaded successfully. Use the returned path to process the file.",
            "file_path": file_location,
            "tenant_id": tenant_id,
            "filename": file.filename,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "storage_usage": {
                "total_files": usage['total_files'],
                "total_mb": usage['total_mb'],
                "quota_mb": default_quota_mb,
                "usage_percent": round((usage['total_mb'] / default_quota_mb) * 100, 2)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed for tenant {tenant_id}: {e}")
        
        # Log failure (non-blocking)
        try:
            audit = AuditService(db)
            audit.log_action(
                tenant_id=tenant_id,
                user_id=user_id,
                action="upload_file",
                resource_type="file",
                details={"filename": file.filename},
                status="failure",
                error_message=str(e),
                request=request
            )
        except Exception as audit_error:
            logger.warning(f"Failed to log audit for failed upload: {audit_error}")
        
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
