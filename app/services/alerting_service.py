"""
Alerting Service - Monitors tenant metrics and triggers alerts.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

from app.models.tenant import Tenant
from app.services.quota_service import QuotaService
from app.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)


class AlertingService:
    """Service for monitoring and alerting on tenant metrics."""
    
    # Alert thresholds
    QUOTA_WARNING_THRESHOLD = 80  # Alert at 80% usage
    QUOTA_CRITICAL_THRESHOLD = 95  # Critical alert at 95% usage
    HIGH_ERROR_RATE_THRESHOLD = 5  # Alert if error rate > 5%
    SLOW_QUERY_THRESHOLD = 5000  # Alert if avg query time > 5 seconds
    
    def __init__(self, db: Session):
        """Initialize alerting service with database session."""
        self.db = db
        self.quota_service = QuotaService(db)
        self.metrics_service = MetricsService(db)
    
    def check_quota_alerts(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        Check if tenant is approaching quota limits.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            List of alert dictionaries
        """
        alerts = []
        quota_status = self.quota_service.get_quota_status(tenant_id)
        
        # Check daily query quota
        daily_queries = quota_status["daily_usage"]["queries"]
        if daily_queries["percentage"] >= self.QUOTA_CRITICAL_THRESHOLD:
            alerts.append({
                "type": "quota_critical",
                "resource": "daily_queries",
                "message": f"Daily query quota at {daily_queries['percentage']:.1f}% ({daily_queries['current']}/{daily_queries['limit']})",
                "severity": "critical",
                "current": daily_queries["current"],
                "limit": daily_queries["limit"],
                "percentage": daily_queries["percentage"]
            })
        elif daily_queries["percentage"] >= self.QUOTA_WARNING_THRESHOLD:
            alerts.append({
                "type": "quota_warning",
                "resource": "daily_queries",
                "message": f"Daily query quota at {daily_queries['percentage']:.1f}% ({daily_queries['current']}/{daily_queries['limit']})",
                "severity": "warning",
                "current": daily_queries["current"],
                "limit": daily_queries["limit"],
                "percentage": daily_queries["percentage"]
            })
        
        # Check monthly query quota
        monthly_queries = quota_status["monthly_usage"]["queries"]
        if monthly_queries["percentage"] >= self.QUOTA_CRITICAL_THRESHOLD:
            alerts.append({
                "type": "quota_critical",
                "resource": "monthly_queries",
                "message": f"Monthly query quota at {monthly_queries['percentage']:.1f}% ({monthly_queries['current']}/{monthly_queries['limit']})",
                "severity": "critical",
                "current": monthly_queries["current"],
                "limit": monthly_queries["limit"],
                "percentage": monthly_queries["percentage"]
            })
        elif monthly_queries["percentage"] >= self.QUOTA_WARNING_THRESHOLD:
            alerts.append({
                "type": "quota_warning",
                "resource": "monthly_queries",
                "message": f"Monthly query quota at {monthly_queries['percentage']:.1f}% ({monthly_queries['current']}/{monthly_queries['limit']})",
                "severity": "warning",
                "current": monthly_queries["current"],
                "limit": monthly_queries["limit"],
                "percentage": monthly_queries["percentage"]
            })
        
        # Check storage quota
        storage = quota_status["storage"]
        if storage["percentage"] >= self.QUOTA_CRITICAL_THRESHOLD:
            alerts.append({
                "type": "quota_critical",
                "resource": "storage",
                "message": f"Storage quota at {storage['percentage']:.1f}% ({storage['current_gb']:.2f}GB/{storage['limit_gb']:.2f}GB)",
                "severity": "critical",
                "current": storage["current_gb"],
                "limit": storage["limit_gb"],
                "percentage": storage["percentage"]
            })
        elif storage["percentage"] >= self.QUOTA_WARNING_THRESHOLD:
            alerts.append({
                "type": "quota_warning",
                "resource": "storage",
                "message": f"Storage quota at {storage['percentage']:.1f}% ({storage['current_gb']:.2f}GB/{storage['limit_gb']:.2f}GB)",
                "severity": "warning",
                "current": storage["current_gb"],
                "limit": storage["limit_gb"],
                "percentage": storage["percentage"]
            })
        
        # Check document quota
        documents = quota_status["documents"]
        if documents["percentage"] >= self.QUOTA_CRITICAL_THRESHOLD:
            alerts.append({
                "type": "quota_critical",
                "resource": "documents",
                "message": f"Document quota at {documents['percentage']:.1f}% ({documents['current']}/{documents['limit']})",
                "severity": "critical",
                "current": documents["current"],
                "limit": documents["limit"],
                "percentage": documents["percentage"]
            })
        elif documents["percentage"] >= self.QUOTA_WARNING_THRESHOLD:
            alerts.append({
                "type": "quota_warning",
                "resource": "documents",
                "message": f"Document quota at {documents['percentage']:.1f}% ({documents['current']}/{documents['limit']})",
                "severity": "warning",
                "current": documents["current"],
                "limit": documents["limit"],
                "percentage": documents["percentage"]
            })
        
        return alerts
    
    def check_error_rate_alerts(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        Check if tenant has high error rates.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            List of alert dictionaries
        """
        alerts = []
        error_metrics = self.metrics_service.get_error_rate_metrics(tenant_id, days=1)
        
        if not error_metrics:
            return alerts
        
        # Check most recent error rate
        latest = error_metrics[-1] if error_metrics else None
        if latest:
            if latest["api_error_rate"] > self.HIGH_ERROR_RATE_THRESHOLD:
                alerts.append({
                    "type": "high_error_rate",
                    "resource": "api",
                    "message": f"High API error rate: {latest['api_error_rate']:.1f}%",
                    "severity": "warning",
                    "error_rate": latest["api_error_rate"],
                    "threshold": self.HIGH_ERROR_RATE_THRESHOLD
                })
            
            if latest["query_error_rate"] > self.HIGH_ERROR_RATE_THRESHOLD:
                alerts.append({
                    "type": "high_error_rate",
                    "resource": "queries",
                    "message": f"High query error rate: {latest['query_error_rate']:.1f}%",
                    "severity": "warning",
                    "error_rate": latest["query_error_rate"],
                    "threshold": self.HIGH_ERROR_RATE_THRESHOLD
                })
        
        return alerts
    
    def check_performance_alerts(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        Check if tenant has performance issues.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            List of alert dictionaries
        """
        alerts = []
        perf_metrics = self.metrics_service.get_query_performance_metrics(tenant_id, days=1)
        
        if perf_metrics["avg_query_time_ms"] > self.SLOW_QUERY_THRESHOLD:
            alerts.append({
                "type": "slow_queries",
                "resource": "query_performance",
                "message": f"Slow query performance: {perf_metrics['avg_query_time_ms']:.0f}ms average",
                "severity": "warning",
                "avg_time_ms": perf_metrics["avg_query_time_ms"],
                "threshold_ms": self.SLOW_QUERY_THRESHOLD
            })
        
        return alerts
    
    def check_all_alerts(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        Check all alert conditions for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            List of all active alerts
        """
        all_alerts = []
        
        # Check quota alerts
        all_alerts.extend(self.check_quota_alerts(tenant_id))
        
        # Check error rate alerts
        all_alerts.extend(self.check_error_rate_alerts(tenant_id))
        
        # Check performance alerts
        all_alerts.extend(self.check_performance_alerts(tenant_id))
        
        # Store alerts in database
        for alert in all_alerts:
            self._store_alert(tenant_id, alert)
        
        return all_alerts
    
    def _store_alert(self, tenant_id: str, alert: Dict[str, Any]) -> None:
        """
        Store alert in database.
        
        Args:
            tenant_id: Tenant identifier
            alert: Alert dictionary
        """
        try:
            self.db.execute(
                """
                INSERT INTO alert_history 
                    (tenant_id, alert_type, message, severity, metric_value, threshold_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    alert["type"],
                    alert["message"],
                    alert["severity"],
                    alert.get("current") or alert.get("error_rate") or alert.get("avg_time_ms"),
                    alert.get("limit") or alert.get("threshold") or alert.get("threshold_ms")
                )
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to store alert: {e}")
    
    def send_email_alert(
        self,
        tenant_id: str,
        alert: Dict[str, Any],
        smtp_config: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send alert via email.
        
        Args:
            tenant_id: Tenant identifier
            alert: Alert dictionary
            smtp_config: SMTP configuration (host, port, username, password)
            
        Returns:
            True if email sent successfully
        """
        # Get tenant email
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant or not tenant.email:
            logger.warning(f"No email address for tenant {tenant_id}")
            return False
        
        if not smtp_config:
            logger.warning("No SMTP configuration provided")
            return False
        
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = smtp_config.get('from_email', 'alerts@example.com')
            msg['To'] = tenant.email
            msg['Subject'] = f"[{alert['severity'].upper()}] {alert['type'].replace('_', ' ').title()}"
            
            body = f"""
            Alert for {tenant.name}
            
            Type: {alert['type']}
            Severity: {alert['severity']}
            Message: {alert['message']}
            
            Time: {datetime.utcnow().isoformat()}
            
            Please review your usage and take appropriate action.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_config['host'], smtp_config.get('port', 587)) as server:
                server.starttls()
                if smtp_config.get('username') and smtp_config.get('password'):
                    server.login(smtp_config['username'], smtp_config['password'])
                server.send_message(msg)
            
            logger.info(f"Sent email alert to {tenant.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def send_webhook_alert(
        self,
        tenant_id: str,
        alert: Dict[str, Any],
        webhook_url: str
    ) -> bool:
        """
        Send alert via webhook.
        
        Args:
            tenant_id: Tenant identifier
            alert: Alert dictionary
            webhook_url: Webhook URL to POST to
            
        Returns:
            True if webhook sent successfully
        """
        try:
            payload = {
                "tenant_id": tenant_id,
                "alert": alert,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            logger.info(f"Sent webhook alert to {webhook_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False
    
    def get_alert_history(
        self,
        tenant_id: str,
        days: int = 7,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get alert history for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            days: Number of days to look back
            severity: Filter by severity ('info', 'warning', 'critical')
            
        Returns:
            List of alert history records
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = """
            SELECT alert_type, message, severity, metric_value, threshold_value, 
                   triggered_at, is_resolved, resolved_at
            FROM alert_history
            WHERE tenant_id = ? AND triggered_at >= ?
        """
        params = [tenant_id, cutoff_date]
        
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        
        query += " ORDER BY triggered_at DESC"
        
        results = self.db.execute(query, params).fetchall()
        
        return [
            {
                "alert_type": row[0],
                "message": row[1],
                "severity": row[2],
                "metric_value": row[3],
                "threshold_value": row[4],
                "triggered_at": row[5],
                "is_resolved": bool(row[6]),
                "resolved_at": row[7]
            }
            for row in results
        ]
    
    def resolve_alert(self, alert_id: int) -> bool:
        """
        Mark an alert as resolved.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            True if resolved successfully
        """
        try:
            self.db.execute(
                """
                UPDATE alert_history
                SET is_resolved = TRUE, resolved_at = ?
                WHERE id = ?
                """,
                (datetime.utcnow(), alert_id)
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
            return False
