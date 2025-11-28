"""
Scheduler Service - Handles background scheduled tasks.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
import threading
import time
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.services.quota_service import QuotaService
from app.services.metrics_service import MetricsService
from app.services.cleanup_service import CleanupService
from app.services.alerting_service import AlertingService
from app.config import QDRANT_URL, QDRANT_API_KEY
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for running scheduled background tasks."""
    
    def __init__(self):
        """Initialize scheduler service."""
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    def start(self):
        """Start the scheduler in a background thread."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop."""
        last_hourly = datetime.utcnow()
        last_daily = datetime.utcnow()
        last_monthly = datetime.utcnow()
        
        while self.running:
            try:
                now = datetime.utcnow()
                
                # Run hourly tasks (every hour)
                if (now - last_hourly).total_seconds() >= 3600:
                    self._run_hourly_tasks()
                    last_hourly = now
                
                # Run daily tasks (at 2 AM UTC)
                if now.hour == 2 and (now - last_daily).total_seconds() >= 86400:
                    self._run_daily_tasks()
                    last_daily = now
                
                # Run monthly tasks (1st of month at 3 AM UTC)
                if now.day == 1 and now.hour == 3 and (now - last_monthly).total_seconds() >= 86400:
                    self._run_monthly_tasks()
                    last_monthly = now
                
                # Sleep for 5 minutes before next check
                time.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def _run_hourly_tasks(self):
        """Run tasks that should execute every hour."""
        logger.info("Running hourly tasks")
        db = SessionLocal()
        
        try:
            # 1. Aggregate hourly metrics for all tenants
            self._aggregate_hourly_metrics(db)
            
            # 2. Check for alerts
            self._check_tenant_alerts(db)
            
        except Exception as e:
            logger.error(f"Error in hourly tasks: {e}")
        finally:
            db.close()
    
    def _run_daily_tasks(self):
        """Run tasks that should execute daily."""
        logger.info("Running daily tasks")
        db = SessionLocal()
        
        try:
            # 1. Aggregate daily metrics
            self._aggregate_daily_metrics(db)
            
            # 2. Reset daily quotas
            self._reset_daily_quotas(db)
            
            # 3. Run cleanup tasks
            cleanup_service = CleanupService(db, self.qdrant_client)
            cleanup_results = cleanup_service.run_daily_cleanup()
            logger.info(f"Daily cleanup results: {cleanup_results}")
            
            # 4. Clean up old metrics (keep 90 days)
            metrics_service = MetricsService(db)
            deleted = metrics_service.cleanup_old_metrics(retention_days=90)
            logger.info(f"Cleaned up {deleted} old metric records")
            
        except Exception as e:
            logger.error(f"Error in daily tasks: {e}")
        finally:
            db.close()
    
    def _run_monthly_tasks(self):
        """Run tasks that should execute monthly."""
        logger.info("Running monthly tasks")
        db = SessionLocal()
        
        try:
            # 1. Reset monthly quotas
            self._reset_monthly_quotas(db)
            
            # 2. Generate monthly reports (if needed)
            # self._generate_monthly_reports(db)
            
        except Exception as e:
            logger.error(f"Error in monthly tasks: {e}")
        finally:
            db.close()
    
    def _aggregate_hourly_metrics(self, db: Session):
        """Aggregate hourly metrics for all active tenants."""
        try:
            from app.models.tenant import Tenant
            
            tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
            metrics_service = MetricsService(db)
            
            now = datetime.utcnow()
            hour = now.replace(minute=0, second=0, microsecond=0)
            
            for tenant in tenants:
                try:
                    metrics_service.aggregate_hourly_metrics(tenant.id, hour)
                except Exception as e:
                    logger.error(f"Failed to aggregate hourly metrics for tenant {tenant.id}: {e}")
            
            logger.info(f"Aggregated hourly metrics for {len(tenants)} tenants")
            
        except Exception as e:
            logger.error(f"Error aggregating hourly metrics: {e}")
    
    def _aggregate_daily_metrics(self, db: Session):
        """Aggregate daily metrics for all active tenants."""
        try:
            from app.models.tenant import Tenant
            
            tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
            metrics_service = MetricsService(db)
            
            yesterday = datetime.utcnow() - timedelta(days=1)
            date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            
            for tenant in tenants:
                try:
                    metrics_service.aggregate_daily_metrics(tenant.id, date)
                except Exception as e:
                    logger.error(f"Failed to aggregate daily metrics for tenant {tenant.id}: {e}")
            
            logger.info(f"Aggregated daily metrics for {len(tenants)} tenants")
            
        except Exception as e:
            logger.error(f"Error aggregating daily metrics: {e}")
    
    def _check_tenant_alerts(self, db: Session):
        """Check alerts for all active tenants."""
        try:
            from app.models.tenant import Tenant
            
            tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
            alerting_service = AlertingService(db)
            
            total_alerts = 0
            for tenant in tenants:
                try:
                    alerts = alerting_service.check_all_alerts(tenant.id)
                    total_alerts += len(alerts)
                    
                    # Send notifications for critical alerts
                    for alert in alerts:
                        if alert["severity"] == "critical":
                            logger.warning(f"Critical alert for tenant {tenant.id}: {alert['message']}")
                            # Could send email/webhook here
                            
                except Exception as e:
                    logger.error(f"Failed to check alerts for tenant {tenant.id}: {e}")
            
            if total_alerts > 0:
                logger.info(f"Found {total_alerts} alerts across all tenants")
            
        except Exception as e:
            logger.error(f"Error checking tenant alerts: {e}")
    
    def _reset_daily_quotas(self, db: Session):
        """Reset daily quota counters for all tenants."""
        try:
            now = datetime.utcnow()
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Reset daily usage counters
            db.execute(
                """
                UPDATE tenant_quota_usage
                SET query_count = 0, api_calls_count = 0, updated_at = ?
                WHERE period_type = 'daily' AND period_start = ?
                """,
                (now, period_start)
            )
            db.commit()
            
            logger.info("Reset daily quotas for all tenants")
            
        except Exception as e:
            logger.error(f"Error resetting daily quotas: {e}")
            db.rollback()
    
    def _reset_monthly_quotas(self, db: Session):
        """Reset monthly quota counters for all tenants."""
        try:
            now = datetime.utcnow()
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Reset monthly usage counters
            db.execute(
                """
                UPDATE tenant_quota_usage
                SET query_count = 0, updated_at = ?
                WHERE period_type = 'monthly' AND period_start = ?
                """,
                (now, period_start)
            )
            db.commit()
            
            logger.info("Reset monthly quotas for all tenants")
            
        except Exception as e:
            logger.error(f"Error resetting monthly quotas: {e}")
            db.rollback()


# Global scheduler instance
_scheduler: Optional[SchedulerService] = None


def get_scheduler() -> SchedulerService:
    """Get or create scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerService()
    return _scheduler


def start_scheduler():
    """Start the background scheduler."""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler = get_scheduler()
    scheduler.stop()
