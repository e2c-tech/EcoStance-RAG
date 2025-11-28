-- Migration 009: Create Public Agent Tables (PostgreSQL)
-- Creates tables for public agent feature (database + KB access)

-- Table: public_agent_configs
-- Configuration for public agent feature per tenant
CREATE TABLE IF NOT EXISTS public_agent_configs (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id VARCHAR(36) NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT true NOT NULL,
    allowed_kbs TEXT DEFAULT '[]' NOT NULL,  -- JSON array
    allowed_dbs TEXT DEFAULT '[]' NOT NULL,  -- JSON array
    welcome_message TEXT NOT NULL DEFAULT 'Hi! How can I help you today?',
    suggested_questions TEXT DEFAULT '[]' NOT NULL,  -- JSON array
    branding TEXT NOT NULL DEFAULT '{}',  -- JSON object
    rate_limit TEXT NOT NULL DEFAULT '{"queries_per_minute": 10, "max_messages_per_session": 50}',  -- JSON object
    features TEXT NOT NULL DEFAULT '{"show_sources": true, "allow_feedback": true, "show_suggested_questions": true, "enable_database_tools": true, "enable_knowledge_base": true}',  -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_public_agent_configs_tenant ON public_agent_configs(tenant_id);

-- Table: public_agent_sessions
-- Individual agent sessions
CREATE TABLE IF NOT EXISTS public_agent_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    message_count INTEGER DEFAULT 0 NOT NULL,
    query_count INTEGER DEFAULT 0 NOT NULL,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    metadata TEXT DEFAULT '{}',  -- JSON object
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_public_agent_sessions_tenant ON public_agent_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_public_agent_sessions_started ON public_agent_sessions(tenant_id, started_at);
CREATE INDEX IF NOT EXISTS idx_public_agent_sessions_activity ON public_agent_sessions(last_activity);

-- Table: public_agent_messages
-- Individual messages in agent sessions
CREATE TABLE IF NOT EXISTS public_agent_messages (
    id VARCHAR(100) PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    tenant_id VARCHAR(36) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources TEXT,  -- JSON array
    tool_used VARCHAR(50),  -- Which tool was used (database/knowledge_base)
    feedback VARCHAR(20) CHECK(feedback IN ('positive', 'negative') OR feedback IS NULL),
    feedback_comment TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (session_id) REFERENCES public_agent_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_public_agent_messages_session ON public_agent_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_public_agent_messages_tenant ON public_agent_messages(tenant_id, timestamp);

-- Table: public_agent_feedback
-- Feedback submitted by users
CREATE TABLE IF NOT EXISTS public_agent_feedback (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id VARCHAR(100) NOT NULL,
    message_id VARCHAR(100) NOT NULL,
    tenant_id VARCHAR(36) NOT NULL,
    feedback_type VARCHAR(20) NOT NULL CHECK(feedback_type IN ('positive', 'negative')),
    comment TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (message_id) REFERENCES public_agent_messages(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_public_agent_feedback_tenant ON public_agent_feedback(tenant_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_public_agent_feedback_message ON public_agent_feedback(message_id);
