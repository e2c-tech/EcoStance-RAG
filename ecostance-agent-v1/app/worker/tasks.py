import asyncio
import logging
from celery import Celery
import os

# Use sc-ai-agent's Celery app via shared Redis
celery_app = Celery(
    "ecostance_tasks",
    broker=os.getenv("REDIS_URL", "redis://sc-ai-agent-redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://sc-ai-agent-redis:6379/0"),
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CeleryWorker")

@celery_app.task(name="app.worker.tasks.process_file_task")
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
