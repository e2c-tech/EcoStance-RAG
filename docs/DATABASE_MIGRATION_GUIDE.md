# Database Migration Guide - PostgreSQL Setup

Complete guide for setting up PostgreSQL multitenancy database.

## Quick Start

### 1. Verify Database Connection

Check your `.env` file has the PostgreSQL connection:
```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

Test connection:
```bash
psql $DATABASE_URL -c "SELECT version();"
```

### 2. Run Migrations

```bash
# Run all migrations
python migrations/run_migrations.py migrate
```

Expected output:
```
Found 2 migration(s) to run
============================================================
✓ Migrations tracking table ready
→ Running 001_create_tenant_tables.sql...
✓ 001_create_tenant_tables.sql completed successfully
→ Running 002_add_tenant_id_to_existing_tables.sql...
✓ 002_add_tenant_id_to_existing_tables.sql completed successfully
============================================================

Completed: 2/2 migrations
✓ All migrations completed successfully!
```

### 3. Verify Setup

```bash
# Check migration status
python migrations/run_migrations.py status
```

## What Gets Created

### Tenant Tables

```sql
-- Main tenant table
tenants (id, name, created_at, is_active, settings)

-- Database connections per tenant
tenant_databases (id, tenant_id, db_name, db_uri_encrypted, ...)

-- Knowledge base mappings
tenant_knowledge_bases (id, tenant_id, kb_name, collection_name, ...)

-- User-tenant relationships
tenant_users (id, tenant_id, user_id, role, permissions)

-- API keys for authentication
tenant_api_keys (id, tenant_id, key_name, key_hash, ...)

-- Resource quotas
tenant_quotas (id, tenant_id, quota_type, quota_limit, quota_used)

-- Audit trail
audit_logs (id, tenant_id, user_id, action, details, ...)
```

### Default Tenant

A default tenant is automatically created:
```json
{
  "id": "default-tenant",
  "name": "Default Tenant",
  "is_active": true,
  "settings": {
    "permissions": ["admin", "upload", "query", "manage_db"],
    "feature_flags": {},
    "quotas": {
      "storage_mb": 10000,
      "queries_per_day": 10000
    }
  }
}
```

### Existing Tables Modified

All existing tables get a `tenant_id` column:
- `uploaded_files` → tenant_id added
- `processing_jobs` → tenant_id added
- `query_history` → tenant_id added
- `documents` → tenant_id added
- `sessions` → tenant_id added

Existing data is assigned to `default-tenant`.

## Database Schema

### Tenant Settings Structure

```json
{
  "permissions": ["upload", "query", "manage_db", "admin"],
  "feature_flags": {
    "ocr_processing": true,
    "advanced_analytics": false
  },
  "quotas": {
    "storage_mb": 10000,
    "queries_per_day": 1000,
    "documents_max": 50000
  },
  "billing": {
    "tier": "professional",
    "monthly_cost": 99.00
  }
}
```

### Indexes Created

Performance indexes on all tenant_id columns:
```sql
-- Single column indexes
CREATE INDEX idx_uploaded_files_tenant_id ON uploaded_files(tenant_id);
CREATE INDEX idx_query_history_tenant_id ON query_history(tenant_id);

-- Composite indexes for common queries
CREATE INDEX idx_uploaded_files_tenant_created 
  ON uploaded_files(tenant_id, created_at DESC);
  
CREATE INDEX idx_query_history_tenant_created 
  ON query_history(tenant_id, created_at DESC);
```

## Using the Database

### Query with Tenant Context

**Before (no tenant isolation):**
```python
from sqlalchemy.orm import Session

def get_documents(db: Session):
    return db.query(Document).all()
```

**After (with tenant isolation):**
```python
from sqlalchemy.orm import Session

def get_documents(db: Session, tenant_id: str):
    return db.query(Document).filter(
        Document.tenant_id == tenant_id
    ).all()
```

### Insert with Tenant Context

```python
from sqlalchemy.orm import Session
from app.models.document import Document

def create_document(db: Session, tenant_id: str, filename: str):
    document = Document(
        tenant_id=tenant_id,
        filename=filename
    )
    db.add(document)
    db.commit()
    return document
```

### Create New Tenant

```python
from sqlalchemy.orm import Session
from app.models.tenant import Tenant
import uuid

def create_tenant(db: Session, name: str):
    tenant = Tenant(
        id=str(uuid.uuid4()),
        name=name,
        is_active=True,
        settings={
            "permissions": ["upload", "query"],
            "quotas": {
                "storage_mb": 5000,
                "queries_per_day": 500
            }
        }
    )
    db.add(tenant)
    db.commit()
    return tenant
```

## Verification Queries

### Check Tenant Tables

```sql
-- List all tenant tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_name LIKE 'tenant%' 
  AND table_schema = 'public';
```

### Check Tenant Data

```sql
-- Count tenants
SELECT COUNT(*) FROM tenants;

-- List all tenants
SELECT id, name, is_active, created_at FROM tenants;

-- Check default tenant
SELECT * FROM tenants WHERE id = 'default-tenant';
```

### Check Data Migration

```sql
-- Verify all records have tenant_id
SELECT 
    'uploaded_files' as table_name,
    COUNT(*) as total_records,
    COUNT(tenant_id) as with_tenant_id,
    COUNT(*) - COUNT(tenant_id) as missing_tenant_id
FROM uploaded_files
UNION ALL
SELECT 
    'query_history',
    COUNT(*),
    COUNT(tenant_id),
    COUNT(*) - COUNT(tenant_id)
FROM query_history;
```

### Check Indexes

```sql
-- List all tenant-related indexes
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname LIKE '%tenant%'
ORDER BY tablename, indexname;
```

## Troubleshooting

### Connection Issues

```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1;"

# Check if database exists
psql $DATABASE_URL -c "\l"

# Check current user permissions
psql $DATABASE_URL -c "SELECT current_user, current_database();"
```

### Migration Already Applied

If you see "already applied" messages, that's normal. Migrations are idempotent.

```bash
# Check what's been applied
python migrations/run_migrations.py status
```

### Orphaned Records

If you have records with invalid tenant_id:

```sql
-- Find orphaned records
SELECT table_name, COUNT(*) as orphan_count
FROM (
    SELECT 'uploaded_files' as table_name, COUNT(*) as count
    FROM uploaded_files
    WHERE tenant_id NOT IN (SELECT id FROM tenants)
    UNION ALL
    SELECT 'query_history', COUNT(*)
    FROM query_history
    WHERE tenant_id NOT IN (SELECT id FROM tenants)
) subquery
WHERE count > 0;

-- Fix by assigning to default tenant
UPDATE uploaded_files 
SET tenant_id = 'default-tenant'
WHERE tenant_id NOT IN (SELECT id FROM tenants);
```

### Performance Issues

```sql
-- Update table statistics
ANALYZE tenants;
ANALYZE uploaded_files;
ANALYZE query_history;

-- Check slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
WHERE query LIKE '%tenant_id%'
ORDER BY mean_time DESC
LIMIT 10;
```

## Rollback

⚠️ **Emergency use only!** This removes all tenant data.

```bash
# Backup first!
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Run rollback
python migrations/run_migrations.py rollback
```

## Best Practices

1. **Always backup before migrations**
   ```bash
   pg_dump $DATABASE_URL > backup.sql
   ```

2. **Test in development first**
   - Run migrations on dev database
   - Verify data integrity
   - Test application functionality

3. **Monitor performance**
   - Check query execution times
   - Verify indexes are being used
   - Monitor database size

4. **Regular maintenance**
   ```sql
   -- Vacuum and analyze
   VACUUM ANALYZE tenants;
   VACUUM ANALYZE uploaded_files;
   ```

## Next Steps

After successful migration:

1. ✅ Update application code to use tenant_id
2. ✅ Test authentication with multiple tenants
3. ✅ Verify tenant isolation in queries
4. ✅ Update Qdrant collections for tenant isolation
5. ✅ Update file storage to use tenant directories
6. ✅ Add tenant validation to all endpoints

## Support

For issues:
- Check PostgreSQL logs: `tail -f /var/log/postgresql/postgresql.log`
- Review migration output for errors
- Verify DATABASE_URL is correct
- Ensure PostgreSQL version is 12+
