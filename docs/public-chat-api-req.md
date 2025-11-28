# Public Chat Configuration - API Specification

## Overview

This document specifies all backend API endpoints required for the Public Chat feature, including both the customer-facing chat interface and the admin configuration panel.

---

## Table of Contents

1. [Public Chat Endpoints](#public-chat-endpoints)
2. [Admin Configuration Endpoints](#admin-configuration-endpoints)
3. [Analytics Endpoints](#analytics-endpoints)
4. [Data Models](#data-models)
5. [Authentication](#authentication)
6. [Rate Limiting](#rate-limiting)
7. [Error Handling](#error-handling)

---

## Public Chat Endpoints

### 1. Query Public Chat

**Purpose:** Send a customer query to the public chat and get an AI response

**Endpoint:** `POST /api/v1/public-chat/query`

**Authentication:** None (public endpoint)

**Request Body:**
```json
{
  "session_id": "session-1732456789-abc123",
  "query": "What is your refund policy?",
  "conversation_history": [
    {
      "role": "user",
      "content": "Hello"
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help you today?"
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "answer": "Our refund policy allows returns within 30 days of purchase...",
  "sources": [
    {
      "filename": "customer-support-faq.pdf",
      "chunk_number": 3,
      "similarity": 0.89,
      "preview": "This section covers common customer questions and provides detailed answers..."
    }
  ],
  "session_id": "session-1732456789-abc123",
  "timestamp": "2024-11-24T10:30:00Z"
}
```

**Response (429 Too Many Requests):**
```json
{
  "detail": "Rate limit exceeded. Please wait before sending another message.",
  "retry_after": 60
}
```

**Response (503 Service Unavailable):**
```json
{
  "detail": "Public chat is currently disabled."
}
```

**Business Logic:**
- Check if public chat is enabled
- Validate session_id format
- Check rate limits (queries per minute, max messages per session)
- Query only allowed knowledge bases
- Return answer with optional sources
- Track session for rate limiting

---

### 2. Get Public Chat Configuration

**Purpose:** Get the current public chat configuration (for rendering the UI)

**Endpoint:** `GET /api/v1/public-chat/config`

**Authentication:** None (public endpoint)

**Response (200 OK):**
```json
{
  "enabled": true,
  "welcome_message": "Hi! How can I help you today?",
  "suggested_questions": [
    "What is your refund policy?",
    "How do I track my order?",
    "What are your business hours?",
    "How do I contact support?"
  ],
  "branding": {
    "logo": "https://example.com/logo.png",
    "primary_color": "#0066CC",
    "company_name": "Your Company"
  },
  "rate_limit": {
    "queries_per_minute": 10,
    "max_messages_per_session": 50
  },
  "features": {
    "show_sources": true,
    "allow_feedback": true,
    "show_suggested_questions": true
  }
}
```

**Response (503 Service Unavailable):**
```json
{
  "enabled": false,
  "message": "Public chat is currently disabled."
}
```

**Business Logic:**
- Return current configuration
- Exclude sensitive data (allowed_kbs, internal settings)
- Cache this response (5 minutes)

---

### 3. Submit Feedback

**Purpose:** Allow customers to rate responses (thumbs up/down)

**Endpoint:** `POST /api/v1/public-chat/feedback`

**Authentication:** None (public endpoint)

**Request Body:**
```json
{
  "session_id": "session-1732456789-abc123",
  "message_id": "msg-1732456790-response",
  "feedback_type": "positive",
  "comment": "Very helpful!"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Thank you for your feedback!"
}
```

**Business Logic:**
- Validate session_id and message_id
- Store feedback for analytics
- feedback_type: "positive" or "negative"
- comment is optional

---

## Admin Configuration Endpoints

### 4. Get Admin Configuration

**Purpose:** Get the full public chat configuration for admin panel

**Endpoint:** `GET /api/v1/admin/public-chat/config`

**Authentication:** Required (Bearer token)

**Authorization:** Admin or Super Admin role

**Response (200 OK):**
```json
{
  "enabled": true,
  "allowed_kbs": ["kb-2", "kb-4"],
  "welcome_message": "Hi! How can I help you today?",
  "suggested_questions": [
    "What is your refund policy?",
    "How do I track my order?",
    "What are your business hours?",
    "How do I contact support?"
  ],
  "branding": {
    "logo": "https://example.com/logo.png",
    "primary_color": "#0066CC",
    "company_name": "Your Company"
  },
  "rate_limit": {
    "queries_per_minute": 10,
    "max_messages_per_session": 50
  },
  "features": {
    "show_sources": true,
    "allow_feedback": true,
    "show_suggested_questions": true
  },
  "created_at": "2024-11-01T10:00:00Z",
  "updated_at": "2024-11-24T10:30:00Z",
  "updated_by": "admin@example.com"
}
```

**Response (401 Unauthorized):**
```json
{
  "detail": "Authentication required"
}
```

**Response (403 Forbidden):**
```json
{
  "detail": "Admin privileges required"
}
```

**Business Logic:**
- Verify user is authenticated
- Check user has admin role
- Return full configuration including allowed_kbs
- Include audit fields (created_at, updated_at, updated_by)

---

### 5. Update Admin Configuration

**Purpose:** Update the public chat configuration

**Endpoint:** `PUT /api/v1/admin/public-chat/config`

**Authentication:** Required (Bearer token)

**Authorization:** Admin or Super Admin role

**Request Body:**
```json
{
  "enabled": true,
  "allowed_kbs": ["kb-2", "kb-4"],
  "welcome_message": "Hi! How can I help you today?",
  "suggested_questions": [
    "What is your refund policy?",
    "How do I track my order?",
    "What are your business hours?",
    "How do I contact support?"
  ],
  "branding": {
    "logo": "https://example.com/logo.png",
    "primary_color": "#0066CC",
    "company_name": "Your Company"
  },
  "rate_limit": {
    "queries_per_minute": 10,
    "max_messages_per_session": 50
  },
  "features": {
    "show_sources": true,
    "allow_feedback": true,
    "show_suggested_questions": true
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Configuration updated successfully",
  "config": {
    "enabled": true,
    "allowed_kbs": ["kb-2", "kb-4"],
    "welcome_message": "Hi! How can I help you today?",
    "suggested_questions": [...],
    "branding": {...},
    "rate_limit": {...},
    "features": {...},
    "updated_at": "2024-11-24T10:30:00Z",
    "updated_by": "admin@example.com"
  }
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "Invalid configuration",
  "errors": {
    "queries_per_minute": "Must be between 1 and 100",
    "suggested_questions": "Maximum 10 questions allowed"
  }
}
```

**Validation Rules:**
- `enabled`: boolean
- `allowed_kbs`: array of valid KB IDs (must exist)
- `welcome_message`: string, 1-500 characters
- `suggested_questions`: array, max 10 items, each 1-200 characters
- `branding.logo`: valid URL or null
- `branding.primary_color`: valid hex color (#RRGGBB)
- `branding.company_name`: string, 1-100 characters
- `rate_limit.queries_per_minute`: integer, 1-100
- `rate_limit.max_messages_per_session`: integer, 1-200
- `features.*`: boolean

**Business Logic:**
- Verify user is authenticated
- Check user has admin role
- Validate all fields
- Verify allowed_kbs exist and are accessible
- Update configuration in database
- Clear public config cache
- Log audit trail (who, when, what changed)

---

### 6. Get Available Knowledge Bases

**Purpose:** Get list of knowledge bases that can be selected for public chat

**Endpoint:** `GET /api/v1/admin/public-chat/available-kbs`

**Authentication:** Required (Bearer token)

**Authorization:** Admin or Super Admin role

**Response (200 OK):**
```json
{
  "knowledge_bases": [
    {
      "id": "kb-1",
      "name": "Product Documentation",
      "document_count": 150,
      "is_public": false,
      "created_at": "2024-10-01T10:00:00Z"
    },
    {
      "id": "kb-2",
      "name": "Customer Support FAQs",
      "document_count": 75,
      "is_public": true,
      "created_at": "2024-10-15T10:00:00Z"
    },
    {
      "id": "kb-3",
      "name": "Company Policies",
      "document_count": 25,
      "is_public": false,
      "created_at": "2024-11-01T10:00:00Z"
    }
  ]
}
```

**Business Logic:**
- Return all knowledge bases for the tenant
- Include metadata (document count, is_public flag)
- Sort by name or creation date

---

## Analytics Endpoints

### 7. Get Public Chat Analytics

**Purpose:** Get usage statistics and analytics for public chat

**Endpoint:** `GET /api/v1/admin/public-chat/analytics`

**Authentication:** Required (Bearer token)

**Authorization:** Admin or Super Admin role

**Query Parameters:**
- `days` (optional): Number of days to include (default: 30)
- `start_date` (optional): Start date (ISO 8601)
- `end_date` (optional): End date (ISO 8601)

**Response (200 OK):**
```json
{
  "period": {
    "start_date": "2024-10-25T00:00:00Z",
    "end_date": "2024-11-24T23:59:59Z",
    "days": 30
  },
  "summary": {
    "total_sessions": 1250,
    "total_queries": 3840,
    "unique_visitors": 980,
    "average_queries_per_session": 3.07,
    "average_rating": 4.2
  },
  "top_questions": [
    {
      "question": "What is your refund policy?",
      "count": 245,
      "percentage": 6.4
    },
    {
      "question": "How do I track my order?",
      "count": 198,
      "percentage": 5.2
    },
    {
      "question": "What are your business hours?",
      "count": 156,
      "percentage": 4.1
    }
  ],
  "feedback_summary": {
    "total_feedback": 890,
    "positive": 756,
    "negative": 134,
    "positive_percentage": 85.0
  },
  "usage_by_day": [
    {
      "date": "2024-11-24",
      "sessions": 45,
      "queries": 138,
      "positive_feedback": 28,
      "negative_feedback": 5
    }
  ],
  "rate_limit_hits": {
    "queries_per_minute": 23,
    "max_messages_per_session": 8
  }
}
```

**Business Logic:**
- Aggregate data for specified period
- Calculate averages and percentages
- Identify top questions (by frequency)
- Summarize feedback ratings
- Track rate limit violations

---

### 8. Get Session Details

**Purpose:** Get detailed information about a specific session

**Endpoint:** `GET /api/v1/admin/public-chat/sessions/{session_id}`

**Authentication:** Required (Bearer token)

**Authorization:** Admin or Super Admin role

**Response (200 OK):**
```json
{
  "session_id": "session-1732456789-abc123",
  "started_at": "2024-11-24T10:00:00Z",
  "ended_at": "2024-11-24T10:15:00Z",
  "duration_seconds": 900,
  "message_count": 8,
  "messages": [
    {
      "id": "msg-1",
      "role": "assistant",
      "content": "Hi! How can I help you today?",
      "timestamp": "2024-11-24T10:00:00Z"
    },
    {
      "id": "msg-2",
      "role": "user",
      "content": "What is your refund policy?",
      "timestamp": "2024-11-24T10:00:15Z"
    },
    {
      "id": "msg-3",
      "role": "assistant",
      "content": "Our refund policy allows...",
      "timestamp": "2024-11-24T10:00:18Z",
      "sources": [
        {
          "filename": "customer-support-faq.pdf",
          "chunk_number": 3,
          "similarity": 0.89
        }
      ],
      "feedback": "positive"
    }
  ],
  "metadata": {
    "user_agent": "Mozilla/5.0...",
    "ip_address": "192.168.1.1",
    "referrer": "https://example.com"
  }
}
```

**Business Logic:**
- Return full conversation history
- Include feedback for each message
- Include metadata for analytics
- Respect privacy settings (anonymize if needed)

---

## Data Models

### PublicChatConfig

```typescript
interface PublicChatConfig {
  id: string;
  tenant_id: string;
  enabled: boolean;
  allowed_kbs: string[];
  welcome_message: string;
  suggested_questions: string[];
  branding: {
    logo?: string;
    primary_color: string;
    company_name: string;
  };
  rate_limit: {
    queries_per_minute: number;
    max_messages_per_session: number;
  };
  features: {
    show_sources: boolean;
    allow_feedback: boolean;
    show_suggested_questions: boolean;
  };
  created_at: string;
  updated_at: string;
  updated_by: string;
}
```

### PublicChatSession

```typescript
interface PublicChatSession {
  session_id: string;
  tenant_id: string;
  started_at: string;
  ended_at?: string;
  message_count: number;
  query_count: number;
  last_activity: string;
  metadata: {
    user_agent?: string;
    ip_address?: string;
    referrer?: string;
  };
}
```

### PublicChatMessage

```typescript
interface PublicChatMessage {
  id: string;
  session_id: string;
  tenant_id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  feedback?: 'positive' | 'negative';
  feedback_comment?: string;
  timestamp: string;
}
```

### PublicChatFeedback

```typescript
interface PublicChatFeedback {
  id: string;
  session_id: string;
  message_id: string;
  tenant_id: string;
  feedback_type: 'positive' | 'negative';
  comment?: string;
  timestamp: string;
}
```

---

## Authentication

### Public Endpoints
- No authentication required
- Rate limited by session_id and IP address
- CORS enabled for all origins

### Admin Endpoints
- Bearer token authentication required
- User must have admin or super_admin role
- Standard CORS policy (authenticated origins only)

**Example Header:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Rate Limiting

### Public Chat Query Endpoint

**Per Session:**
- Configurable queries per minute (default: 10)
- Configurable max messages per session (default: 50)
- Session expires after 24 hours of inactivity

**Per IP Address:**
- 100 queries per hour (global limit)
- 1000 queries per day (global limit)

**Response Headers:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1732456800
```

### Admin Endpoints

**Standard Rate Limits:**
- 100 requests per minute per user
- 1000 requests per hour per user

---

## Error Handling

### Standard Error Response

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-11-24T10:30:00Z"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `PUBLIC_CHAT_DISABLED` | 503 | Public chat is disabled |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INVALID_SESSION` | 400 | Invalid session_id format |
| `SESSION_EXPIRED` | 400 | Session has expired |
| `INVALID_CONFIG` | 400 | Invalid configuration data |
| `KB_NOT_FOUND` | 404 | Knowledge base not found |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `INTERNAL_ERROR` | 500 | Internal server error |

---

## Database Schema

### Table: public_chat_configs

```sql
CREATE TABLE public_chat_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    enabled BOOLEAN DEFAULT true,
    allowed_kbs TEXT[] DEFAULT '{}',
    welcome_message TEXT NOT NULL,
    suggested_questions TEXT[] DEFAULT '{}',
    branding JSONB NOT NULL,
    rate_limit JSONB NOT NULL,
    features JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(255),
    UNIQUE(tenant_id)
);
```

### Table: public_chat_sessions

```sql
CREATE TABLE public_chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    query_count INTEGER DEFAULT 0,
    last_activity TIMESTAMP DEFAULT NOW(),
    metadata JSONB,
    INDEX idx_tenant_started (tenant_id, started_at),
    INDEX idx_last_activity (last_activity)
);
```

### Table: public_chat_messages

```sql
CREATE TABLE public_chat_messages (
    id VARCHAR(100) PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL REFERENCES public_chat_sessions(session_id),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    sources JSONB,
    feedback VARCHAR(20),
    feedback_comment TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    INDEX idx_session (session_id),
    INDEX idx_tenant_timestamp (tenant_id, timestamp)
);
```

### Table: public_chat_feedback

```sql
CREATE TABLE public_chat_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(100) NOT NULL,
    message_id VARCHAR(100) NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    feedback_type VARCHAR(20) NOT NULL,
    comment TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    INDEX idx_tenant_timestamp (tenant_id, timestamp),
    INDEX idx_message (message_id)
);
```

---

## Implementation Checklist

### Backend Tasks

- [ ] Create database tables
- [ ] Implement PublicChatConfig model
- [ ] Implement PublicChatSession model
- [ ] Implement PublicChatMessage model
- [ ] Implement PublicChatFeedback model
- [ ] Create public chat query endpoint
- [ ] Create get public config endpoint
- [ ] Create submit feedback endpoint
- [ ] Create get admin config endpoint
- [ ] Create update admin config endpoint
- [ ] Create get available KBs endpoint
- [ ] Create analytics endpoint
- [ ] Create session details endpoint
- [ ] Implement rate limiting logic
- [ ] Implement session management
- [ ] Add CORS configuration
- [ ] Add input validation
- [ ] Add error handling
- [ ] Add audit logging
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Add API documentation (Swagger)

### Frontend Tasks

- [x] Public chat page UI
- [x] Admin config page UI
- [ ] Connect to query endpoint
- [ ] Connect to config endpoint
- [ ] Connect to feedback endpoint
- [ ] Connect to admin endpoints
- [ ] Add error handling
- [ ] Add loading states
- [ ] Test rate limiting
- [ ] Test all features

---

## Testing

### Manual Testing

**Public Chat:**
```bash
# Get config
curl http://localhost:8000/api/v1/public-chat/config

# Send query
curl -X POST http://localhost:8000/api/v1/public-chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-123",
    "query": "What is your refund policy?"
  }'

# Submit feedback
curl -X POST http://localhost:8000/api/v1/public-chat/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-123",
    "message_id": "msg-123",
    "feedback_type": "positive"
  }'
```

**Admin Endpoints:**
```bash
# Get admin config
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/admin/public-chat/config

# Update config
curl -X PUT \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, ...}' \
  http://localhost:8000/api/v1/admin/public-chat/config

# Get analytics
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/admin/public-chat/analytics?days=30
```

---

## Security Considerations

### Public Endpoints
- Rate limiting to prevent abuse
- Input sanitization to prevent injection
- Session validation
- IP-based throttling
- No sensitive data in responses

### Admin Endpoints
- Authentication required
- Role-based access control
- Audit logging for all changes
- Input validation
- CSRF protection

### Data Privacy
- No PII collection without consent
- Session data retention policy (30 days)
- Anonymize IP addresses in logs
- GDPR compliance considerations

---

## Performance Considerations

### Caching
- Cache public config (5 minutes)
- Cache available KBs list (10 minutes)
- Cache analytics data (1 hour)

### Database Optimization
- Index on tenant_id, session_id, timestamp
- Partition messages table by month
- Archive old sessions (>90 days)

### Query Optimization
- Use connection pooling
- Implement query result caching
- Optimize vector search queries
- Batch insert for analytics

---

## Monitoring

### Metrics to Track
- Queries per minute
- Average response time
- Error rate
- Rate limit hits
- Feedback ratio (positive/negative)
- Session duration
- Messages per session

### Alerts
- Error rate > 5%
- Response time > 3 seconds
- Rate limit hits > 100/hour
- Public chat disabled unexpectedly

---

## Summary

This specification covers all API endpoints needed for:

✅ **Public Chat Interface**
- Query endpoint with rate limiting
- Config endpoint for UI rendering
- Feedback submission

✅ **Admin Configuration**
- Get/update configuration
- Knowledge base selection
- Full customization options

✅ **Analytics**
- Usage statistics
- Session details
- Feedback analysis

**Total Endpoints:** 8  
**Authentication Required:** 5 endpoints  
**Public Endpoints:** 3 endpoints  
**Database Tables:** 4 tables

---

**Status:** Ready for Implementation  
**Priority:** HIGH  
**Estimated Backend Time:** 16-20 hours  
**Last Updated:** November 24, 2024
