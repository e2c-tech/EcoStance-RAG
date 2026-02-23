from .tasks import app as celery_app, process_file_task

__all__ = ["celery_app", "process_file_task"]
