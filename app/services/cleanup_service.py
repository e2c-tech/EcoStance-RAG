import asyncio
import logging
from .job_service import job_tracker

logger = logging.getLogger(__name__)

class CleanupService:
    """Service to periodically clean up old jobs and temporary files."""
    
    def __init__(self, cleanup_interval_hours: int = 1, max_job_age_hours: int = 24):
        self.cleanup_interval_hours = cleanup_interval_hours
        self.max_job_age_hours = max_job_age_hours
        self._running = False
        self._task = None
    
    async def start(self):
        """Start the cleanup service."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"Cleanup service started. Will run every {self.cleanup_interval_hours} hours.")
    
    async def stop(self):
        """Stop the cleanup service."""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Cleanup service stopped.")
    
    async def _cleanup_loop(self):
        """Main cleanup loop."""
        while self._running:
            try:
                await self._perform_cleanup()
                # Wait for the next cleanup interval
                await asyncio.sleep(self.cleanup_interval_hours * 3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(300)  # 5 minutes
    
    async def _perform_cleanup(self):
        """Perform the actual cleanup operations."""
        logger.info("Starting periodic cleanup...")
        
        # Clean up old jobs
        initial_job_count = len(job_tracker._jobs)
        job_tracker.cleanup_old_jobs(self.max_job_age_hours)
        final_job_count = len(job_tracker._jobs)
        
        removed_jobs = initial_job_count - final_job_count
        if removed_jobs > 0:
            logger.info(f"Cleaned up {removed_jobs} old jobs.")
        
        logger.info("Periodic cleanup completed.")

# Global cleanup service instance
cleanup_service = CleanupService()