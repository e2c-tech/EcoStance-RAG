# Phase 2.3 Quick Reference

## 📁 File Management

### List Files
```bash
GET /api/v1/files/
Authorization: Bearer {token}
```

### Download File
```bash
GET /api/v1/files/{filename}
Authorization: Bearer {token}
```

### Delete File
```bash
DELETE /api/v1/files/{filename}
Authorization: Bearer {token}
```

### Get Storage Usage
```bash
GET /api/v1/files/storage/usage
Authorization: Bearer {token}
```

### Check Quota
```bash
POST /api/v1/files/storage/check-quota
Authorization: Bearer {token}
{
  "file_size_mb": 5.0
}
```

## 📤 Upload with Quota

```bash
POST /api/v1/upload/
Authorization: Bearer {token}
Content-Type: multipart/form-data
file: <file>

# Returns storage usage info
# Rejects if quota exceeded (HTTP 413)
```

## 💻 Code Examples

### Verify File Ownership
```python
from app.services.file_access_service import get_file_access_service

service = get_file_access_service()

# Check ownership
is_owned = service.verify_tenant_owns_file(
    "tenant-123",
    "uploads/tenant-123/document.pdf"
)
```

### Get Safe Path
```python
# Prevents path traversal
safe_path = service.get_safe_file_path(
    "tenant-123",
    "document.pdf"
)
```

### Check Storage Quota
```python
quota = service.check_storage_quota(
    tenant_id="tenant-123",
    quota_mb=10000,
    file_size_bytes=5242880
)

if not quota['within_quota']:
    print(f"Quota exceeded: {quota['usage_percent']}%")
```

### List Tenant Files
```python
files = service.list_tenant_files("tenant-123")
for file in files:
    print(f"{file['filename']}: {file['size_mb']} MB")
```

## 🔐 Security

### Ownership Verification
```
✓ Checks file path starts with tenant directory
✓ Prevents cross-tenant access
✓ Returns 403 if access denied
```

### Path Traversal Prevention
```
✗ Blocks: ../../../etc/passwd
✗ Blocks: /etc/passwd
✗ Blocks: ..\\..\\windows\\system32
✓ Allows: document.pdf
```

### Storage Quotas
```
Default: 10GB per tenant
Checked: Before every upload
Rejected: HTTP 413 if exceeded
```

## 📊 Storage Structure

```
uploads/
├── tenant-123/
│   ├── doc1.pdf
│   └── doc2.pdf
└── tenant-456/
    └── doc3.pdf
```

## 🧪 Testing

```python
# Test ownership
service = get_file_access_service()
assert service.verify_tenant_owns_file(
    "tenant-123",
    "uploads/tenant-123/file.pdf"
) == True

# Test path traversal prevention
try:
    service.get_safe_file_path("tenant-123", "../etc/passwd")
    assert False
except ValueError:
    pass  # Expected

# Test quota
quota = service.check_storage_quota("tenant-123", 100, 50*1024*1024)
print(f"Within quota: {quota['within_quota']}")
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `app/services/file_access_service.py` | File access control |
| `app/routers/file_router.py` | File management endpoints |
| `app/routers/upload.py` | Upload with quota check |

## 🎯 Status

✅ **Phase 2.3 Complete** - File Storage Isolation
✅ **Phase 2 Complete** - Core Multitenancy

**Next:** Phase 3 - Security & Access Control
