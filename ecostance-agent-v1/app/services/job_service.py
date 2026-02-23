import uuid
from typing import Dict, Optional, List, Any
from datetime import datetime
import logging
from ..db.database import SessionLocal
from ..models.background_job import BackgroundJob, JobStatus

logger = logging.getLogger(__name__)

class JobTracker:
    """Persistent job tracking service using the database."""
    
    def create_job(self, file_path: str, collection_name: str, tenant_id: str = None) -> str:
        """Create a new job in the database and return its ID."""
        job_id = str(uuid.uuid4())
        
        db = SessionLocal()
        try:
            job = BackgroundJob(
                job_id=job_id,
                tenant_id=tenant_id,
                status=JobStatus.PENDING,
                file_path=file_path,
                collection_name=collection_name
            )
            db.add(job)
            db.commit()
            return job_id
        except Exception as e:
            logger.error(f"Failed to create job in DB: {e}")
            db.rollback()
            return job_id # Return the ID anyway to avoid breaking frontend completely
        finally:
            db.close()
    
    def start_job(self, job_id: str) -> bool:
        """Mark a job as started in the database."""
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).first()
            if job:
                job.status = JobStatus.PROCESSING
                job.started_at = datetime.now()
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to start job {job_id} in DB: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def complete_job(self, job_id: str, result: Optional[Dict] = None) -> bool:
        """Mark a job as completed in the database."""
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).first()
            if job:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now()
                if result:
                    job.result_data = result
                    if "collection_name" in result:
                        job.collection_name = result["collection_name"]
                    if "message" in result:
                        job.progress_message = result.get("message")
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to complete job {job_id} in DB: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def fail_job(self, job_id: str, error_message: str) -> bool:
        """Mark a job as failed in the database."""
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now()
                job.error_message = error_message
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to fail job {job_id} in DB: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def update_progress(self, job_id: str, message: str) -> bool:
        """Update the progress message for a job in the database."""
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).first()
            if job:
                job.progress_message = message
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update progress for job {job_id} in DB: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        """Get job information from the database."""
        db = SessionLocal()
        try:
            return db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).first()
        finally:
            db.close() # Note: The object will be detached after close
    
    def get_job_dict(self, job_id: str) -> Optional[Dict]:
        """Get job information as dictionary for JSON serialization."""
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).first()
            if job:
                return job.to_dict()
            return None
        finally:
            db.close()

    def list_jobs(self, tenant_id: str = None, limit: int = 100) -> List[Dict]:
        """List all jobs from the database, optionally filtered by tenant."""
        db = SessionLocal()
        try:
            query = db.query(BackgroundJob)
            if tenant_id:
                query = query.filter(BackgroundJob.tenant_id == tenant_id)
            
            jobs = query.order_by(BackgroundJob.created_at.desc()).limit(limit).all()
            return [job.to_dict() for job in jobs]
        finally:
            db.close()

    def get_recent_jobs(self, limit: int = 10) -> List[Dict]:
        """Get the most recent jobs from all tenants."""
        return self.list_jobs(limit=limit)

# Global job tracker instance
job_tracker = JobTracker()