-- Migration 001: Create Tenant Tables
-- Description: Creates all tenant-related tables for multitenancy support
-- Date: 2025-11-13

-- ============================================================================
-- 1. TENANTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    settings JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT tenants_name_unique UNIQUE (name)
);

CREATE INDEX idx_tenants_is_active ON tenants(is_active);
CREATE INDEX idx_tenants_created_at ON tenants(created_at);

COMMENT ON TABLE tenants IS 'Main tenant table storing tenant information';
COMMENT ON COLUMN tenants.settings IS 'JSON settings including quotas, features, permissions';

-- ============================================================================
-- 2. TENANT_DATABASES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenant_databases (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL,
    db_name VARCHAR(255) NOT NULL,
    db_type VARCHAR(50) NOT NULL,
    db_uri_encrypted TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    connection_settings JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT fk_tenant_databases_tenant FOREIGN KEY (tenant_id) 
        REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT tenant_databases_unique UNIQUE (tenant_id, db_name)
);

CREATE INDEX idx_tenant_databases_tenant_id ON tenant_databases(tenant_id);
CREATE INDEX idx_tenant_databases_is_active ON tenant_databases(is_active);

COMMENT ON TABLE tenant_databases IS 'Stores encrypted database connection information per tenant';
COMMENT ON COLUMN tenant_databases.db_uri_encrypted IS 'Encrypted database connection URI';

-- ============================================================================
-- 3. TENANT_KNOWLEDGE_BASES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenant_knowledge_bases (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL,
    kb_name VARCHAR(255) NOT NULL,
    collection_name VARCHAR(255) NOT NULL,
    document_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT fk_tenant_knowledge_bases_tenant FOREIGN KEY (tenant_id) 
        REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT tenant_knowledge_bases_unique UNIQUE (tenant_id, kb_name)
);

CREATE INDEX idx_tenant_knowledge_bases_tenant_id ON tenant_knowledge_bases(tenant_id);
CREATE INDEX idx_tenant_knowledge_bases_collection_name ON tenant_knowledge_bases(collection_name);
CREATE INDEX idx_tenant_knowledge_bases_is_active ON tenant_knowledge_bases(is_active);

COMMENT ON TABLE tenant_knowledge_bases IS 'Maps tenant knowledge bases to Qdrant collections';

-- ============================================================================
-- 4. TENANT_USERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenant_users (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    permissions JSONB DEFAULT '[]'::jsonb,
    CONSTRAINT fk_tenant_users_tenant FOREIGN KEY (tenant_id) 
        REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT tenant_users_unique UNIQUE (tenant_id, user_id)
);

CREATE INDEX idx_tenant_users_tenant_id ON tenant_users(tenant_id);
CREATE INDEX idx_tenant_users_user_id ON tenant_users(user_id);
CREATE INDEX idx_tenant_users_role ON tenant_users(role);

COMMENT ON TABLE tenant_users IS 'Maps users to tenants with roles and permissions';
COMMENT ON COLUMN tenant_users.role IS 'User role: admin, manager, user';

-- ============================================================================
-- 5. TENANT_API_KEYS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenant_api_keys (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL,
    key_name VARCHAR(255) NOT NULL,
    key_hash TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    permissions JSONB DEFAULT '[]'::jsonb,
    CONSTRAINT fk_tenant_api_keys_tenant FOREIGN KEY (tenant_id) 
        REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT tenant_api_keys_unique UNIQUE (tenant_id, key_name)
);

CREATE INDEX idx_tenant_api_keys_tenant_id ON tenant_api_keys(tenant_id);
CREATE INDEX idx_tenant_api_keys_key_hash ON tenant_api_keys(key_hash);
CREATE INDEX idx_tenant_api_keys_is_active ON tenant_api_keys(is_active);

COMMENT ON TABLE tenant_api_keys IS 'Stores hashed API keys for tenant authentication';
COMMENT ON COLUMN tenant_api_keys.key_hash IS 'Hashed API key (never store plain text)';

-- ============================================================================
-- 6. TENANT_QUOTAS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenant_quotas (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL,
    quota_type VARCHAR(50) NOT NULL,
    quota_limit BIGINT NOT NULL,
    quota_used BIGINT NOT NULL DEFAULT 0,
    reset_period VARCHAR(20) NOT NULL DEFAULT 'monthly',
    last_reset_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tenant_quotas_tenant FOREIGN KEY (tenant_id) 
        REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT tenant_quotas_unique UNIQUE (tenant_id, quota_type)
);

CREATE INDEX idx_tenant_quotas_tenant_id ON tenant_quotas(tenant_id);
CREATE INDEX idx_tenant_quotas_quota_type ON tenant_quotas(quota_type);

COMMENT ON TABLE tenant_quotas IS 'Tracks resource quotas and usage per tenant';
COMMENT ON COLUMN tenant_quotas.quota_type IS 'Type: storage, queries, documents, connections';
COMMENT ON COLUMN tenant_quotas.reset_period IS 'Reset period: daily, monthly, never';

-- ============================================================================
-- 7. AUDIT_LOGS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(50),
    user_id VARCHAR(50),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    details JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_logs_tenant FOREIGN KEY (tenant_id) 
        REFERENCES tenants(id) ON DELETE SET NULL
);

CREATE INDEX idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

COMMENT ON TABLE audit_logs IS 'Audit trail for all tenant operations';
COMMENT ON COLUMN audit_logs.action IS 'Action performed: create, update, delete, login, etc.';

-- ============================================================================
-- 8. CREATE DEFAULT TENANT
-- ============================================================================
INSERT INTO tenants (id, name, is_active, settings)
VALUES (
    'default-tenant',
    'Default Tenant',
    TRUE,
    '{"permissions": ["admin", "upload", "query", "manage_db"], "feature_flags": {}, "quotas": {"storage_mb": 10000, "queries_per_day": 10000}}'::jsonb
)
ON CONFLICT (id) DO NOTHING;

COMMENT ON TABLE tenants IS 'Default tenant created for backward compatibility';
