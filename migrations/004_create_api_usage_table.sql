-- Migration 004: Create API Usage Tracking Table
-- Purpose: Track API requests, response times, and errors per tenant
-- Date: 2025-11-17

-- Create api_usage table
CREATE TABLE IF NOT EXISTS api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id VARCHAR(36) NOT NULL,
    
    -- Request details
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    
    -- Authentication
    auth_method VARCHAR(50),
    api_key_id VARCHAR(36),
    
    -- Response details
    status_code INTEGER NOT NULL,
    response_time_ms REAL NOT NULL,
    
    -- Error tracking
    error_type VARCHAR(100),
    error_message VARCHAR(500),
    
    -- Additional metadata
    user_agent VARCHAR(255),
    ip_address VARCHAR(50),
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,
    
    -- Timestamp
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_api_usage_tenant_id ON api_usage(tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON api_usage(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_usage_status_code ON api_usage(status_code);
CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_usage(timestamp);
CREATE INDEX IF NOT EXISTS idx_api_usage_tenant_timestamp ON api_usage(tenant_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_api_usage_tenant_endpoint ON api_usage(tenant_id, endpoint);
CREATE INDEX IF NOT EXISTS idx_api_usage_tenant_status ON api_usage(tenant_id, status_code);

-- Add comment
-- This table tracks all API requests for usage analytics, monitoring, and billing purposes
