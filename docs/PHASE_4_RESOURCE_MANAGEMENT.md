# Phase 4: Resource Management - Complete Implementation

**Status:** ✅ COMPLETE  
**Date:** November 17, 2025

## Overview

Phase 4 implements comprehensive resource management for the multitenancy system, including:
- Quota management and enforcement
- Metrics collection and monitoring
- Alerting system
- Automated cleanup and maintenance
- Background scheduler for automated tasks

---

## 4.1 Quotas & Limits ✅

### Database Schema

Created two new tables for quota management:

**tenant_quotas** - Stores quota limits per tenant
- `max_queries_per_day` - Daily query limit
- `max_queries_per_month` - Monthly query limit
- `max_documents` - Maximum number of documents
- `max_storage_bytes` - Storage limit in bytes
- `max_db_connections` - Maximum database connections
- `max_concurrent_queries` - Concurrent query limit
- `max_api_calls_per_minute` - API rate limit (per minute)
- `max_api_calls_per_hour` - API rate limit (per hour)

**tenant_quota_usage** - Tracks actual usage
- Tracks usage by period (hourly, daily, monthly)
- Records query counts, storage usage, API calls
- Automatically resets based on period type

### Quota Service

**File:** `app/services/quota_service.py`

**Key Features:**
- Tier-based default quotas (free, starter, professional, enterprise)
- Real-time quota checking before operations
- Usage tracking and increment functions
- Comprehensive quota status reporting
- Admin functions for quota management

**Quota Tiers:**

| Tier | Daily Queries | Monthly Queries | Storage | Documents | DB Connections |
|------|--------------|-----------------|---------|-----------|----------------|
| Free | 100 | 3,000 | 1GB | 1,000 | 2 |
| Starter | 1,000 | 30,000 | 10GB | 10,000 | 5 |
| Professional | 10,000 | 300,000 | 100GB | 100,000 | 20 |
| Enterprise | Unlimited | Unlimited | Unlimited | Unlimited | 100 |

**Methods:**
- `check_query_quota(tenant_id)` - Check if tenant can execute query
- `check_document_quota(tenant_id, additional_docs)` - Check document limit
- `check_storage_quota(tenant_id, additional_bytes)` - Check storage limit
- `check_connection_quota(tenant_id)` - Check connection limit
- `check_api_rate_limit(tenant_id, period)` - Check API rate limit
- `increment_usage(tenant_id, usage_type, amount)` - Increment usage counter
- `get_quota_status(tenant_id)` - Get comprehensive quota status
- `update_tenant_quotas(tenant_id, quotas)` - Update quota limits (admin)

### Quota Router

**File:** `app/routers/quota_router.py`

**Endpoints:**

```
GET  /api/v1/quota/status          - Get quota status
GET  /api/v1/quota/limits          - Get quota limits
GET  /api/v1/quota/usage           - Get current usage
GET  /api/v1/quota/history         - Get usage history
PUT  /api/v1/quota/admin/tenant/{id} - Update quotas (admin)
POST /api/v1/quota/admin/tenant/{id}/reset - Reset quotas (admin)
```

**Example Response:**

```json
{
  "success": true,
  "data": {
    "tenant_id": "acme-corp",
    "quotas": {
      "max_queries_per_day": 1000,
      "max_storage_bytes": 10737418240
    },
    "daily_usage": {
      "queries": {
        "current": 450,
        "limit": 1000,
        "percentage": 45.0
      }
    },
    "storage": {
      "current_gb": 3.5,
      "limit_gb": 10.0,
      "percentage": 35.0
    }
  }
}
```

---

## 4.2 Monitoring & Metrics ✅

### Database Schema

**tenant_metrics** - Aggregated metrics
- Stores hourly, daily, and monthly aggregations
- Tracks storage, queries, API calls, errors
- Records performance metrics (avg, p50, p95, p99)
- Calculates estimated costs

**tenant_alerts** - Alert configuration
- Configurable alert thresholds
- Email and webhook notification support
- Alert enable/disable per tenant

**alert_history** - Alert tracking
- Records all triggered alerts
- Tracks resolution status
- Maintains alert history

### Metrics Service

**File:** `app/services/metrics_service.py`

**Key Features:**
- Automatic hourly and daily aggregation
- Storage usage tracking over time
- Query performance analysis
- Error rate monitoring
- Cost estimation
- Automatic cleanup of old metrics (90-day retention)

**Methods:**
- `aggregate_hourly_metrics(tenant_id, hour)` - Aggregate hourly data
- `aggregate_daily_metrics(tenant_id, date)` - Aggregate daily data
- `get_tenant_metrics(tenant_id, metric_type, start_date, end_date)` - Get metrics
- `get_storage_usage_over_time(tenant_id, days)` - Storage trends
- `get_query_performance_metrics(tenant_id, days)` - Performance analysis
- `get_error_rate_metrics(tenant_id, days)` - Error analysis
- `calculate_estimated_cost(tenant_id, ...)` - Cost calculation
- `cleanup_old_metrics(retention_days)` - Remove old data

### Alerting Service

**File:** `app/services/alerting_service.py`

**Alert Types:**
- **Quota Warnings** - Alert at 80% and 95% usage
- **High Error Rate** - Alert when error rate > 5%
- **Slow Queries** - Alert when avg query time > 5 seconds
- **Storage Limits** - Alert when approaching storage limit

**Methods:**
- `check_quota_alerts(tenant_id)` - Check quota thresholds
- `check_error_rate_alerts(tenant_id)` - Check error rates
- `check_performance_alerts(tenant_id)` - Check performance
- `check_all_alerts(tenant_id)` - Run all checks
- `send_email_alert(tenant_id, alert, smtp_config)` - Email notification
- `send_webhook_alert(tenant_id, alert, webhook_url)` - Webhook notification
- `get_alert_history(tenant_id, days, severity)` - Get alert history

### Metrics Router

**File:** `app/routers/metrics_router.py`

**Endpoints:**

```
GET  /api/v1/metrics/              - Get tenant metrics
GET  /api/v1/metrics/storage       - Storage usage over time
GET  /api/v1/metrics/queries       - Query performance metrics
GET  /api/v1/metrics/errors        - Error rate metrics
GET  /api/v1/metrics/alerts        - Active alerts
GET  /api/v1/metrics/alerts/history - Alert history
GET  /api/v1/metrics/export        - Export metrics (CSV/JSON)
GET  /api/v1/metrics/admin/all    - All tenant metrics (admin)
POST /api/v1/metrics/admin/aggregate - Trigger aggregation (admin)
```

**Example Metrics Response:**

```json
{
  "success": true,
  "data": [
    {
      "period_start": "2025-11-17T00:00:00",
      "storage": {
        "gb": 3.5,
        "document_count": 1250
      },
      "queries": {
        "total": 450,
        "success": 445,
        "errors": 5,
        "success_rate": 98.9,
        "avg_time_ms": 234.5
      },
      "api": {
        "total_calls": 1200,
        "success": 1185,
        "errors": 15,
        "success_rate": 98.75
      }
    }
  ]
}
```

---

## 4.3 Cleanup & Maintenance ✅

### Cleanup Service

**File:** `app/services/cleanup_service.py`

**Key Features:**
- Complete tenant data deletion (soft/hard)
- Automated cleanup of expired sessions
- Temporary file cleanup
- Audit log archival
- Inactive connection cleanup
- Tenant data export for offboarding
- Storage usage calculation

**Methods:**
- `delete_tenant_data(tenant_id, soft_delete)` - Delete all tenant data
- `cleanup_expired_sessions(max_age_hours)` - Remove old sessions
- `cleanup_temporary_files(max_age_days)` - Remove temp files
- `archive_old_audit_logs(max_age_days)` - Archive logs
- `cleanup_inactive_connections(max_idle_hours)` - Close idle connections
- `run_daily_cleanup()` - Run all cleanup tasks
- `export_tenant_data(tenant_id, export_path)` - Export for backup
- `get_tenant_storage_usage(tenant_id)` - Calculate storage

### Admin Router

**File:** `app/routers/admin_router.py`

**Endpoints:**

```
DELETE /api/v1/admin/tenants/{id}           - Delete tenant
POST   /api/v1/admin/tenants/{id}/export    - Export tenant data
GET    /api/v1/admin/tenants/{id}/storage   - Get storage usage
POST   /api/v1/admin/cleanup/sessions       - Cleanup sessions
POST   /api/v1/admin/cleanup/temp-files     - Cleanup temp files
POST   /api/v1/admin/cleanup/audit-logs     - Archive logs
POST   /api/v1/admin/cleanup/all            - Run all cleanup
GET    /api/v1/admin/health/system          - System health
```

### Background Scheduler

**File:** `app/services/scheduler_service.py`

**Automated Tasks:**

**Hourly:**
- Aggregate hourly metrics for all tenants
- Check for alerts and send notifications

**Daily (2 AM UTC):**
- Aggregate daily metrics
- Reset daily quota counters
- Run cleanup tasks (sessions, temp files, logs)
- Clean up old metrics (90-day retention)

**Monthly (1st at 3 AM UTC):**
- Reset monthly quota counters
- Generate monthly reports (if configured)

**Implementation:**
- Runs in background thread
- Automatic startup/shutdown with application
- Error handling and logging
- Configurable schedules

---

## Integration with Existing System

### Main Application Updates

**File:** `app/main.py`

Added:
- Import of new routers (quota_router, metrics_router)
- Import of scheduler service
- Scheduler startup in lifespan
- Router registration

### Middleware Integration

The quota and metrics services integrate with existing middleware:

**Usage Tracking Middleware:**
- Automatically increments quota usage
- Records metrics for aggregation

**Rate Limiter:**
- Uses quota service for rate limit checks
- Returns 429 with quota info when exceeded

---

## Database Migrations

### Migration Files

1. **005_create_quota_tables.sql**
   - Creates tenant_quotas table
   - Creates tenant_quota_usage table
   - Adds indexes for performance
   - Inserts default quotas for existing tenants

2. **006_create_metrics_tables.sql**
   - Creates tenant_metrics table
   - Creates tenant_alerts table
   - Creates alert_history table
   - Adds indexes for queries

### Applying Migrations

```bash
python migrations/apply_phase4_migrations.py
```

---

## Testing

### Test Files

**tests/test_quota_service.py**
- Tests quota checking and enforcement
- Tests usage tracking
- Tests quota updates
- Tests tier-based quotas

### Running Tests

```bash
pytest tests/test_quota_service.py -v
```

---

## Usage Examples

### Check Quota Before Operation

```python
from app.services.quota_service import QuotaService

quota_service = QuotaService(db)

# Check if tenant can execute query
allowed, error = quota_service.check_query_quota(tenant_id)
if not allowed:
    raise HTTPException(status_code=429, detail=error)

# Execute query...

# Increment usage
quota_service.increment_usage(tenant_id, "query", amount=1, period_type="daily")
quota_service.increment_usage(tenant_id, "query", amount=1, period_type="monthly")
```

### Get Tenant Metrics

```python
from app.services.metrics_service import MetricsService

metrics_service = MetricsService(db)

# Get daily metrics for last 30 days
metrics = metrics_service.get_tenant_metrics(
    tenant_id=tenant_id,
    metric_type="daily",
    limit=30
)

# Get storage trends
storage_data = metrics_service.get_storage_usage_over_time(tenant_id, days=30)
```

### Check Alerts

```python
from app.services.alerting_service import AlertingService

alerting_service = AlertingService(db)

# Check all alerts for tenant
alerts = alerting_service.check_all_alerts(tenant_id)

# Send critical alerts
for alert in alerts:
    if alert["severity"] == "critical":
        alerting_service.send_email_alert(tenant_id, alert, smtp_config)
```

---

## API Usage Examples

### Get Quota Status

```bash
curl -X GET "http://localhost:8000/api/v1/quota/status" \
  -H "X-Tenant-ID: acme-corp" \
  -H "Authorization: Bearer <token>"
```

### Get Metrics

```bash
curl -X GET "http://localhost:8000/api/v1/metrics/?metric_type=daily&days=30" \
  -H "X-Tenant-ID: acme-corp" \
  -H "Authorization: Bearer <token>"
```

### Export Metrics

```bash
curl -X GET "http://localhost:8000/api/v1/metrics/export?format=csv&days=30" \
  -H "X-Tenant-ID: acme-corp" \
  -H "Authorization: Bearer <token>" \
  -o metrics.csv
```

### Update Quotas (Admin)

```bash
curl -X PUT "http://localhost:8000/api/v1/quota/admin/tenant/acme-corp" \
  -H "X-Tenant-ID: admin-tenant" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "max_queries_per_day": 5000,
    "max_storage_bytes": 53687091200
  }'
```

### Delete Tenant (Admin)

```bash
curl -X DELETE "http://localhost:8000/api/v1/admin/tenants/acme-corp" \
  -H "X-Tenant-ID: admin-tenant" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "soft_delete": true,
    "confirm": true
  }'
```

---

## Configuration

### Quota Thresholds

Edit `app/services/quota_service.py` to modify tier quotas:

```python
TIER_QUOTAS = {
    "free": {
        "max_queries_per_day": 100,
        "max_storage_bytes": 1073741824,  # 1GB
        # ...
    }
}
```

### Alert Thresholds

Edit `app/services/alerting_service.py`:

```python
QUOTA_WARNING_THRESHOLD = 80  # Alert at 80% usage
QUOTA_CRITICAL_THRESHOLD = 95  # Critical at 95%
HIGH_ERROR_RATE_THRESHOLD = 5  # Alert if error rate > 5%
SLOW_QUERY_THRESHOLD = 5000  # Alert if avg > 5 seconds
```

### Scheduler Timing

Edit `app/services/scheduler_service.py`:

```python
# Hourly tasks run every hour
# Daily tasks run at 2 AM UTC
# Monthly tasks run on 1st at 3 AM UTC
```

---

## Performance Considerations

1. **Quota Checks:** Cached in memory for performance
2. **Metrics Aggregation:** Runs in background, doesn't block requests
3. **Database Indexes:** Added on frequently queried columns
4. **Retention Policy:** Old metrics automatically cleaned up (90 days)
5. **Background Scheduler:** Runs in separate thread, minimal impact

---

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

Returns scheduler status and system health.

### System Health (Admin)

```bash
curl -X GET "http://localhost:8000/api/v1/admin/health/system" \
  -H "X-Tenant-ID: admin-tenant" \
  -H "Authorization: Bearer <admin-token>"
```

Returns:
- Total/active tenant counts
- Total storage usage
- API call statistics
- Error rates

---

## Next Steps

Phase 4 is complete! Next phases:

**Phase 5: UI & User Experience**
- Tenant login and selection
- Usage dashboards
- Admin interface

**Phase 6: Advanced Features**
- Multi-region support
- Tenant customization
- Billing integration

---

## Summary

Phase 4 successfully implements:
- ✅ Complete quota management system with tier-based limits
- ✅ Comprehensive metrics collection and aggregation
- ✅ Automated alerting for quota, errors, and performance
- ✅ Cleanup and maintenance services
- ✅ Background scheduler for automated tasks
- ✅ Admin APIs for resource management
- ✅ Database migrations and schema
- ✅ Integration with existing middleware
- ✅ Tests and documentation

The system now has full resource management capabilities with automated monitoring, alerting, and maintenance.
