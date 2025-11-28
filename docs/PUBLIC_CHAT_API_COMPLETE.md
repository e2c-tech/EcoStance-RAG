# Public AI Agent API - Complete Implementation

## ✅ Implementation Status: COMPLETE

All required endpoints and database tables have been implemented and are ready for use.

---

## 📋 API Endpoints

### Public Endpoints (No Authentication Required)

#### 1. Get Public Chat Configuration
```
GET /api/v1/public-chat/config
```
**Description:** Get the current public chat configuration for rendering the UI.

**Response:**
```json
{
  "enabled": true,
  "welcome_message": "Hi! How can I help you today?",
  "suggested_questions": [
    "What are your business hours?",
    "How can I track my order?"
  ],
  "branding": {
    "logo": "https://example.com/logo.png",
    "primary_color": "#0066CC",
    "company_name": "QuickShip"
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

#### 2. Send Chat Message
```
POST /api/v1/public-chat/query
```
**Description:** Send a query to the public chat and get an AI response.

**Request:**
```json
{
  "session_id": "unique-session-id",
  "query": "What are your shipping options?",
  "conversation_history": [
    {
      "role": "user",
      "content": "Hello"
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help you?"
    }
  ]
}
```

**Response:**
```json
{
  "answer": "We offer standard, express, and overnight shipping...",
  "sources": [
    {
      "filename": "shipping-policy.pdf",
      "chunk_number": 1,
      "similarity": 0.95,
      "preview": "Our shipping options include..."
    }
  ],
  "session_id": "unique-session-id",
  "timestamp": "2024-11-26T10:30:00Z"
}
```

**Rate Limiting:**
- Returns 429 if rate limit exceeded
- Includes `Retry-After` header with seconds to wait

#### 3. Submit Feedback
```
POST /api/v1/public-chat/feedback
```
**Description:** Submit feedback for a chat message.

**Request:**
```json
{
  "session_id": "unique-session-id",
  "message_id": "msg-abc123",
  "feedback_type": "positive",
  "comment": "Very helpful answer!"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Thank you for your feedback!"
}
```

---

### Admin Endpoints (Authentication Required)

All admin endpoints require `admin` or `super_admin` role.

#### 4. Get Admin Configuration
```
GET /api/v1/admin/public-chat/config
```
**Description:** Get the full public chat configuration for admin panel.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "enabled": true,
  "allowed_kbs": ["kb-1", "kb-2"],
  "welcome_message": "Hi! How can I help you today?",
  "suggested_questions": ["Question 1", "Question 2"],
  "branding": {
    "logo": "https://example.com/logo.png",
    "primary_color": "#0066CC",
    "company_name": "QuickShip"
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
  "created_at": "2024-11-26T10:00:00Z",
  "updated_at": "2024-11-26T10:30:00Z",
  "updated_by": "admin@example.com"
}
```

#### 5. Update Configuration
```
PUT /api/v1/admin/public-chat/config
```
**Description:** Update the public chat configuration.

**Headers:**
```
Authorization: Bearer <token>
```

**Request:**
```json
{
  "enabled": true,
  "allowed_kbs": ["kb-1", "kb-2"],
  "welcome_message": "Welcome! How can I assist you?",
  "suggested_questions": [
    "What are your business hours?",
    "How can I track my order?"
  ],
  "branding": {
    "logo": "https://example.com/logo.png",
    "primary_color": "#0066CC",
    "company_name": "QuickShip"
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

**Response:**
```json
{
  "success": true,
  "message": "Configuration updated successfully",
  "config": { /* full config object */ }
}
```

#### 6. Get Available Knowledge Bases
```
GET /api/v1/admin/public-chat/available-kbs
```
**Description:** Get list of knowledge bases that can be selected for public chat.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "knowledge_bases": [
    {
      "id": "kb-1",
      "name": "Product Documentation",
      "document_count": 150,
      "is_public": false,
      "created_at": "2024-11-26T10:00:00Z"
    },
    {
      "id": "kb-2",
      "name": "FAQ",
      "document_count": 50,
      "is_public": false,
      "created_at": "2024-11-26T10:00:00Z"
    }
  ]
}
```

#### 7. Get Available Databases
```
GET /api/v1/admin/public-chat/available-dbs
```
**Description:** Get list of database connections available for the tenant.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "databases": [
    {
      "id": "qragent",
      "name": "Qragent",
      "type": "postgresql",
      "database": "qr-agent-db",
      "host": "buddi-db-buddi.k.aivencloud.com"
    },
    {
      "id": "logistics-demo",
      "name": "Logistics Demo",
      "type": "sqlite",
      "database": "sqlite:///path/to/QuickShip.db",
      "host": null
    }
  ]
}
```

#### 8. Get Analytics
```
GET /api/v1/admin/public-chat/analytics?days=30
```
**Description:** Get usage statistics and analytics for public chat.

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `days` (optional): Number of days to analyze (default: 30)
- `start_date` (optional): ISO format start date
- `end_date` (optional): ISO format end date

**Response:**
```json
{
  "period": {
    "start_date": "2024-10-27T00:00:00Z",
    "end_date": "2024-11-26T00:00:00Z",
    "days": 30
  },
  "summary": {
    "total_sessions": 150,
    "total_queries": 450,
    "unique_visitors": 150,
    "average_queries_per_session": 3.0,
    "average_rating": 4.5
  },
  "top_questions": [
    {
      "question": "What are your shipping options?",
      "count": 45,
      "percentage": 10.0
    }
  ],
  "feedback_summary": {
    "total_feedback": 100,
    "positive": 85,
    "negative": 15,
    "positive_percentage": 85.0
  },
  "usage_by_day": [],
  "rate_limit_hits": {
    "queries_per_minute": 0,
    "max_messages_per_session": 0
  }
}
```

#### 9. Get Session Details
```
GET /api/v1/admin/public-chat/sessions/{session_id}
```
**Description:** Get detailed information about a specific session.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "session_id": "unique-session-id",
  "started_at": "2024-11-26T10:00:00Z",
  "ended_at": "2024-11-26T10:30:00Z",
  "duration_seconds": 1800,
  "message_count": 10,
  "messages": [
    {
      "id": "msg-abc123",
      "role": "user",
      "content": "Hello",
      "timestamp": "2024-11-26T10:00:00Z",
      "sources": null,
      "feedback": null
    },
    {
      "id": "msg-def456",
      "role": "assistant",
      "content": "Hi! How can I help you?",
      "timestamp": "2024-11-26T10:00:05Z",
      "sources": [],
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

---

## 🗄️ Database Tables

All tables have been created via migration `008_create_public_chat_tables.sql`.

### 1. public_chat_configs
Stores configuration for public chat feature per tenant.

**Columns:**
- `id` (TEXT, PRIMARY KEY)
- `tenant_id` (TEXT, FOREIGN KEY → tenants.id)
- `enabled` (BOOLEAN)
- `allowed_kbs` (TEXT, JSON array)
- `welcome_message` (TEXT)
- `suggested_questions` (TEXT, JSON array)
- `branding` (TEXT, JSON object)
- `rate_limit` (TEXT, JSON object)
- `features` (TEXT, JSON object)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)
- `updated_by` (TEXT)

**Indexes:**
- `idx_public_chat_configs_tenant` on `tenant_id`

### 2. public_chat_sessions
Stores individual chat sessions.

**Columns:**
- `session_id` (TEXT, PRIMARY KEY)
- `tenant_id` (TEXT, FOREIGN KEY → tenants.id)
- `started_at` (TIMESTAMP)
- `ended_at` (TIMESTAMP)
- `message_count` (INTEGER)
- `query_count` (INTEGER)
- `last_activity` (TIMESTAMP)
- `metadata` (TEXT, JSON object)

**Indexes:**
- `idx_public_chat_sessions_tenant_started` on `(tenant_id, started_at)`
- `idx_public_chat_sessions_last_activity` on `last_activity`

### 3. public_chat_messages
Stores individual messages in chat sessions.

**Columns:**
- `id` (TEXT, PRIMARY KEY)
- `session_id` (TEXT, FOREIGN KEY → public_chat_sessions.session_id)
- `tenant_id` (TEXT, FOREIGN KEY → tenants.id)
- `role` (TEXT, CHECK: 'user' or 'assistant')
- `content` (TEXT)
- `sources` (TEXT, JSON array)
- `feedback` (TEXT, CHECK: 'positive', 'negative', or NULL)
- `feedback_comment` (TEXT)
- `timestamp` (TIMESTAMP)

**Indexes:**
- `idx_public_chat_messages_session` on `session_id`
- `idx_public_chat_messages_tenant_timestamp` on `(tenant_id, timestamp)`

### 4. public_chat_feedback
Stores feedback submitted by users.

**Columns:**
- `id` (TEXT, PRIMARY KEY)
- `session_id` (TEXT)
- `message_id` (TEXT, FOREIGN KEY → public_chat_messages.id)
- `tenant_id` (TEXT, FOREIGN KEY → tenants.id)
- `feedback_type` (TEXT, CHECK: 'positive' or 'negative')
- `comment` (TEXT)
- `timestamp` (TIMESTAMP)

**Indexes:**
- `idx_public_chat_feedback_tenant_timestamp` on `(tenant_id, timestamp)`
- `idx_public_chat_feedback_message` on `message_id`

---

## 📁 Implementation Files

### Models
- `app/models/public_chat.py` - SQLAlchemy models for all tables

### Schemas
- `app/schemas/public_chat.py` - Pydantic models for request/response validation

### Services
- `app/services/public_chat_service.py` - Business logic for public chat functionality

### Routers
- `app/routers/public_chat_router.py` - API endpoints

### Migrations
- `migrations/008_create_public_chat_tables.sql` - SQLite migration
- `migrations/008_create_public_chat_tables_postgres.sql` - PostgreSQL migration

---

## 🚀 Testing the API

### 1. Start the Server
```bash
.venv\Scripts\activate
python run_app.py
```

### 2. Test Public Endpoints (No Auth)

**Get Configuration:**
```bash
curl http://localhost:8000/api/v1/public-chat/config
```

**Send Query:**
```bash
curl -X POST http://localhost:8000/api/v1/public-chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-123",
    "query": "What are your shipping options?",
    "conversation_history": []
  }'
```

**Submit Feedback:**
```bash
curl -X POST http://localhost:8000/api/v1/public-chat/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-123",
    "message_id": "msg-abc123",
    "feedback_type": "positive",
    "comment": "Very helpful!"
  }'
```

### 3. Test Admin Endpoints (Auth Required)

First, get an auth token:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "your-password"
  }'
```

Then use the token for admin endpoints:
```bash
# Get admin config
curl http://localhost:8000/api/v1/admin/public-chat/config \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get available KBs
curl http://localhost:8000/api/v1/admin/public-chat/available-kbs \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get available databases
curl http://localhost:8000/api/v1/admin/public-chat/available-dbs \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get analytics
curl http://localhost:8000/api/v1/admin/public-chat/analytics?days=30 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Update config
curl -X PUT http://localhost:8000/api/v1/admin/public-chat/config \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "allowed_kbs": ["kb-1"],
    "welcome_message": "Welcome!",
    "suggested_questions": ["Question 1"],
    "branding": {
      "primary_color": "#0066CC",
      "company_name": "QuickShip"
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
  }'
```

---

## 🔒 Security Features

1. **Rate Limiting**: Configurable per-session and per-minute limits
2. **Session Expiry**: Sessions expire after 24 hours of inactivity
3. **Tenant Isolation**: All data is isolated by tenant_id
4. **Admin Authentication**: Admin endpoints require valid JWT token
5. **Role-Based Access**: Only admin/super_admin can access admin endpoints

---

## 📊 Features

1. **Configuration Management**: Full control over chat behavior and appearance
2. **Session Tracking**: Track user sessions and conversation history
3. **Message Storage**: Store all messages with timestamps and metadata
4. **Feedback Collection**: Collect positive/negative feedback with comments
5. **Analytics**: Comprehensive usage statistics and insights
6. **Knowledge Base Selection**: Choose which KBs to use for responses
7. **Database Integration**: Access to configured database connections
8. **Rate Limiting**: Prevent abuse with configurable limits
9. **Branding**: Customize colors, logo, and company name
10. **Suggested Questions**: Guide users with pre-configured questions

---

## ✅ Next Steps for Frontend

Your React frontend should implement:

1. **Public Chat Widget**:
   - Fetch config from `/api/v1/public-chat/config`
   - Display welcome message and suggested questions
   - Send queries to `/api/v1/public-chat/query`
   - Show sources if `features.show_sources` is true
   - Allow feedback if `features.allow_feedback` is true
   - Generate unique session IDs (use UUID)
   - Handle rate limiting (429 responses)

2. **Admin Settings Page**:
   - Fetch config from `/api/v1/admin/public-chat/config`
   - Update config via `/api/v1/admin/public-chat/config`
   - List available KBs from `/api/v1/admin/public-chat/available-kbs`
   - List available DBs from `/api/v1/admin/public-chat/available-dbs`
   - Show analytics from `/api/v1/admin/public-chat/analytics`
   - View session details from `/api/v1/admin/public-chat/sessions/{id}`

---

## 📝 Notes

- All endpoints are registered in `app/main.py`
- Database tables are created automatically on first run
- Default configuration is created for each tenant
- Public chat is disabled by default (must be enabled via admin)
- Session IDs should be generated client-side (use UUID v4)
- Tenant ID is extracted from `X-Tenant-ID` header or defaults to CertifyDigital tenant

---

## 🎉 Summary

**All required endpoints and database tables are implemented and ready to use!**

The backend is complete and waiting for your React frontend to integrate with it.
