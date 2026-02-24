from celery import Celery
import os
from app.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

# Initialize Celery
celery_app = Celery(
    "ecostance_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Optional configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600, # 1 hour max
)

# Auto-discover tasks from the tasks module
celery_app.autodiscover_tasks(['app.worker'])
