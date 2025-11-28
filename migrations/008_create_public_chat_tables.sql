-- Migration: Create Public Chat Tables
-- Description: Creates tables for public chat configuration, sessions, messages, and feedback
-- Date: 2024-11-24

-- Table: public_chat_configs
-- Stores configuration for public chat feature per tenant
CREATE TABLE IF NOT EXISTS public_chat_configs (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    tenant_id TEXT NOT NULL,
    enabled BOOLEAN DEFAULT 1,
    allowed_kbs TEXT DEFAULT '[]',  -- JSON array of KB IDs
    welcome_message TEXT NOT NULL DEFAULT 'Hi! How can I help you today?',
    suggested_questions TEXT DEFAULT '[]',  -- JSON array of questions
    branding TEXT NOT NULL DEFAULT '{}',  -- JSON object with logo, primary_color, company_name
    rate_limit TEXT NOT NULL DEFAULT '{"queries_per_minute": 10, "max_messages_per_session": 50}',  -- JSON object
    features TEXT NOT NULL DEFAULT '{"show_sources": true, "allow_feedback": true, "show_suggested_questions": true}',  -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    UNIQUE(tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_public_chat_configs_tenant ON public_chat_configs(tenant_id);

-- Table: public_chat_sessions
-- Stores individual chat sessions
CREATE TABLE IF NOT EXISTS public_chat_sessions (
    session_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    query_count INTEGER DEFAULT 0,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT DEFAULT '{}',  -- JSON object with user_agent, ip_address, referrer
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_public_chat_sessions_tenant_started ON public_chat_sessions(tenant_id, started_at);
CREATE INDEX IF NOT EXISTS idx_public_chat_sessions_last_activity ON public_chat_sessions(last_activity);

-- Table: public_chat_messages
-- Stores individual messages in chat sessions
CREATE TABLE IF NOT EXISTS public_chat_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources TEXT,  -- JSON array of source objects
    feedback TEXT CHECK(feedback IN ('positive', 'negative', NULL)),
    feedback_comment TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES public_chat_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_public_chat_messages_session ON public_chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_public_chat_messages_tenant_timestamp ON public_chat_messages(tenant_id, timestamp);

-- Table: public_chat_feedback
-- Stores feedback submitted by users
CREATE TABLE IF NOT EXISTS public_chat_feedback (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    session_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    feedback_type TEXT NOT NULL CHECK(feedback_type IN ('positive', 'negative')),
    comment TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES public_chat_messages(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_public_chat_feedback_tenant_timestamp ON public_chat_feedback(tenant_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_public_chat_feedback_message ON public_chat_feedback(message_id);

-- Insert default configuration for existing tenants
INSERT INTO public_chat_configs (tenant_id, enabled, welcome_message, branding, rate_limit, features)
SELECT 
    id,
    0,  -- Disabled by default
    'Hi! How can I help you today?',
    '{"primary_color": "#0066CC", "company_name": "' || name || '"}',
    '{"queries_per_minute": 10, "max_messages_per_session": 50}',
    '{"show_sources": true, "allow_feedback": true, "show_suggested_questions": true}'
FROM tenants
WHERE NOT EXISTS (SELECT 1 FROM public_chat_configs WHERE public_chat_configs.tenant_id = tenants.id);
