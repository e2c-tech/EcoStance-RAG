-- Migration: Create Public Chat Tables (PostgreSQL)
-- Description: Creates tables for public chat configuration, sessions, messages, and feedback
-- Date: 2024-11-24

-- Table: public_chat_configs
-- Stores configuration for public chat feature per tenant
CREATE TABLE IF NOT EXISTS public_chat_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    allowed_kbs JSONB DEFAULT '[]'::jsonb,
    welcome_message TEXT NOT NULL DEFAULT 'Hi! How can I help you today?',
    suggested_questions JSONB DEFAULT '[]'::jsonb,
    branding JSONB NOT NULL DEFAULT '{}'::jsonb,
    rate_limit JSONB NOT NULL DEFAULT '{"queries_per_minute": 10, "max_messages_per_session": 50}'::jsonb,
    features JSONB NOT NULL DEFAULT '{"show_sources": true, "allow_feedback": true, "show_suggested_questions": true}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    UNIQUE(tenant_id)
);

-- Table: public_chat_sessions
-- Stores individual chat sessions
CREATE TABLE IF NOT EXISTS public_chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    tenant_id UUID NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    query_count INTEGER DEFAULT 0,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_public_chat_sessions_tenant ON public_chat_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_public_chat_sessions_started ON public_chat_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_public_chat_sessions_last_activity ON public_chat_sessions(last_activity);

-- Table: public_chat_messages
-- Stores individual messages in chat sessions
CREATE TABLE IF NOT EXISTS public_chat_messages (
    id VARCHAR(100) PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    tenant_id UUID NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources JSONB,
    feedback VARCHAR(20) CHECK (feedback IN ('positive', 'negative', NULL)),
    feedback_comment TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES public_chat_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_public_chat_messages_session ON public_chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_public_chat_messages_tenant ON public_chat_messages(tenant_id);
CREATE INDEX IF NOT EXISTS idx_public_chat_messages_timestamp ON public_chat_messages(timestamp);

-- Table: public_chat_feedback
-- Stores feedback for messages (optional, for analytics)
CREATE TABLE IF NOT EXISTS public_chat_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(100) NOT NULL,
    message_id VARCHAR(100) NOT NULL,
    tenant_id UUID NOT NULL,
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('positive', 'negative')),
    comment TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_public_chat_feedback_tenant ON public_chat_feedback(tenant_id);
CREATE INDEX IF NOT EXISTS idx_public_chat_feedback_timestamp ON public_chat_feedback(timestamp);
CREATE INDEX IF NOT EXISTS idx_public_chat_feedback_message ON public_chat_feedback(message_id);
