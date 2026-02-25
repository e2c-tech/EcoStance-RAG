from sqlalchemy import Column, String, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
import enum
from ..db.database import Base

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    job_id = Column(String(255), primary_key=True, index=True)
    tenant_id = Column(String(255), index=True, nullable=True)
    status = Column(String(50), default=JobStatus.PENDING)
    file_path = Column(String(512))
    collection_name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String(1024), nullable=True)
    progress_message = Column(String(1024), nullable=True)
    logs = Column(JSON, nullable=True, default=list)
    result_data = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "file_path": self.file_path,
            "collection_name": self.collection_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "progress_message": self.progress_message,
            "logs": self.logs if self.logs is not None else [],
            "result_data": self.result_data
        }
