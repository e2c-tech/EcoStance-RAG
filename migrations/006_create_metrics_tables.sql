-- Migration 006: Create tenant metrics tables
-- Purpose: Track detailed metrics for monitoring and analytics

-- Tenant metrics table (aggregated hourly/daily)
CREATE TABLE IF NOT EXISTS tenant_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    
    -- Time period
    metric_type TEXT NOT NULL, -- 'hourly', 'daily', 'monthly'
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    
    -- Storage metrics
    storage_bytes INTEGER DEFAULT 0,
    document_count INTEGER DEFAULT 0,
    collection_count INTEGER DEFAULT 0,
    
    -- Query metrics
    query_count INTEGER DEFAULT 0,
    query_success_count INTEGER DEFAULT 0,
    query_error_count INTEGER DEFAULT 0,
    avg_query_time_ms REAL DEFAULT 0,
    p50_query_time_ms REAL DEFAULT 0,
    p95_query_time_ms REAL DEFAULT 0,
    p99_query_time_ms REAL DEFAULT 0,
    
    -- API metrics
    api_call_count INTEGER DEFAULT 0,
    api_success_count INTEGER DEFAULT 0,
    api_error_count INTEGER DEFAULT 0,
    avg_response_time_ms REAL DEFAULT 0,
    
    -- Database connection metrics
    db_connection_count INTEGER DEFAULT 0,
    avg_connection_time_ms REAL DEFAULT 0,
    
    -- Cost metrics (if applicable)
    estimated_cost REAL DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    UNIQUE(tenant_id, metric_type, period_start)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_metrics_tenant_period 
    ON tenant_metrics(tenant_id, metric_type, period_start);

CREATE INDEX IF NOT EXISTS idx_metrics_period_end 
    ON tenant_metrics(period_end);

-- Tenant alerts configuration
CREATE TABLE IF NOT EXISTS tenant_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    
    -- Alert configuration
    alert_type TEXT NOT NULL, -- 'quota_warning', 'high_error_rate', 'slow_queries', etc.
    threshold_value REAL NOT NULL,
    threshold_unit TEXT NOT NULL, -- 'percentage', 'count', 'milliseconds', etc.
    
    -- Alert channels
    email_enabled BOOLEAN DEFAULT TRUE,
    webhook_url TEXT,
    
    -- Alert status
    is_active BOOLEAN DEFAULT TRUE,
    last_triggered_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- Alert history table
CREATE TABLE IF NOT EXISTS alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    alert_id INTEGER NOT NULL,
    
    -- Alert details
    alert_type TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT NOT NULL, -- 'info', 'warning', 'critical'
    
    -- Alert data
    metric_value REAL,
    threshold_value REAL,
    
    -- Status
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    
    -- Timestamps
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (alert_id) REFERENCES tenant_alerts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_alert_history_tenant 
    ON alert_history(tenant_id, triggered_at);
