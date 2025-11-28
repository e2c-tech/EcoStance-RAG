import uuid
import time
from typing import Dict, Optional
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime
import threading

class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class JobInfo:
    job_id: str
    status: JobStatus
    file_path: str
    collection_name: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    progress_message: Optional[str] = None

class JobTracker:
    """Thread-safe job tracking service for background processing tasks."""
    
    def __init__(self):
        self._jobs: Dict[str, JobInfo] = {}
        self._lock = threading.Lock()
    
    def create_job(self, file_path: str, collection_name: str) -> str:
        """Create a new job and return its ID."""
        job_id = str(uuid.uuid4())
        
        with self._lock:
            self._jobs[job_id] = JobInfo(
                job_id=job_id,
                status=JobStatus.PENDING,
                file_path=file_path,
                collection_name=collection_name,
                created_at=datetime.now()
            )
        
        return job_id
    
    def start_job(self, job_id: str) -> bool:
        """Mark a job as started."""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].status = JobStatus.PROCESSING
                self._jobs[job_id].started_at = datetime.now()
                return True
            return False
    
    def complete_job(self, job_id: str) -> bool:
        """Mark a job as completed."""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].status = JobStatus.COMPLETED
                self._jobs[job_id].completed_at = datetime.now()
                return True
            return False
    
    def fail_job(self, job_id: str, error_message: str) -> bool:
        """Mark a job as failed with an error message."""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].status = JobStatus.FAILED
                self._jobs[job_id].completed_at = datetime.now()
                self._jobs[job_id].error_message = error_message
                return True
            return False
    
    def update_progress(self, job_id: str, message: str) -> bool:
        """Update the progress message for a job."""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].progress_message = message
                return True
            return False
    
    def get_job(self, job_id: str) -> Optional[JobInfo]:
        """Get job information by ID."""
        with self._lock:
            return self._jobs.get(job_id)
    
    def get_job_dict(self, job_id: str) -> Optional[Dict]:
        """Get job information as dictionary for JSON serialization."""
        job = self.get_job(job_id)
        if job:
            job_dict = asdict(job)
            # Convert enum to string
            job_dict['status'] = job.status.value
            # Convert datetime objects to ISO strings
            for field in ['created_at', 'started_at', 'completed_at']:
                if job_dict[field]:
                    job_dict[field] = job_dict[field].isoformat()
            return job_dict
        return None
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove jobs older than specified hours."""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        with self._lock:
            jobs_to_remove = []
            for job_id, job in self._jobs.items():
                if job.created_at.timestamp() < cutoff_time:
                    jobs_to_remove.append(job_id)
            
            for job_id in jobs_to_remove:
                del self._jobs[job_id]

# Global job tracker instance
job_tracker = JobTracker()