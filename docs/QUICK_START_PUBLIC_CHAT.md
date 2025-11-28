# Quick Start: Public Chat API Testing

## 🚀 Quick Test Guide

### Step 1: Start the Server

```bash
.venv\Scripts\activate
python run_app.py
```

The server will start at `http://localhost:8000`

---

### Step 2: Test Public Endpoints (No Authentication)

#### Get Configuration
```bash
curl http://localhost:8000/api/v1/public-chat/config
```

**Expected Response:**
```json
{
  "enabled": false,
  "welcome_message": "Public chat is currently disabled.",
  "suggested_questions": [],
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
}
```

---

### Step 3: Enable Public Chat (Admin Required)

#### 3.1 Login as Admin
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"admin@certifydigital.com\", \"password\": \"admin123\"}"
```

**Save the token from the response!**

#### 3.2 Get Available Knowledge Bases
```bash
curl http://localhost:8000/api/v1/admin/public-chat/available-kbs \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

#### 3.3 Get Available Databases
```bash
curl http://localhost:8000/api/v1/admin/public-chat/available-dbs \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

#### 3.4 Enable and Configure Public Chat
```bash
curl -X PUT http://localhost:8000/api/v1/admin/public-chat/config \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d "{
    \"enabled\": true,
    \"allowed_kbs\": [\"tenant_badcd123-6cc6-4011-b01b-d33d1153f10d_quickship-logistics\"],
    \"welcome_message\": \"Welcome to QuickShip! How can I help you today?\",
    \"suggested_questions\": [
      \"What are your shipping options?\",
      \"How can I track my order?\",
      \"What are your business hours?\"
    ],
    \"branding\": {
      \"primary_color\": \"#0066CC\",
      \"company_name\": \"QuickShip\"
    },
    \"rate_limit\": {
      \"queries_per_minute\": 10,
      \"max_messages_per_session\": 50
    },
    \"features\": {
      \"show_sources\": true,
      \"allow_feedback\": true,
      \"show_suggested_questions\": true
    }
  }"
```

---

### Step 4: Test Chat Functionality

#### 4.1 Send a Query
```bash
curl -X POST http://localhost:8000/api/v1/public-chat/query \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"test-session-123\",
    \"query\": \"What are your shipping options?\",
    \"conversation_history\": []
  }"
```

**Expected Response:**
```json
{
  "answer": "Based on our shipping policy...",
  "sources": [],
  "session_id": "test-session-123",
  "timestamp": "2024-11-26T10:30:00Z"
}
```

#### 4.2 Continue Conversation
```bash
curl -X POST http://localhost:8000/api/v1/public-chat/query \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"test-session-123\",
    \"query\": \"How much does express shipping cost?\",
    \"conversation_history\": [
      {
        \"role\": \"user\",
        \"content\": \"What are your shipping options?\"
      },
      {
        \"role\": \"assistant\",
        \"content\": \"We offer standard, express, and overnight shipping...\"
      }
    ]
  }"
```

#### 4.3 Submit Feedback
```bash
curl -X POST http://localhost:8000/api/v1/public-chat/feedback \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"test-session-123\",
    \"message_id\": \"msg-abc123\",
    \"feedback_type\": \"positive\",
    \"comment\": \"Very helpful answer!\"
  }"
```

---

### Step 5: View Analytics (Admin)

#### Get Analytics
```bash
curl "http://localhost:8000/api/v1/admin/public-chat/analytics?days=30" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

#### Get Session Details
```bash
curl http://localhost:8000/api/v1/admin/public-chat/sessions/test-session-123 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## 🧪 Testing with Python

Create a test script `test_public_chat.py`:

```python
import requests
import uuid

BASE_URL = "http://localhost:8000"

# 1. Get config
response = requests.get(f"{BASE_URL}/api/v1/public-chat/config")
print("Config:", response.json())

# 2. Login as admin
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"email": "admin@certifydigital.com", "password": "admin123"}
)
token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 3. Get available KBs
kbs_response = requests.get(
    f"{BASE_URL}/api/v1/admin/public-chat/available-kbs",
    headers=headers
)
print("Available KBs:", kbs_response.json())

# 4. Enable public chat
config_update = {
    "enabled": True,
    "allowed_kbs": ["tenant_badcd123-6cc6-4011-b01b-d33d1153f10d_quickship-logistics"],
    "welcome_message": "Welcome! How can I help?",
    "suggested_questions": ["What are your shipping options?"],
    "branding": {
        "primary_color": "#0066CC",
        "company_name": "QuickShip"
    },
    "rate_limit": {
        "queries_per_minute": 10,
        "max_messages_per_session": 50
    },
    "features": {
        "show_sources": True,
        "allow_feedback": True,
        "show_suggested_questions": True
    }
}
update_response = requests.put(
    f"{BASE_URL}/api/v1/admin/public-chat/config",
    headers=headers,
    json=config_update
)
print("Config updated:", update_response.json())

# 5. Send a query
session_id = str(uuid.uuid4())
query_response = requests.post(
    f"{BASE_URL}/api/v1/public-chat/query",
    json={
        "session_id": session_id,
        "query": "What are your shipping options?",
        "conversation_history": []
    }
)
print("Query response:", query_response.json())

# 6. Get analytics
analytics_response = requests.get(
    f"{BASE_URL}/api/v1/admin/public-chat/analytics?days=30",
    headers=headers
)
print("Analytics:", analytics_response.json())
```

Run it:
```bash
.venv\Scripts\activate
python test_public_chat.py
```

---

## 📊 API Documentation

Visit the interactive API docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Look for the "14. Public Chat" and "Public Chat Admin" sections.

---

## ✅ Verification Checklist

- [ ] Server starts without errors
- [ ] Can get public chat config (disabled by default)
- [ ] Can login as admin
- [ ] Can get available knowledge bases
- [ ] Can get available databases
- [ ] Can enable and configure public chat
- [ ] Can send queries and get responses
- [ ] Can submit feedback
- [ ] Can view analytics
- [ ] Can view session details
- [ ] Rate limiting works (429 error after limit)

---

## 🐛 Troubleshooting

### Issue: "Public chat is currently disabled"
**Solution:** Enable it via the admin config endpoint (Step 3.4)

### Issue: "No knowledge bases configured"
**Solution:** Add KB IDs to `allowed_kbs` in the config

### Issue: "Session not found"
**Solution:** Make sure you're using the same session_id for queries and feedback

### Issue: "Rate limit exceeded"
**Solution:** Wait 60 seconds or increase limits in config

### Issue: "Authentication required"
**Solution:** Get a token via `/api/v1/auth/login` and include it in the Authorization header

---

## 📝 Notes

- Session IDs should be unique per user (use UUID v4)
- Public chat is disabled by default for security
- Admin must configure allowed KBs before public chat works
- Rate limits are per session, not global
- Sessions expire after 24 hours of inactivity
- All data is tenant-isolated

---

## 🎉 Success!

If all tests pass, your Public Chat API is ready for frontend integration!
