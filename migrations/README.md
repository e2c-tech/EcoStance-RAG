# Database Migrations

This directory contains SQL migration scripts for adding multitenancy support to the PostgreSQL database.

## Migration Files

1. **001_create_tenant_tables.sql** - Creates all tenant-related tables
2. **002_add_tenant_id_to_existing_tables.sql** - Adds tenant_id to existing tables
3. **003_rollback_tenant_migration.sql** - Emergency rollback script

## Prerequisites

- PostgreSQL database
- `DATABASE_URL` environment variable set in `.env`
- Python with `psycopg2` installed

## Installation

Install required Python package:
```bash
pip install psycopg2-binary
```

## Usage

### Run All Migrations

```bash
python migrations/run_migrations.py migrate
```

This will:
- Create tenant tables (tenants, tenant_databases, etc.)
- Add tenant_id columns to existing tables
- Create indexes for performance
- Backfill existing data with default tenant
- Track which migrations have been applied

### Check Migration Status

```bash
python migrations/run_migrations.py status
```

Shows which migrations have been applied and when.

### Rollback (Emergency Only)

```bash
python migrations/run_migrations.py rollback
```

⚠️ **WARNING**: This removes ALL tenant data! Only use if migration fails.

## Manual Execution

You can also run migrations manually using `psql`:

```bash
# Connect to database
psql $DATABASE_URL

# Run migration
\i migrations/001_create_tenant_tables.sql
\i migrations/002_add_tenant_id_to_existing_tables.sql
```

## What Gets Created

### New Tables

1. **tenants** - Main tenant information
2. **tenant_databases** - Database connections per tenant
3. **tenant_knowledge_bases** - Knowledge base mappings
4. **tenant_users** - User-tenant-role mappings
5. **tenant_api_keys** - API keys for authentication
6. **tenant_quotas** - Resource quotas and usage tracking
7. **audit_logs** - Audit trail for all operations

### Modified Tables

The following tables get a `tenant_id` column added:
- uploaded_files
- processing_jobs
- query_history
- documents
- sessions
- (any other existing tables)

### Default Tenant

A default tenant is created with ID `default-tenant` for backward compatibility. All existing data is assigned to this tenant.

## Migration Safety

The migration scripts are designed to be:
- **Idempotent** - Can be run multiple times safely
- **Non-destructive** - Existing data is preserved
- **Conditional** - Only modifies tables that exist
- **Tracked** - Records which migrations have been applied

## Verification

After running migrations, verify:

```sql
-- Check tenant tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_name LIKE 'tenant%';

-- Check tenant_id columns added
SELECT table_name, column_name 
FROM information_schema.columns 
WHERE column_name = 'tenant_id';

-- Check default tenant created
SELECT * FROM tenants WHERE id = 'default-tenant';

-- Check data integrity
SELECT COUNT(*) FROM uploaded_files WHERE tenant_id IS NULL;
```

## Troubleshooting

### Migration Fails

1. Check database connection:
   ```bash
   psql $DATABASE_URL -c "SELECT version();"
   ```

2. Check migration status:
   ```bash
   python migrations/run_migrations.py status
   ```

3. Review error messages in output

4. If needed, rollback and try again

### Orphaned Data

If you see warnings about orphaned records:
```sql
-- Find records with invalid tenant_id
SELECT * FROM uploaded_files 
WHERE tenant_id NOT IN (SELECT id FROM tenants);

-- Fix by assigning to default tenant
UPDATE uploaded_files 
SET tenant_id = 'default-tenant' 
WHERE tenant_id NOT IN (SELECT id FROM tenants);
```

### Performance Issues

If queries are slow after migration:
```sql
-- Analyze tables to update statistics
ANALYZE tenants;
ANALYZE uploaded_files;
ANALYZE query_history;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan 
FROM pg_stat_user_indexes 
WHERE schemaname = 'public' 
ORDER BY idx_scan;
```

## Backup & Recovery

### Before Migration

Always backup before running migrations:
```bash
pg_dump $DATABASE_URL > backup_before_migration_$(date +%Y%m%d_%H%M%S).sql
```

### Restore from Backup

If something goes wrong:
```bash
psql $DATABASE_URL < backup_before_migration_20251113_123000.sql
```

## Next Steps

After running migrations:

1. Update application code to use tenant_id
2. Test with multiple tenants
3. Verify tenant isolation
4. Update existing queries to filter by tenant_id
5. Migrate Qdrant collections to tenant-specific names

## Support

For issues or questions:
- Check the migration logs
- Review SQL scripts for details
- Consult PostgreSQL documentation
- Test in development environment first
