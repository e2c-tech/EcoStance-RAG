# Phase 1 Quick Reference Card

## 🚀 Quick Commands

### Run Migrations
```bash
python migrations/run_migrations.py migrate
```

### Check Migration Status
```bash
python migrations/run_migrations.py status
```

### Start Server
```bash
uvicorn app.main:app --reload
```

### Run Tests
```bash
python -m pytest tests/test_authentication.py -v
```

## 🔑 Authentication

### Get Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "default-tenant", "user_id": "user-123"}'
```

### Use Token in Request
```bash
curl -X GET http://localhost:8000/api/v1/endpoint \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Use X-Tenant-ID Header (Alternative)
```bash
curl -X GET http://localhost:8000/api/v1/endpoint \
  -H "X-Tenant-ID: default-tenant"
```

## 💻 Code Examples

### Protect Endpoint with Tenant Context
```python
from fastapi import APIRouter, Depends
from app.auth.dependencies import get_tenant_id

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint(tenant_id: str = Depends(get_tenant_id)):
    return {"tenant_id": tenant_id}
```

### Query with Tenant Filter
```python
from sqlalchemy.orm import Session

def get_documents(db: Session, tenant_id: str):
    return db.query(Document).filter(
        Document.tenant_id == tenant_id
    ).all()
```

### Create with Tenant Context
```python
def create_document(db: Session, tenant_id: str, filename: str):
    doc = Document(tenant_id=tenant_id, filename=filename)
    db.add(doc)
    db.commit()
    return doc
```

## 🗄️ Database Queries

### Check Tenants
```sql
SELECT id, name, is_active FROM tenants;
```

### Check Default Tenant
```sql
SELECT * FROM tenants WHERE id = 'default-tenant';
```

### Verify tenant_id Columns
```sql
SELECT table_name FROM information_schema.columns 
WHERE column_name = 'tenant_id';
```

### Check Data Migration
```sql
SELECT COUNT(*) FROM uploaded_files WHERE tenant_id IS NULL;
```

## 📁 Important Files

| File | Purpose |
|------|---------|
| `migrations/001_create_tenant_tables.sql` | Creates tenant tables |
| `migrations/002_add_tenant_id_to_existing_tables.sql` | Adds tenant_id |
| `migrations/run_migrations.py` | Migration runner |
| `app/auth/jwt_handler.py` | JWT token management |
| `app/auth/dependencies.py` | Tenant context extraction |
| `app/middleware/auth_middleware.py` | Request authentication |
| `app/services/tenant_validation.py` | Tenant validation |

## 📚 Documentation

| Document | Description |
|----------|-------------|
| `AUTHENTICATION_QUICKSTART.md` | 5-minute quick start |
| `AUTHENTICATION_GUIDE.md` | Complete auth guide |
| `DATABASE_MIGRATION_GUIDE.md` | Migration guide |
| `PHASE_1_COMPLETE_SUMMARY.md` | Full summary |

## ⚙️ Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:port/db

# Optional (with defaults)
JWT_SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## ✅ Verification Checklist

- [ ] DATABASE_URL set in .env
- [ ] Migrations run successfully
- [ ] Default tenant created
- [ ] Authentication tests passing
- [ ] Server starts without errors
- [ ] Can generate JWT tokens
- [ ] Can make authenticated requests

## 🆘 Troubleshooting

### Can't connect to database
```bash
psql $DATABASE_URL -c "SELECT 1;"
```

### Migration already applied
```bash
python migrations/run_migrations.py status
```

### Token invalid
- Check token hasn't expired (30 min default)
- Verify JWT_SECRET_KEY matches
- Generate new token

### Import errors
```bash
pip install -r requirements.txt
```

## 🎯 Default Tenant

- **ID:** `default-tenant`
- **Name:** Default Tenant
- **Permissions:** admin, upload, query, manage_db
- **Quotas:** 10GB storage, 10,000 queries/day

## 📊 Phase 1 Status

✅ **COMPLETE**

- ✅ 1.1 Tenant Data Model
- ✅ 1.2 Authentication & Context
- ✅ 1.3 Database Schema Migration

**Next:** Phase 2 - Core Multitenancy
