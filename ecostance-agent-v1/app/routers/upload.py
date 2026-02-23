from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, Form, BackgroundTasks
import os
import logging
from typing import Optional

from ..services.file_upload_service import save_upload_file_async
from ..services.file_access_service import get_file_access_service
from ..auth.dependencies import get_tenant_id, get_current_user
from ..auth.rbac import RBACService
from ..auth.permissions import Permission
from ..services.audit_service import AuditService
from ..db.database import get_db
from sqlalchemy.orm import Session

# Import processing logic from qdrant_upload
from .qdrant_upload import background_process_file
from ..services.job_service import job_tracker
from ..services.qdrant_service import get_qdrant_client
from ..services.tenant_service import get_tenant_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload/")
async def upload_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    process_now: bool = Form(False),
    kb_name: str = Form("default"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accepts a file upload, saves it to a tenant-specific directory.
    
    If process_now is True, it automatically starts the Qdrant processing pipeline
    and returns a job_id for tracking both upload and processing.
    
    Files are stored in: uploads/{tenant_id}/{filename}
    """
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.FILE_UPLOAD)
    
    try:
        file_service = get_file_access_service()
        
        # Get file size safely
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        # Get quota (default 10GB if not found)
        from ..services.quota_service import QuotaService
        quota_service = QuotaService(db)
        quotas = quota_service.get_tenant_quotas(tenant_id)
        max_storage_bytes = quotas.get("max_storage_bytes", 10 * 1024 * 1024 * 1024)
        
        # Check storage quota
        quota_check = file_service.check_storage_quota(
            tenant_id,
            max_storage_bytes / (1024 * 1024),
            file_size
        )
        
        if not quota_check['within_quota']:
            raise HTTPException(
                status_code=413,
                detail="Storage quota exceeded"
            )
        
        # Create tenant-specific upload directory
        upload_dir = file_service.ensure_tenant_directory(tenant_id)
        file_location = os.path.join(upload_dir, file.filename)
        
        # Save file asynchronously
        await save_upload_file_async(upload_file=file, destination=file_location)
        
        # If processing is requested, start the background job
        job_id = None
        if process_now:
            # Check KB_UPLOAD permission if processing is requested
            rbac.require_permission(tenant_id, user_id, Permission.KB_UPLOAD)
            
            # Generate collection name
            qdrant_client = get_qdrant_client()
            tenant_service = get_tenant_service(qdrant_client)
            collection_name = tenant_service.get_collection_name(tenant_id, kb_name)
            
            # Ensure collection exists
            tenant_service.create_tenant_collection(tenant_id, kb_name)
            
            # Create a job for tracking
            job_id = job_tracker.create_job(file_location, collection_name, tenant_id=tenant_id)
            job_tracker.update_progress(job_id, "Upload complete. Starting processing...")
            
            # Add processing task
            background_tasks.add_task(
                background_process_file, 
                job_id, 
                file_location, 
                collection_name,
                tenant_id
            )
        
        # Log successful upload
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
                    "size_mb": round(file_size / (1024 * 1024), 2),
                    "processed": process_now,
                    "job_id": job_id
                },
                status="success",
                request=request
            )
        except Exception as audit_error:
            logger.warning(f"Failed to log audit for file upload: {audit_error}")
        
        return {
            "message": "File uploaded successfully" + (". Processing started." if process_now else "."),
            "file_path": file_location,
            "filename": file.filename,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "job_id": job_id,
            "status_url": f"/api/v1/processing-status/{job_id}" if job_id else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
