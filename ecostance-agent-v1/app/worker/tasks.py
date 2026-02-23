from celery import Celery
import os
import asyncio
import logging
from ..config import REDIS_URL

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CeleryWorker")

# Initialize Celery
app = Celery(
    "ecostance_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Optional: Celery Configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1, # Recommended for long-running tasks like processing 19k chunks
)

@app.task(name="app.worker.tasks.process_file_task")
def process_file_task(job_id: str, file_path: str, collection_name: str, tenant_id: str):
    """
    Celery task to process a file and upload to Qdrant.
    This wraps the async process_file_intelligently function.
    """
    from ..services.multilingual_integration_service import process_file_intelligently
    from ..services.job_service import job_tracker
    
    logger.info(f"Starting Celery task for job {job_id} (File: {file_path})")
    
    try:
        # Mark job as started
        job_tracker.start_job(job_id)
        
        # Run the async processing function
        # We use asyncio.run to bridge the sync Celery worker with async app logic
        asyncio.run(process_file_intelligently(
            file_path=file_path,
            collection_name=collection_name,
            tenant_id=tenant_id,
            job_id=job_id
        ))
        
        logger.info(f"✓ Celery task completed for job {job_id}")
        return {"status": "success", "job_id": job_id}
        
    except Exception as e:
        logger.error(f"✗ Celery task failed for job {job_id}: {str(e)}")
        job_tracker.fail_job(job_id, str(e))
        return {"status": "error", "job_id": job_id, "error": str(e)}
