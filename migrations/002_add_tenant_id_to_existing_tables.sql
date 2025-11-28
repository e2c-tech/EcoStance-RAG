-- Migration 002: Add tenant_id to Existing Tables
-- Description: Adds tenant_id column to all existing tables for multitenancy
-- Date: 2025-11-13
-- Prerequisites: Run 001_create_tenant_tables.sql first

-- ============================================================================
-- BACKUP REMINDER
-- ============================================================================
-- IMPORTANT: Backup your database before running this migration!
-- pg_dump -U username -d database_name > backup_before_migration.sql

-- ============================================================================
-- 1. ADD tenant_id TO uploaded_files TABLE (if exists)
-- ============================================================================
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'uploaded_files') THEN
        -- Add tenant_id column
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'uploaded_files' AND column_name = 'tenant_id'
        ) THEN
            ALTER TABLE uploaded_files 
            ADD COLUMN tenant_id VARCHAR(50);
            
            -- Set default tenant for existing records
            UPDATE uploaded_files 
            SET tenant_id = 'default-tenant' 
            WHERE tenant_id IS NULL;
            
            -- Make it NOT NULL after backfill
            ALTER TABLE uploaded_files 
            ALTER COLUMN tenant_id SET NOT NULL;
            
            -- Add foreign key
            ALTER TABLE uploaded_files 
            ADD CONSTRAINT fk_uploaded_files_tenant 
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
            
            -- Add index
            CREATE INDEX idx_uploaded_files_tenant_id ON uploaded_files(tenant_id);
            
            RAISE NOTICE 'Added tenant_id to uploaded_files table';
        END IF;
    END IF;
END $$;

-- ============================================================================
-- 2. ADD tenant_id TO processing_jobs TABLE (if exists)
-- ============================================================================
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'processing_jobs') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'processing_jobs' AND column_name = 'tenant_id'
        ) THEN
            ALTER TABLE processing_jobs 
            ADD COLUMN tenant_id VARCHAR(50);
            
            UPDATE processing_jobs 
            SET tenant_id = 'default-tenant' 
            WHERE tenant_id IS NULL;
            
            ALTER TABLE processing_jobs 
            ALTER COLUMN tenant_id SET NOT NULL;
            
            ALTER TABLE processing_jobs 
            ADD CONSTRAINT fk_processing_jobs_tenant 
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
            
            CREATE INDEX idx_processing_jobs_tenant_id ON processing_jobs(tenant_id);
            
            RAISE NOTICE 'Added tenant_id to processing_jobs table';
        END IF;
    END IF;
END $$;

-- ============================================================================
-- 3. ADD tenant_id TO query_history TABLE (if exists)
-- ============================================================================
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'query_history') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'query_history' AND column_name = 'tenant_id'
        ) THEN
            ALTER TABLE query_history 
            ADD COLUMN tenant_id VARCHAR(50);
            
            UPDATE query_history 
            SET tenant_id = 'default-tenant' 
            WHERE tenant_id IS NULL;
            
            ALTER TABLE query_history 
            ALTER COLUMN tenant_id SET NOT NULL;
            
            ALTER TABLE query_history 
            ADD CONSTRAINT fk_query_history_tenant 
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
            
            CREATE INDEX idx_query_history_tenant_id ON query_history(tenant_id);
            
            RAISE NOTICE 'Added tenant_id to query_history table';
        END IF;
    END IF;
END $$;

-- ============================================================================
-- 4. ADD tenant_id TO documents TABLE (if exists)
-- ============================================================================
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documents') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'documents' AND column_name = 'tenant_id'
        ) THEN
            ALTER TABLE documents 
            ADD COLUMN tenant_id VARCHAR(50);
            
            UPDATE documents 
            SET tenant_id = 'default-tenant' 
            WHERE tenant_id IS NULL;
            
            ALTER TABLE documents 
            ALTER COLUMN tenant_id SET NOT NULL;
            
            ALTER TABLE documents 
            ADD CONSTRAINT fk_documents_tenant 
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
            
            CREATE INDEX idx_documents_tenant_id ON documents(tenant_id);
            
            RAISE NOTICE 'Added tenant_id to documents table';
        END IF;
    END IF;
END $$;

-- ============================================================================
-- 5. ADD tenant_id TO sessions TABLE (if exists)
-- ============================================================================
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sessions') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'sessions' AND column_name = 'tenant_id'
        ) THEN
            ALTER TABLE sessions 
            ADD COLUMN tenant_id VARCHAR(50);
            
            UPDATE sessions 
            SET tenant_id = 'default-tenant' 
            WHERE tenant_id IS NULL;
            
            ALTER TABLE sessions 
            ALTER COLUMN tenant_id SET NOT NULL;
            
            ALTER TABLE sessions 
            ADD CONSTRAINT fk_sessions_tenant 
            FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
            
            CREATE INDEX idx_sessions_tenant_id ON sessions(tenant_id);
            
            RAISE NOTICE 'Added tenant_id to sessions table';
        END IF;
    END IF;
END $$;

-- ============================================================================
-- 6. CREATE COMPOSITE INDEXES FOR COMMON QUERIES
-- ============================================================================
DO $$ 
BEGIN
    -- uploaded_files: tenant_id + created_at
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'uploaded_files') THEN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'uploaded_files' AND indexname = 'idx_uploaded_files_tenant_created'
        ) THEN
            CREATE INDEX idx_uploaded_files_tenant_created 
            ON uploaded_files(tenant_id, created_at DESC);
        END IF;
    END IF;
    
    -- query_history: tenant_id + created_at
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'query_history') THEN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'query_history' AND indexname = 'idx_query_history_tenant_created'
        ) THEN
            CREATE INDEX idx_query_history_tenant_created 
            ON query_history(tenant_id, created_at DESC);
        END IF;
    END IF;
END $$;

-- ============================================================================
-- 7. VERIFY DATA INTEGRITY
-- ============================================================================
DO $$ 
DECLARE
    table_name TEXT;
    orphan_count INTEGER;
BEGIN
    FOR table_name IN 
        SELECT t.table_name 
        FROM information_schema.tables t
        JOIN information_schema.columns c ON t.table_name = c.table_name
        WHERE c.column_name = 'tenant_id' 
        AND t.table_schema = 'public'
        AND t.table_type = 'BASE TABLE'
    LOOP
        EXECUTE format('
            SELECT COUNT(*) FROM %I 
            WHERE tenant_id NOT IN (SELECT id FROM tenants)
        ', table_name) INTO orphan_count;
        
        IF orphan_count > 0 THEN
            RAISE WARNING 'Table % has % orphaned records with invalid tenant_id', 
                table_name, orphan_count;
        END IF;
    END LOOP;
END $$;

-- ============================================================================
-- SUMMARY
-- ============================================================================
SELECT 
    'Migration 002 Complete' as status,
    COUNT(*) as tables_with_tenant_id
FROM information_schema.columns 
WHERE column_name = 'tenant_id' 
AND table_schema = 'public';
