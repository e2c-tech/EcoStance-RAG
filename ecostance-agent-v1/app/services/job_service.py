import uuid
from typing import Dict, Optional, List
from datetime import datetime
import logging
from ..db.database import SessionLocal
from ..models.background_job import BackgroundJob, JobStatus

logger = logging.getLogger(__name__)


class JobTracker:
    """Persistent job tracking service using the database."""

    def _get_db(self):
        return SessionLocal()

    def create_job(self, file_path: str, collection_name: str, tenant_id: str = None) -> str:
        job_id = str(uuid.uuid4())
        db = self._get_db()
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
            return job_id
        finally:
            db.close()

    def start_job(self, job_id: str, db=None) -> bool:
        own_db = db is None
        if own_db:
            db = self._get_db()
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
            if own_db:
                db.close()

    def complete_job(self, job_id: str, result: Optional[Dict] = None, db=None) -> bool:
        own_db = db is None
        if own_db:
            db = self._get_db()
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
            if own_db:
                db.close()

    def fail_job(self, job_id: str, error_message: str, db=None) -> bool:
        own_db = db is None
        if own_db:
            db = self._get_db()
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
            if own_db:
                db.close()

    def update_progress(self, job_id: str, message: str, db=None) -> bool:
        own_db = db is None
        if own_db:
            db = self._get_db()
        try:
            job = db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).first()
            if job:
                job.progress_message = message
                current_logs = job.logs if job.logs is not None else []
                new_logs = list(current_logs)
                new_logs.append({"timestamp": datetime.now().isoformat(), "message": message})
                job.logs = new_logs
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update progress for job {job_id} in DB: {e}")
            db.rollback()
            return False
        finally:
            if own_db:
                db.close()

    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        db = self._get_db()
        try:
            return db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).first()
        finally:
            db.close()

    def get_job_dict(self, job_id: str) -> Optional[Dict]:
        db = self._get_db()
        try:
            job = db.query(BackgroundJob).filter(BackgroundJob.job_id == job_id).first()
            return job.to_dict() if job else None
        finally:
            db.close()

    def list_jobs(self, tenant_id: str = None, limit: int = 100) -> List[Dict]:
        db = self._get_db()
        try:
            query = db.query(BackgroundJob)
            if tenant_id:
                query = query.filter(BackgroundJob.tenant_id == tenant_id)
            jobs = query.order_by(BackgroundJob.created_at.desc()).limit(limit).all()
            return [job.to_dict() for job in jobs]
        finally:
            db.close()

    def get_recent_jobs(self, limit: int = 10) -> List[Dict]:
        return self.list_jobs(limit=limit)


# Global job tracker instance
job_tracker = JobTracker()
