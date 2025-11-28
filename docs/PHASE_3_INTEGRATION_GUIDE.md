# Phase 3: Integration Guide

## How to Add Security to Existing Endpoints

This guide shows how to integrate RBAC, audit logging, and rate limiting into your existing API endpoints.

## Step 1: Add Permission Checks

### Before (No Security)
```python
@router.post("/kb/create")
async def create_knowledge_base(
    kb_name: str,
    db: Session = Depends(get_db)
):
    # Create KB logic
    pass
```

### After (With RBAC)
```python
from app.auth.dependencies import get_current_user
from app.auth.rbac import RBACService
from app.auth.permissions import Permission

@router.post("/kb/create")
async def create_knowledge_base(
    kb_name: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.KB_CREATE)
    
    # Create KB logic
    pass
```

## Step 2: Add Audit Logging

### Complete Example with Audit Logging
```python
from app.services.audit_service import AuditService
from fastapi import Request

@router.post("/kb/create")
async def create_knowledge_base(
    kb_name: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.KB_CREATE)
    
    try:
        # Create KB logic
        kb_id = create_kb(tenant_id, kb_name)
        
        # Log success
        audit = AuditService(db)
        audit.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action="create_kb",
            resource_type="knowledge_base",
            resource_id=kb_id,
            details={"kb_name": kb_name},
            status="success",
            request=request
        )
        
        return {"kb_id": kb_id, "status": "created"}
        
    except Exception as e:
        # Log failure
        audit = AuditService(db)
        audit.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action="create_kb",
            resource_type="knowledge_base",
            details={"kb_name": kb_name},
            status="failure",
            error_message=str(e),
            request=request
        )
        raise
```

## Step 3: Rate Limiting (Automatic)

Rate limiting is applied automatically via middleware. No code changes needed in endpoints!

The middleware checks:
- Requests per minute
- Requests per hour
- Requests per day

Returns 429 if limits exceeded.

## Common Patterns

### Pattern 1: Read Operations (View)
```python
@router.get("/kb/{kb_id}")
async def get_knowledge_base(
    kb_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.KB_VIEW)
    
    # Get KB
    kb = get_kb(tenant_id, kb_id)
    
    # Log data access
    audit = AuditService(db)
    audit.log_data_access(
        tenant_id=tenant_id,
        user_id=user_id,
        resource_type="knowledge_base",
        resource_id=kb_id,
        action="view"
    )
    
    return kb
```

### Pattern 2: Write Operations (Create/Update/Delete)
```python
@router.delete("/kb/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.KB_DELETE)
    
    try:
        # Delete KB
        delete_kb(tenant_id, kb_id)
        
        # Log success
        audit = AuditService(db)
        audit.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action="delete_kb",
            resource_type="knowledge_base",
            resource_id=kb_id,
            status="success",
            request=request
        )
        
        return {"status": "deleted"}
        
    except Exception as e:
        # Log failure
        audit = AuditService(db)
        audit.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action="delete_kb",
            resource_type="knowledge_base",
            resource_id=kb_id,
            status="failure",
            error_message=str(e),
            request=request
        )
        raise
```

### Pattern 3: File Operations
```python
@router.post("/files/upload")
async def upload_file(
    file: UploadFile,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.FILE_UPLOAD)
    
    try:
        # Upload file
        file_id = save_file(tenant_id, file)
        
        # Log success
        audit = AuditService(db)
        audit.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action="upload_file",
            resource_type="file",
            resource_id=file_id,
            details={
                "filename": file.filename,
                "size": file.size
            },
            status="success",
            request=request
        )
        
        return {"file_id": file_id}
        
    except Exception as e:
        audit = AuditService(db)
        audit.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action="upload_file",
            resource_type="file",
            details={"filename": file.filename},
            status="failure",
            error_message=str(e),
            request=request
        )
        raise
```

### Pattern 4: Database Operations
```python
@router.post("/db/execute")
async def execute_query(
    query: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]
    
    # Check permission
    rbac = RBACService(db)
    rbac.require_permission(tenant_id, user_id, Permission.DB_EXECUTE)
    
    try:
        # Execute query
        result = execute_db_query(tenant_id, query)
        
        # Log success
        audit = AuditService(db)
        audit.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action="execute_query",
            resource_type="database",
            details={"query": query[:100]},  # Truncate long queries
            status="success",
            request=request
        )
        
        return result
        
    except Exception as e:
        audit = AuditService(db)
        audit.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            action="execute_query",
            resource_type="database",
            details={"query": query[:100]},
            status="failure",
            error_message=str(e),
            request=request
        )
        raise
```

## Permission Reference

### Knowledge Base Permissions
- `Permission.KB_VIEW` - View knowledge bases
- `Permission.KB_CREATE` - Create knowledge bases
- `Permission.KB_UPDATE` - Update knowledge bases
- `Permission.KB_DELETE` - Delete knowledge bases
- `Permission.KB_UPLOAD` - Upload documents
- `Permission.KB_QUERY` - Query knowledge bases

### Database Permissions
- `Permission.DB_VIEW` - View database connections
- `Permission.DB_CONNECT` - Connect to databases
- `Permission.DB_QUERY` - Generate queries
- `Permission.DB_EXECUTE` - Execute queries
- `Permission.DB_MANAGE` - Manage connections

### File Permissions
- `Permission.FILE_VIEW` - View files
- `Permission.FILE_UPLOAD` - Upload files
- `Permission.FILE_DOWNLOAD` - Download files
- `Permission.FILE_DELETE` - Delete files

### Tenant Permissions
- `Permission.TENANT_VIEW` - View tenant info
- `Permission.TENANT_UPDATE` - Update tenant settings
- `Permission.TENANT_MANAGE_USERS` - Manage users
- `Permission.TENANT_MANAGE_SETTINGS` - Manage settings

### Admin Permissions
- `Permission.ADMIN_VIEW_ALL` - View all tenants
- `Permission.ADMIN_MANAGE_TENANTS` - Manage tenants
- `Permission.ADMIN_MANAGE_USERS` - Manage all users
- `Permission.ADMIN_VIEW_METRICS` - View metrics
- `Permission.ADMIN_MANAGE_QUOTAS` - Manage quotas

## Error Handling

### Permission Denied (403)
```python
try:
    rbac.require_permission(tenant_id, user_id, Permission.KB_DELETE)
except HTTPException as e:
    # Returns 403 with message: "Permission denied: kb:delete required"
    raise
```

### Rate Limit Exceeded (429)
```python
# Handled automatically by middleware
# Returns: {"detail": "Rate limit exceeded. Please try again later."}
# Headers: {"Retry-After": "60"}
```

## Best Practices

1. **Always check permissions first** before any operation
2. **Log all sensitive operations** (create, update, delete)
3. **Include request context** for IP and user agent tracking
4. **Log both success and failure** for complete audit trail
5. **Use try-except** to ensure failures are logged
6. **Truncate sensitive data** in logs (passwords, long queries)
7. **Check permissions at service layer** not just routes

## Testing Your Integration

```python
# Test permission check
def test_permission_check():
    rbac = RBACService(db)
    
    # Should succeed
    rbac.require_permission(tenant_id, admin_user_id, Permission.KB_DELETE)
    
    # Should raise 403
    with pytest.raises(HTTPException) as exc:
        rbac.require_permission(tenant_id, viewer_user_id, Permission.KB_DELETE)
    assert exc.value.status_code == 403

# Test audit logging
def test_audit_logging():
    audit = AuditService(db)
    
    # Log action
    log = audit.log_action(
        tenant_id=tenant_id,
        user_id=user_id,
        action="test_action",
        status="success"
    )
    
    # Verify
    assert log.tenant_id == tenant_id
    assert log.action == "test_action"
    
    # Retrieve logs
    logs = audit.get_tenant_audit_logs(tenant_id)
    assert len(logs) > 0
```

## Migration Checklist

For each existing endpoint:

- [ ] Add `current_user: dict = Depends(get_current_user)` parameter
- [ ] Extract `tenant_id` and `user_id` from current_user
- [ ] Add permission check with `rbac.require_permission()`
- [ ] Add audit logging for the operation
- [ ] Add try-except for error logging
- [ ] Test with different user roles
- [ ] Verify audit logs are created

## Summary

Security integration requires three main steps:
1. **Permission checks** - Use RBAC service
2. **Audit logging** - Use Audit service
3. **Rate limiting** - Automatic via middleware

Follow the patterns above for consistent security across all endpoints.
