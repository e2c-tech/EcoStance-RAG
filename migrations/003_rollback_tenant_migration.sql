-- Migration 003: Rollback Script (Emergency Use Only)
-- Description: Removes tenant_id columns and tenant tables
-- Date: 2025-11-13
-- WARNING: This will remove all tenant data! Use only if migration fails.

-- ============================================================================
-- BACKUP REMINDER
-- ============================================================================
-- CRITICAL: Backup your database before running this rollback!
-- pg_dump -U username -d database_name > backup_before_rollback.sql

-- ============================================================================
-- 1. REMOVE tenant_id FROM EXISTING TABLES
-- ============================================================================

-- Remove from uploaded_files
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'uploaded_files' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE uploaded_files DROP CONSTRAINT IF EXISTS fk_uploaded_files_tenant;
        DROP INDEX IF EXISTS idx_uploaded_files_tenant_id;
        DROP INDEX IF EXISTS idx_uploaded_files_tenant_created;
        ALTER TABLE uploaded_files DROP COLUMN tenant_id;
        RAISE NOTICE 'Removed tenant_id from uploaded_files';
    END IF;
END $$;

-- Remove from processing_jobs
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'processing_jobs' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE processing_jobs DROP CONSTRAINT IF EXISTS fk_processing_jobs_tenant;
        DROP INDEX IF EXISTS idx_processing_jobs_tenant_id;
        ALTER TABLE processing_jobs DROP COLUMN tenant_id;
        RAISE NOTICE 'Removed tenant_id from processing_jobs';
    END IF;
END $$;

-- Remove from query_history
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'query_history' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE query_history DROP CONSTRAINT IF EXISTS fk_query_history_tenant;
        DROP INDEX IF EXISTS idx_query_history_tenant_id;
        DROP INDEX IF EXISTS idx_query_history_tenant_created;
        ALTER TABLE query_history DROP COLUMN tenant_id;
        RAISE NOTICE 'Removed tenant_id from query_history';
    END IF;
END $$;

-- Remove from documents
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'documents' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE documents DROP CONSTRAINT IF EXISTS fk_documents_tenant;
        DROP INDEX IF EXISTS idx_documents_tenant_id;
        ALTER TABLE documents DROP COLUMN tenant_id;
        RAISE NOTICE 'Removed tenant_id from documents';
    END IF;
END $$;

-- Remove from sessions
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'sessions' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE sessions DROP CONSTRAINT IF EXISTS fk_sessions_tenant;
        DROP INDEX IF EXISTS idx_sessions_tenant_id;
        ALTER TABLE sessions DROP COLUMN tenant_id;
        RAISE NOTICE 'Removed tenant_id from sessions';
    END IF;
END $$;

-- ============================================================================
-- 2. DROP TENANT TABLES (in correct order due to foreign keys)
-- ============================================================================

DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS tenant_quotas CASCADE;
DROP TABLE IF EXISTS tenant_api_keys CASCADE;
DROP TABLE IF EXISTS tenant_users CASCADE;
DROP TABLE IF EXISTS tenant_knowledge_bases CASCADE;
DROP TABLE IF EXISTS tenant_databases CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;

-- ============================================================================
-- SUMMARY
-- ============================================================================
SELECT 'Rollback Complete - All tenant tables and columns removed' as status;
