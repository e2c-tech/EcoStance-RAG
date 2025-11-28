-- Migration 005: Create quota tracking tables
-- Purpose: Track tenant resource usage and enforce quotas

-- Tenant quota configuration table
CREATE TABLE IF NOT EXISTS tenant_quotas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    
    -- Query quotas
    max_queries_per_day INTEGER DEFAULT 1000,
    max_queries_per_month INTEGER DEFAULT 30000,
    
    -- Document quotas
    max_documents INTEGER DEFAULT 10000,
    max_storage_bytes INTEGER DEFAULT 10737418240, -- 10GB default
    
    -- Connection quotas
    max_db_connections INTEGER DEFAULT 5,
    max_concurrent_queries INTEGER DEFAULT 10,
    
    -- API quotas
    max_api_calls_per_minute INTEGER DEFAULT 60,
    max_api_calls_per_hour INTEGER DEFAULT 3600,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    UNIQUE(tenant_id)
);

-- Tenant quota usage tracking table
CREATE TABLE IF NOT EXISTS tenant_quota_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    
    -- Usage period
    period_type TEXT NOT NULL, -- 'daily', 'monthly', 'hourly'
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    
    -- Query usage
    query_count INTEGER DEFAULT 0,
    
    -- Document usage
    document_count INTEGER DEFAULT 0,
    storage_bytes INTEGER DEFAULT 0,
    
    -- Connection usage
    active_db_connections INTEGER DEFAULT 0,
    concurrent_queries INTEGER DEFAULT 0,
    
    -- API usage
    api_calls_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    UNIQUE(tenant_id, period_type, period_start)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_quota_usage_tenant_period 
    ON tenant_quota_usage(tenant_id, period_type, period_start);

CREATE INDEX IF NOT EXISTS idx_quota_usage_period_end 
    ON tenant_quota_usage(period_end);

-- Insert default quotas for existing tenants
INSERT OR IGNORE INTO tenant_quotas (tenant_id)
SELECT id FROM tenants WHERE id NOT IN (SELECT tenant_id FROM tenant_quotas);
