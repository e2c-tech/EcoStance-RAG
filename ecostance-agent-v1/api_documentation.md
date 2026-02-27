# EcoStance RAG & Smart Agent: Ultimate API Reference

This is the complete, detailed technical documentation for all EcoStance backend endpoints.

## 0. Global Headers & Auth
Every request (except `/auth/login`, `/auth/set-password`, and `/tenant/register`) MUST include:
- `Authorization: Bearer <JWT_ACCESS_TOKEN>`
- `Content-Type: application/json` (unless a File Upload endpoint)

---

## 1. Authentication (`auth_router.py`)

### Login
`POST /api/v1/auth/login`
- **Request (JSON):**
  ```json
  {
    "email": "user@example.com",
    "password": "password123",
    "tenant_id": "optional-uuid",
    "api_key": "optional-string"
  }
  ```
- **Success Response (200):**
  ```json
  {
    "access_token": "string",
    "refresh_token": "string", // also set as httpOnly cookie
    "token_type": "bearer",
    "tenant_id": "string",
    "user_id": "string",
    "role": "string"
  }
  ```

### Refresh Token
`POST /api/v1/auth/refresh`
- **Request (JSON):** `{ "refresh_token": "string" }` (or via cookie)
- **Response:** New access token and user info.

### Logout
`POST /api/v1/auth/logout`
- **Action:** Clears secure cookies and invalidates session context.

---

## 2. Tenant Management (`tenant_router.py`)

### Register New Tenant
`POST /api/v1/tenant/register`
- **Request (JSON):**
  ```json
  {
    "name": "Acme Corp",
    "email": "admin@acme.com",
    "password": "securepassword",
    "phone": "+1234567890",
    "billing_tier": "free_trial"
  }
  ```

### Get Current Tenant Profile
`GET /api/v1/tenant/current`
- **Response:**
  ```json
  {
    "id": "uuid", "name": "Acme Corp", "slug": "acme-corp",
    "is_active": true, "billing_tier": "free_trial",
    "logo_url": "/api/v1/tenant/logo"
  }
  ```

### Update Notification Preferences
`PUT /api/v1/tenant/preferences`
- **Request (JSON):**
  ```json
  {
    "email_alerts": true,
    "quota_warnings": true,
    "webhook_url": "https://hooks.slack.com/..."
  }
  ```

---

## 3. User & Role Management (RBAC)
*Routers: `tenant_users.py`, `tenant_roles.py`*

### Invite User
`POST /api/v1/tenant/users/invite`
- **Request (JSON):**
  ```json
  {
    "email": "analyst@acme.com",
    "role_id": "uuid-of-role",
    "notify": true
  }
  ```

### List Roles
`GET /api/v1/tenant/roles`
- **Response:** Array of role objects with associated permissions (`KB_QUERY`, `DB_CONNECT`, etc.).

---

## 4. AI Agents (`beta_agent_router.py`)

### Chat with Agent
`POST /api/v1/beta/agent/chat`
- **Request (JSON):**
  ```json
  {
    "session_id": "optional-uuid",
    "message": "Analyze the log file for unauthorized access.",
    "knowledge_base": "default",
    "database_connection": "prod_db"
  }
  ```
- **Response:**
  ```json
  {
    "content": "Final AI answer...",
    "session_id": "session-uuid",
    "success": true,
    "agent_type": "security_analyst",
    "timestamp": "2026-02-27T13:45:00"
  }
  ```

### Get Session History
`GET /api/v1/beta/agent/history/{session_id}`
- **Response:** Array of `role` (user/assistant) and `content` pairs.

---

## 5. Investigation Journal (`investigation_router.py`)

### Retrieve Investigation Log (CoT)
`GET /api/v1/investigation/journal/{session_id}`
- **Description:** Returns the internal "Chain of Thought" steps for SOC audit.
- **Response Example:**
  ```json
  [
    {
      "step_number": 1,
      "thought": "I will search the knowledge base for 'unauthorized access' patterns.",
      "tool_name": "kb_search",
      "tool_args": {"query": "unauthorized access"},
      "tool_result": "Found 3 matching documents...",
      "timestamp": "..."
    }
  ]
  ```

---

## 6. Document Ingestion & RAG (`upload.py`, `query_router.py`)

### Upload File
`POST /api/v1/upload/`
- **Body (Multipart):**
  - `file`: (Binary)
  - `process_now`: (bool)
  - `kb_name`: (string)
- **Response:** Includes `job_id` and `file_path`.

### Query RAG
`POST /api/v1/query/`
- **Body (Form):**
  - `kb_name`: "default"
  - `query`: "What is our vacation policy?"
- **Response:** `{ "answer": "...", "kb_name": "default" }`

---

## 7. Gmail Integration (`gmail_router.py`)

### Start OAuth
`GET /api/v1/gmail/auth-url`
- **Response:** `{ "auth_url": "https://accounts.google.com/..." }`

### Create Monitoring recipient
`POST /api/v1/gmail/recipients`
- **Body (JSON):**
  ```json
  {
    "email_address": "support@acme.com",
    "display_name": "Support Inbox",
    "enabled": true
  }
  ```

### Manually Sync Mail
`POST /api/v1/gmail/sync/{schedule_id}`
- **Action:** Triggers background process to pull and vectorize new emails.

---

## 8. Billing & Quotas (`billing_router.py`, `quota_router.py`)

### Create Stripe Checkout
`POST /billing/checkout`
- **Body (JSON):** `{ "plan_id": "enterprise", "currency": "USD" }`
- **Response:** `{ "id": "cs_...", "url": "https://checkout.stripe.com/..." }`

### Quota Status
`GET /api/v1/quota/status`
- **Response:**
  ```json
  {
    "storage": { "used_mb": 150, "limit_mb": 1000, "percent": 15 },
    "queries": { "daily_used": 45, "daily_limit": 100 }
  }
  ```

---

## 9. Monitoring & Admin (`metrics_router.py`, `llm_usage_router.py`)

### Detailed Metrics
`GET /api/v1/metrics/tenant`
- **Query Params:** `metric_type=daily`, `days=7`
- **Action:** Returns time-series data of usage/errors.

### LLM Token Usage
`GET /api/llm-usage/summary`
- **Response:**
  ```json
  {
    "total_token_count": 125000,
    "input_tokens": 80000,
    "output_tokens": 45000,
    "estimated_cost_usd": 1.25
  }
  ```

---
*End of Complete API Reference*
