"""
Metrics Service - Collects and aggregates tenant metrics for monitoring.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, text
import statistics

from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for collecting and aggregating tenant metrics."""
    
    def __init__(self, db: Session):
        """Initialize metrics service with database session."""
        self.db = db
    
    def record_query_metric(
        self,
        tenant_id: str,
        query_time_ms: float,
        success: bool,
        endpoint: str = "query"
    ) -> None:
        """
        Record a query execution metric.
        
        Args:
            tenant_id: Tenant identifier
            query_time_ms: Query execution time in milliseconds
            success: Whether the query succeeded
            endpoint: API endpoint name
        """
        # This would typically be stored in a time-series database
        # For now, we'll aggregate it immediately
        logger.debug(f"Query metric: tenant={tenant_id}, time={query_time_ms}ms, success={success}")
    
    def record_api_call(
        self,
        tenant_id: str,
        endpoint: str,
        method: str,
        response_time_ms: float,
        status_code: int
    ) -> None:
        """
        Record an API call metric.
        
        Args:
            tenant_id: Tenant identifier
            endpoint: API endpoint path
            method: HTTP method
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
        """
        success = 200 <= status_code < 300
        logger.debug(f"API call: tenant={tenant_id}, endpoint={endpoint}, time={response_time_ms}ms, status={status_code}")
    
    def aggregate_hourly_metrics(self, tenant_id: str, hour: datetime) -> None:
        """
        Aggregate metrics for a specific hour.
        
        Args:
            tenant_id: Tenant identifier
            hour: Hour to aggregate (should be start of hour)
        """
        period_start = hour.replace(minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(hours=1)
        
        # Get usage data from api_usage table
        usage_stats = self.db.execute(
            text("""
            SELECT 
                COUNT(*) as total_calls,
                SUM(CASE WHEN status_code >= 200 AND status_code < 300 THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count,
                AVG(response_time_ms) as avg_response_time,
                COUNT(DISTINCT endpoint) as unique_endpoints
            FROM api_usage
            WHERE tenant_id = :tenant_id AND timestamp >= :start AND timestamp < :end
            """),
            {"tenant_id": tenant_id, "start": period_start, "end": period_end}
        ).fetchone()
        
        if not usage_stats or usage_stats[0] == 0:
            logger.debug(f"No metrics to aggregate for tenant {tenant_id} at {period_start}")
            return
        
        # Calculate percentiles (simplified - would need actual data points for accurate percentiles)
        avg_time = usage_stats[3] or 0
        
        # Insert or update metrics
        self.db.execute(
            text("""
            INSERT INTO tenant_metrics 
                (tenant_id, metric_type, period_start, period_end,
                 api_call_count, api_success_count, api_error_count, avg_response_time_ms,
                 updated_at)
            VALUES (:tenant_id, 'hourly', :period_start, :period_end, :call_count, :success_count, :error_count, :avg_time, :updated_at)
            ON CONFLICT(tenant_id, metric_type, period_start)
            DO UPDATE SET
                api_call_count = :call_count2,
                api_success_count = :success_count2,
                api_error_count = :error_count2,
                avg_response_time_ms = :avg_time2,
                updated_at = :updated_at2
            """),
            {
                "tenant_id": tenant_id, 
                "period_start": period_start, 
                "period_end": period_end,
                "call_count": usage_stats[0], 
                "success_count": usage_stats[1], 
                "error_count": usage_stats[2], 
                "avg_time": avg_time,
                "updated_at": datetime.utcnow(),
                "call_count2": usage_stats[0], 
                "success_count2": usage_stats[1], 
                "error_count2": usage_stats[2], 
                "avg_time2": avg_time,
                "updated_at2": datetime.utcnow()
            }
        )
        self.db.commit()
        
        logger.info(f"Aggregated hourly metrics for tenant {tenant_id} at {period_start}")
    
    def aggregate_daily_metrics(self, tenant_id: str, date: datetime) -> None:
        """
        Aggregate metrics for a specific day.
        
        Args:
            tenant_id: Tenant identifier
            date: Date to aggregate
        """
        period_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=1)
        
        # Aggregate from hourly metrics
        hourly_stats = self.db.execute(
            """
            SELECT 
                SUM(api_call_count) as total_calls,
                SUM(api_success_count) as success_count,
                SUM(api_error_count) as error_count,
                AVG(avg_response_time_ms) as avg_response_time,
                SUM(query_count) as total_queries,
                SUM(query_success_count) as query_success,
                SUM(query_error_count) as query_errors,
                AVG(avg_query_time_ms) as avg_query_time
            FROM tenant_metrics
            WHERE tenant_id = ? AND metric_type = 'hourly' 
                AND period_start >= ? AND period_start < ?
            """,
            (tenant_id, period_start, period_end)
        ).fetchone()
        
        if not hourly_stats or hourly_stats[0] is None:
            logger.debug(f"No hourly metrics to aggregate for tenant {tenant_id} on {period_start.date()}")
            return
        
        # Get storage metrics from quota usage
        storage_stats = self.db.execute(
            """
            SELECT storage_bytes, document_count
            FROM tenant_quota_usage
            WHERE tenant_id = ? AND period_type = 'daily' AND period_start = ?
            """,
            (tenant_id, period_start)
        ).fetchone()
        
        storage_bytes = storage_stats[0] if storage_stats else 0
        document_count = storage_stats[1] if storage_stats else 0
        
        # Insert or update daily metrics
        self.db.execute(
            """
            INSERT INTO tenant_metrics 
                (tenant_id, metric_type, period_start, period_end,
                 storage_bytes, document_count,
                 query_count, query_success_count, query_error_count, avg_query_time_ms,
                 api_call_count, api_success_count, api_error_count, avg_response_time_ms,
                 updated_at)
            VALUES (?, 'daily', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant_id, metric_type, period_start)
            DO UPDATE SET
                storage_bytes = ?,
                document_count = ?,
                query_count = ?,
                query_success_count = ?,
                query_error_count = ?,
                avg_query_time_ms = ?,
                api_call_count = ?,
                api_success_count = ?,
                api_error_count = ?,
                avg_response_time_ms = ?,
                updated_at = ?
            """,
            (
                tenant_id, period_start, period_end,
                storage_bytes, document_count,
                hourly_stats[4] or 0, hourly_stats[5] or 0, hourly_stats[6] or 0, hourly_stats[7] or 0,
                hourly_stats[0] or 0, hourly_stats[1] or 0, hourly_stats[2] or 0, hourly_stats[3] or 0,
                datetime.utcnow(),
                storage_bytes, document_count,
                hourly_stats[4] or 0, hourly_stats[5] or 0, hourly_stats[6] or 0, hourly_stats[7] or 0,
                hourly_stats[0] or 0, hourly_stats[1] or 0, hourly_stats[2] or 0, hourly_stats[3] or 0,
                datetime.utcnow()
            )
        )
        self.db.commit()
        
        logger.info(f"Aggregated daily metrics for tenant {tenant_id} on {period_start.date()}")
    
    def get_tenant_metrics(
        self,
        tenant_id: str,
        metric_type: str = "daily",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get metrics for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            metric_type: 'hourly', 'daily', or 'monthly'
            start_date: Start date for metrics (default: 30 days ago)
            end_date: End date for metrics (default: now)
            limit: Maximum number of records to return
            
        Returns:
            List of metric dictionaries
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        results = self.db.execute(
            """
            SELECT 
                period_start, period_end,
                storage_bytes, document_count, collection_count,
                query_count, query_success_count, query_error_count,
                avg_query_time_ms, p50_query_time_ms, p95_query_time_ms, p99_query_time_ms,
                api_call_count, api_success_count, api_error_count, avg_response_time_ms,
                db_connection_count, avg_connection_time_ms,
                estimated_cost
            FROM tenant_metrics
            WHERE tenant_id = ? AND metric_type = ?
                AND period_start >= ? AND period_start <= ?
            ORDER BY period_start DESC
            LIMIT ?
            """,
            (tenant_id, metric_type, start_date, end_date, limit)
        ).fetchall()
        
        metrics = []
        for row in results:
            metrics.append({
                "period_start": row[0],
                "period_end": row[1],
                "storage": {
                    "bytes": row[2] or 0,
                    "gb": (row[2] or 0) / (1024**3),
                    "document_count": row[3] or 0,
                    "collection_count": row[4] or 0,
                },
                "queries": {
                    "total": row[5] or 0,
                    "success": row[6] or 0,
                    "errors": row[7] or 0,
                    "success_rate": (row[6] / row[5] * 100) if row[5] else 0,
                    "avg_time_ms": row[8] or 0,
                    "p50_time_ms": row[9] or 0,
                    "p95_time_ms": row[10] or 0,
                    "p99_time_ms": row[11] or 0,
                },
                "api": {
                    "total_calls": row[12] or 0,
                    "success": row[13] or 0,
                    "errors": row[14] or 0,
                    "success_rate": (row[13] / row[12] * 100) if row[12] else 0,
                    "avg_response_time_ms": row[15] or 0,
                },
                "database": {
                    "connection_count": row[16] or 0,
                    "avg_connection_time_ms": row[17] or 0,
                },
                "cost": {
                    "estimated": row[18] or 0,
                }
            })
        
        return metrics
    
    def get_storage_usage_over_time(
        self,
        tenant_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get storage usage trend over time.
        
        Args:
            tenant_id: Tenant identifier
            days: Number of days to look back
            
        Returns:
            List of storage usage data points
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        results = self.db.execute(
            """
            SELECT period_start, storage_bytes, document_count
            FROM tenant_metrics
            WHERE tenant_id = ? AND metric_type = 'daily'
                AND period_start >= ? AND period_start <= ?
            ORDER BY period_start ASC
            """,
            (tenant_id, start_date, end_date)
        ).fetchall()
        
        return [
            {
                "date": row[0],
                "storage_bytes": row[1] or 0,
                "storage_gb": (row[1] or 0) / (1024**3),
                "document_count": row[2] or 0,
            }
            for row in results
        ]
    
    def get_query_performance_metrics(
        self,
        tenant_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get query performance metrics.
        
        Args:
            tenant_id: Tenant identifier
            days: Number of days to analyze
            
        Returns:
            Dictionary with performance metrics
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        result = self.db.execute(
            """
            SELECT 
                SUM(query_count) as total_queries,
                SUM(query_success_count) as successful_queries,
                SUM(query_error_count) as failed_queries,
                AVG(avg_query_time_ms) as avg_time,
                MAX(p99_query_time_ms) as max_p99_time
            FROM tenant_metrics
            WHERE tenant_id = ? AND metric_type = 'daily'
                AND period_start >= ? AND period_start <= ?
            """,
            (tenant_id, start_date, end_date)
        ).fetchone()
        
        if not result or result[0] is None:
            return {
                "total_queries": 0,
                "successful_queries": 0,
                "failed_queries": 0,
                "success_rate": 0,
                "avg_query_time_ms": 0,
                "max_p99_time_ms": 0,
            }
        
        total = result[0] or 0
        success = result[1] or 0
        
        return {
            "total_queries": total,
            "successful_queries": success,
            "failed_queries": result[2] or 0,
            "success_rate": (success / total * 100) if total > 0 else 0,
            "avg_query_time_ms": result[3] or 0,
            "max_p99_time_ms": result[4] or 0,
        }
    
    def get_error_rate_metrics(
        self,
        tenant_id: str,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get error rate metrics over time.
        
        Args:
            tenant_id: Tenant identifier
            days: Number of days to analyze
            
        Returns:
            List of error rate data points
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        results = self.db.execute(
            """
            SELECT 
                period_start,
                api_call_count,
                api_error_count,
                query_count,
                query_error_count
            FROM tenant_metrics
            WHERE tenant_id = ? AND metric_type = 'daily'
                AND period_start >= ? AND period_start <= ?
            ORDER BY period_start ASC
            """,
            (tenant_id, start_date, end_date)
        ).fetchall()
        
        return [
            {
                "date": row[0],
                "api_error_rate": (row[2] / row[1] * 100) if row[1] else 0,
                "query_error_rate": (row[4] / row[3] * 100) if row[3] else 0,
                "total_api_calls": row[1] or 0,
                "total_queries": row[3] or 0,
            }
            for row in results
        ]
    
    def calculate_estimated_cost(
        self,
        tenant_id: str,
        storage_bytes: int,
        query_count: int,
        api_calls: int
    ) -> float:
        """
        Calculate estimated cost for tenant usage.
        
        Args:
            tenant_id: Tenant identifier
            storage_bytes: Storage used in bytes
            query_count: Number of queries
            api_calls: Number of API calls
            
        Returns:
            Estimated cost in USD
        """
        # Pricing model (example)
        STORAGE_COST_PER_GB = 0.10  # $0.10 per GB per month
        QUERY_COST_PER_1000 = 0.50  # $0.50 per 1000 queries
        API_CALL_COST_PER_1000 = 0.10  # $0.10 per 1000 API calls
        
        storage_gb = storage_bytes / (1024**3)
        storage_cost = storage_gb * STORAGE_COST_PER_GB
        query_cost = (query_count / 1000) * QUERY_COST_PER_1000
        api_cost = (api_calls / 1000) * API_CALL_COST_PER_1000
        
        total_cost = storage_cost + query_cost + api_cost
        
        return round(total_cost, 2)
    
    def cleanup_old_metrics(self, retention_days: int = 90) -> int:
        """
        Clean up metrics older than retention period.
        
        Args:
            retention_days: Number of days to retain metrics
            
        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        result = self.db.execute(
            "DELETE FROM tenant_metrics WHERE period_start < ?",
            (cutoff_date,)
        )
        self.db.commit()
        
        deleted_count = result.rowcount
        logger.info(f"Cleaned up {deleted_count} old metric records")
        
        return deleted_count
