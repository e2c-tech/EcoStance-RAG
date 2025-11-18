from fastapi import APIRouter, Form, HTTPException, BackgroundTasks
import os

from ..services.data_processing_service import process_and_upload_file
from ..services.job_service import job_tracker

router = APIRouter()

def background_process_file(job_id: str, file_path: str, collection_name: str):
    """Background task function for file processing."""
    try:
        job_tracker.start_job(job_id)
        process_and_upload_file(file_path, collection_name, job_id)
    except Exception as e:
        job_tracker.fail_job(job_id, str(e))

@router.post("/upload-to-qdrant/")
async def upload_to_qdrant(
    background_tasks: BackgroundTasks,
    file_path: str = Form(...),
    collection_name: str = Form("default_collection"),
):
    """
    API endpoint to take a path to an already uploaded file, process it 
    through the full pipeline, and upload the results to a specified
    Qdrant collection.
    
    This endpoint now processes files in the background and returns immediately
    with a job ID for tracking progress.
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found at the specified path.")

    # Create a job for tracking
    job_id = job_tracker.create_job(file_path, collection_name)
    
    # Add the processing task to background tasks
    background_tasks.add_task(background_process_file, job_id, file_path, collection_name)

    return {
        "message": f"Processing started for '{os.path.basename(file_path)}' in collection '{collection_name}'.",
        "job_id": job_id,
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
    jobs = []
    for job_id in job_tracker._jobs.keys():
        job_info = job_tracker.get_job_dict(job_id)
        if job_info:
            jobs.append(job_info)
    
    return {
        "total_jobs": len(jobs),
        "jobs": jobs
    }
