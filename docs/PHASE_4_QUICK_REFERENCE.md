# Phase 4: Resource Management - Quick Reference

## Quick Start

### 1. Apply Migrations

```bash
python migrations/apply_phase4_migrations.py
```

### 2. Start Application

The scheduler starts automatically with the application.

```bash
python run_app.py
```

---

## API Endpoints

### Quota Management

```bash
# Get quota status
GET /api/v1/quota/status

# Get quota limits
GET /api/v1/quota/limits

# Get current usage
GET /api/v1/quota/usage?period=daily

# Get usage history
GET /api/v1/quota/history?days=30

# Update quotas (admin)
PUT /api/v1/quota/admin/tenant/{tenant_id}

# Reset quotas (admin)
POST /api/v1/quota/admin/tenant/{tenant_id}/reset?period=daily
```

### Metrics & Monitoring

```bash
# Get metrics
GET /api/v1/metrics/?metric_type=daily&days=30

# Get storage metrics
GET /api/v1/metrics/storage?days=30

# Get query performance
GET /api/v1/metrics/queries?days=7

# Get error rates
GET /api/v1/metrics/errors?days=7

# Get active alerts
GET /api/v1/metrics/alerts

# Get alert history
GET /api/v1/metrics/alerts/history?days=7&severity=critical

# Export metrics
GET /api/v1/metrics/export?format=csv&days=30
```

### Admin & Cleanup

```bash
# Delete tenant
DELETE /api/v1/admin/tenants/{tenant_id}

# Export tenant data
POST /api/v1/admin/tenants/{tenant_id}/export

# Get storage usage
GET /api/v1/admin/tenants/{tenant_id}/storage

# Cleanup sessions
POST /api/v1/admin/cleanup/sessions?max_age_hours=24

# Cleanup temp files
POST /api/v1/admin/cleanup/temp-files?max_age_days=7

# Archive audit logs
POST /api/v1/admin/cleanup/audit-logs?max_age_days=90

# Run all cleanup
POST /api/v1/admin/cleanup/all

# System health
GET /api/v1/admin/health/system
```

---

## Quota Tiers

| Tier | Daily Queries | Monthly Queries | Storage | Documents |
|------|--------------|-----------------|---------|-----------|
| Free | 100 | 3,000 | 1GB | 1,000 |
| Starter | 1,000 | 30,000 | 10GB | 10,000 |
| Professional | 10,000 | 300,000 | 100GB | 100,000 |
| Enterprise | Unlimited | Unlimited | Unlimited | Unlimited |

---

## Code Examples

### Check Quota

```python
from app.services.quota_service import QuotaService

quota_service = QuotaService(db)
allowed, error = quota_service.check_query_quota(tenant_id)

if not allowed:
    raise HTTPException(status_code=429, detail=error)
```

### Increment Usage

```python
quota_service.increment_usage(tenant_id, "query", amount=1, period_type="daily")
quota_service.increment_usage(tenant_id, "storage", amount=file_size, period_type="daily")
```

### Get Metrics

```python
from app.services.metrics_service import MetricsService

metrics_service = MetricsService(db)
metrics = metrics_service.get_tenant_metrics(tenant_id, "daily", limit=30)
```

### Check Alerts

```python
from app.services.alerting_service import AlertingService

alerting_service = AlertingService(db)
alerts = alerting_service.check_all_alerts(tenant_id)
```

---

## Automated Tasks

### Hourly (Every Hour)
- Aggregate hourly metrics
- Check for alerts

### Daily (2 AM UTC)
- Aggregate daily metrics
- Reset daily quotas
- Cleanup expired sessions
- Cleanup temp files (>7 days)
- Archive audit logs (>90 days)
- Cleanup old metrics (>90 days)

### Monthly (1st at 3 AM UTC)
- Reset monthly quotas

---

## Alert Thresholds

- **Quota Warning:** 80% usage
- **Quota Critical:** 95% usage
- **High Error Rate:** >5%
- **Slow Queries:** >5 seconds average

---

## Database Tables

### tenant_quotas
Stores quota limits per tenant

### tenant_quota_usage
Tracks actual usage by period

### tenant_metrics
Aggregated metrics (hourly/daily/monthly)

### tenant_alerts
Alert configuration

### alert_history
Alert tracking and history

---

## Configuration Files

- `app/services/quota_service.py` - Quota tiers and limits
- `app/services/alerting_service.py` - Alert thresholds
- `app/services/scheduler_service.py` - Schedule timing
- `migrations/005_create_quota_tables.sql` - Quota schema
- `migrations/006_create_metrics_tables.sql` - Metrics schema

---

## Testing

```bash
# Run quota tests
pytest tests/test_quota_service.py -v

# Run all tests
pytest tests/ -v
```

---

## Troubleshooting

### Scheduler Not Running

Check health endpoint:
```bash
curl http://localhost:8000/health
```

### Quotas Not Enforcing

1. Check if migrations applied
2. Verify tenant tier in database
3. Check quota_service logs

### Metrics Not Aggregating

1. Check scheduler is running
2. Verify api_usage table has data
3. Check metrics_service logs

### Alerts Not Triggering

1. Verify alert thresholds in alerting_service.py
2. Check if usage exceeds thresholds
3. Review alert_history table

---

## Support

For issues or questions:
1. Check logs in application output
2. Review PHASE_4_RESOURCE_MANAGEMENT.md
3. Check database tables for data
4. Verify migrations applied successfully
