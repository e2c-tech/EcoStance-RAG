# Phase 3: Security & Access Control - Quick Reference

## Role Hierarchy

```
VIEWER < USER < MANAGER < ADMIN < SUPER_ADMIN
```

## Common Permission Checks

```python
from app.auth.rbac import RBACService
from app.auth.permissions import Permission

rbac = RBACService(db)

# Check permission (returns bool)
if rbac.check_permission(tenant_id, user_id, Permission.KB_CREATE):
    # allowed
    pass

# Require permission (raises 403 if denied)
rbac.require_permission(tenant_id, user_id, Permission.FILE_UPLOAD)
```

## Audit Logging

```python
from app.services.audit_service import AuditService

audit = AuditService(db)

# Log any action
audit.log_action(
    tenant_id=tenant_id,
    user_id=user_id,
    action="create_kb",
    resource_type="knowledge_base",
    resource_id=kb_id,
    status="success",
    request=request
)

# Log authentication
audit.log_authentication(
    user_id=user_id,
    action="login",
    status="success",
    tenant_id=tenant_id
)

# Get logs
logs = audit.get_tenant_audit_logs(tenant_id, limit=100)
```

## Rate Limiting

**Tiers:**
- FREE: 10/min, 100/hour, 1K/day
- BASIC: 30/min, 500/hour, 5K/day
- PREMIUM: 60/min, 1K/hour, 10K/day
- ENTERPRISE: 120/min, 5K/hour, 50K/day

**Check usage:**
```python
from app.middleware.rate_limiter import rate_limiter

stats = rate_limiter.get_usage_stats(tenant_id)
```

## Admin Endpoints

```bash
# List all tenants
GET /api/v1/admin/tenants

# Create tenant
POST /api/v1/admin/tenants
{
  "name": "Acme Corp",
  "email": "admin@acme.com",
  "settings": {"tier": "premium"}
}

# Assign role
POST /api/v1/admin/tenants/{tenant_id}/users
{
  "user_id": "user123",
  "role": "manager"
}

# List tenant users
GET /api/v1/admin/tenants/{tenant_id}/users

# Remove user
DELETE /api/v1/admin/tenants/{tenant_id}/users/{user_id}
```

## Database Migration

```bash
python migrations/apply_audit_logs_migration.py
```

## Testing

```bash
python test_phase3_security.py
```

## Key Files

- `app/auth/permissions.py` - Permission definitions
- `app/auth/rbac.py` - RBAC service
- `app/services/audit_service.py` - Audit logging
- `app/middleware/rate_limiter.py` - Rate limiting
- `app/routers/admin_router.py` - Admin endpoints
- `app/models/audit_log.py` - Audit log model
