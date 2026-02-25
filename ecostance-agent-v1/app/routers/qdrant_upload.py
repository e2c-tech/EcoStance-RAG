from fastapi import APIRouter, Form, HTTPException, BackgroundTasks, Depends, Request
import os

from ..services.multilingual_integration_service import process_file_intelligently
from ..services.job_service import job_tracker
from ..worker.tasks import process_file_task
from ..services.qdrant_service import get_qdrant_client
from ..services.tenant_service import get_tenant_service
from ..auth.dependencies import get_current_user
from ..auth.rbac import RBACService
from ..auth.permissions import Permission
from ..services.audit_service import AuditService
from ..db.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()

async def background_process_file(job_id: str, file_path: str, collection_name: str, tenant_id: str):
    """Background task function for file processing with tenant context and multilingual support."""
    try:
        job_tracker.start_job(job_id)
        # Use intelligent processing that automatically selects multilingual or legacy pipeline
        await process_file_intelligently(
            file_path=file_path, 
            collection_name=collection_name, 
            tenant_id=tenant_id,
            job_id=job_id
        )
    except Exception as e:
        job_tracker.fail_job(job_id, str(e))

@router.post("/upload-to-qdrant/")
async def upload_to_qdrant(
    background_tasks: BackgroundTasks,
    file_path: str = Form(...),
    kb_name: str = Form("default"),
    request: Request = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    API endpoint to take a path to an already uploaded file, process it 
    through the full pipeline, and upload the results to a tenant-specific
    Qdrant collection.
    
    This endpoint now processes files in the background and returns immediately
    with a job ID for tracking progress.
    
    The collection name is automatically generated based on tenant_id and kb_name.
    
    Requires: KB_UPLOAD permission
    """
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.KB_UPLOAD)
    
    # Check if the file path is just a filename, and construct correct tenant upload path
    if not os.path.exists(file_path):
        from ..services.file_access_service import get_file_access_service
        file_service = get_file_access_service()
        resolved_path = file_service.get_safe_file_path(tenant_id, os.path.basename(file_path))
        if os.path.exists(resolved_path):
            file_path = resolved_path
        else:
            raise HTTPException(status_code=404, detail="File not found at the specified path.")

    # Generate tenant-specific collection name
    qdrant_client = get_qdrant_client()
    tenant_service = get_tenant_service(qdrant_client)
    collection_name = tenant_service.get_collection_name(tenant_id, kb_name)
    
    # Ensure collection exists
    try:
        tenant_service.create_tenant_collection(tenant_id, kb_name)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create collection: {str(e)}"
        )

    # Create a job for tracking
    job_id = job_tracker.create_job(file_path, collection_name, tenant_id=tenant_id)
    
    # Add the processing task to Celery
    process_file_task.delay(
        job_id, 
        file_path, 
        collection_name,
        tenant_id
    )
    
    # Log action (non-blocking)
    try:
        audit = AuditService(db)
        audit.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action="process_file_to_kb",
            resource_type="knowledge_base",
            resource_id=kb_name,
            details={
                "file_path": os.path.basename(file_path),
                "job_id": job_id,
                "collection_name": collection_name
            },
            status="success",
            request=request
        )
    except Exception as audit_error:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to log audit for file processing: {audit_error}")

    return {
        "message": f"Processing started for '{os.path.basename(file_path)}' in knowledge base '{kb_name}'.",
        "job_id": job_id,
        "tenant_id": tenant_id,
        "kb_name": kb_name,
        "collection_name": collection_name,
        "status_url": f"/api/v1/processing-status/{job_id}"
    }

@router.get("/processing-status/{job_id}")
async def get_processing_status(job_id: str):
    """
    Get the current status of a background processing job.
    """
    job_info = job_tracker.get_job_dict(job_id)
    
    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found.")
    
    return job_info

@router.get("/jobs/")
async def list_all_jobs():
    """
    List all current jobs (for debugging/monitoring).
    """
    jobs = job_tracker.get_recent_jobs(limit=50)
    
    return {
        "total_jobs": len(jobs),
        "jobs": jobs
    }
