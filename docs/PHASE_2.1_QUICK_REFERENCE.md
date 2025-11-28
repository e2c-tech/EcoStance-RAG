# Phase 2.1 Quick Reference

## 🚀 Collection Naming

```python
from app.services.qdrant_service import get_qdrant_client
from app.services.tenant_service import get_tenant_service

client = get_qdrant_client()
tenant_service = get_tenant_service(client)

# Generate collection name
collection_name = tenant_service.get_collection_name("acme-corp", "docs")
# Result: "tenant_acme-corp_docs"
```

## 📤 Upload with Tenant Context

```bash
# Get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "acme-corp"}'

# Upload file
curl -X POST http://localhost:8000/api/v1/upload/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"

# Process to Qdrant
curl -X POST http://localhost:8000/api/v1/upload-to-qdrant/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file_path=uploads/acme-corp/document.pdf" \
  -F "kb_name=docs"
```

## 🔍 Query Tenant KB

```bash
curl -X POST http://localhost:8000/api/v1/query/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "kb_name=docs" \
  -F "query=What is the refund policy?"
```

## 🔄 Migrate Collections

```bash
# List collections
python migrations/migrate_qdrant_collections.py list

# Migrate to tenant naming
python migrations/migrate_qdrant_collections.py migrate

# Migrate and delete old
python migrations/migrate_qdrant_collections.py migrate --delete-old
```

## 💻 Code Examples

### Create Tenant Collection
```python
collection_name = tenant_service.create_tenant_collection(
    tenant_id="acme-corp",
    kb_name="support-docs"
)
```

### List Tenant Collections
```python
collections = tenant_service.list_tenant_collections("acme-corp")
for col in collections:
    print(f"{col['kb_name']}: {col['points_count']} points")
```

### Delete Tenant Collection
```python
success = tenant_service.delete_tenant_collection(
    tenant_id="acme-corp",
    kb_name="old-docs"
)
```

### Verify Collection Access
```python
has_access = tenant_service.verify_tenant_access(
    tenant_id="acme-corp",
    collection_name="tenant_acme-corp_docs"
)
```

## 📊 Collection Format

```
Format: tenant_{tenant_id}_{kb_name}

Examples:
- tenant_default-tenant_docs
- tenant_acme-corp_support
- tenant_techco_knowledge-base
```

## 🗄️ Document Metadata

```json
{
  "text": "Document content...",
  "source_filename": "document.pdf",
  "chunk_index": 0,
  "tenant_id": "acme-corp",
  "page_number": 1
}
```

## 📁 File Structure

```
uploads/
├── tenant-123/
│   ├── document1.pdf
│   └── document2.pdf
└── tenant-456/
    └── document3.pdf
```

## ✅ Verification

```python
# Check collection exists
exists = tenant_service.collection_exists("tenant_acme-corp_docs")

# Get collection info
info = tenant_service.get_collection_info("acme-corp", "docs")
print(f"Points: {info['points_count']}")

# Parse collection name
parsed = tenant_service.parse_collection_name("tenant_acme-corp_docs")
# Result: {"tenant_id": "acme-corp", "kb_name": "docs"}
```

## 🔐 Security

- ✅ Collections isolated by tenant
- ✅ Automatic tenant_id in metadata
- ✅ Collection ownership verification
- ✅ Tenant-specific file directories
- ✅ Access control via JWT tokens

## 📚 Key Files

| File | Purpose |
|------|---------|
| `app/services/tenant_service.py` | Tenant collection management |
| `app/routers/upload.py` | File upload with tenant context |
| `app/routers/qdrant_upload.py` | Process & upload to tenant KB |
| `app/routers/query_router.py` | Query tenant KB |
| `migrations/migrate_qdrant_collections.py` | Migration tool |

## 🎯 Status

✅ **Phase 2.1 Complete** - Qdrant Collection Isolation

**Next:** Phase 2.2 - Database Connection Management
