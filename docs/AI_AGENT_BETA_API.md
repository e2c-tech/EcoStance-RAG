# AI Agent Beta Feature API

API documentation for the AI Agent beta feature - intelligent query system that can answer questions using both database queries and knowledge base documents.

---

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
```
Authorization: Bearer <access_token>
```

---

## AI Agent Endpoints

### 1. Get Agent Status
**Endpoint:** `GET /db/status`

**Description:** Check what database is currently connected to the agent

**Response (Connected):**
```json
{
  "connected": true,
  "database": {
    "type": "postgresql",
    "status": "active",
    "host": "localhost",
    "database": "mydb"
  }
}
```

**Response (Not Connected):**
```json
{
  "connected": false,
  "database": null
}
```

**Note:** For knowledge bases, use `GET /manage/knowledge-bases/` to see available KBs. The KB is specified per query, not globally connected.

---

### 2. Upload SQLite Database
**Endpoint:** `POST /db/upload-sqlite`

**Description:** Upload a SQLite database file to use with the AI agent

**Request:** `multipart/form-data`
- `file`: SQLite database file (.db, .sqlite, .sqlite3)

**Response:**
```json
{
  "message": "SQLite database uploaded successfully",
  "file_path": "sqlite:///uploads/tenant_abc123/databases/mydb.sqlite",
  "filename": "mydb.sqlite",
  "size_mb": 2.5,
  "tenant_id": "abc123"
}
```

**Note:** Use the returned `file_path` to connect to the database in the next step.

---

### 3. Connect Database
**Endpoint:** `POST /db/connect`

**Description:** Connect the AI agent to your database

**Request:**
```json
{
  "db_uri": "postgresql://user:pass@host:5432/database"
}
```

**For uploaded SQLite (use file_path from upload response):**
```json
{
  "db_uri": "sqlite:///uploads/tenant_abc123/databases/mydb.sqlite"
}
```

**Response:**
```json
{
  "message": "Database connection successful and schema loaded."
}
```

---

### 4. Get Database Schema
**Endpoint:** `GET /db/schema`

**Description:** View the connected database structure

**Response:**
```json
{
  "tables": [
    {
      "name": "users",
      "columns": [
        {
          "name": "id",
          "type": "INTEGER",
          "nullable": false
        },
        {
          "name": "email",
          "type": "VARCHAR(255)",
          "nullable": false
        }
      ],
      "primary_keys": ["id"],
      "foreign_keys": []
    }
  ],
  "relationships": []
}
```

---

### 5. Ask Database Question (Natural Language to SQL)
**Endpoint:** `POST /db/generate-query`

**Description:** Convert natural language to SQL query

**Request:**
```json
{
  "question": "How many users registered last month?"
}
```

**Response:**
```json
{
  "query": "SELECT COUNT(*) FROM users WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')",
  "explanation": "This query counts all users who registered in the previous month."
}
```

---

### 6. Execute Database Query
**Endpoint:** `POST /db/execute-query`

**Description:** Run the generated SQL query

**Request:**
```json
{
  "query": "SELECT COUNT(*) FROM users WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')"
}
```

**Response:**
```json
[
  {
    "count": 1250
  }
]
```

---

### 7. List Available Knowledge Bases
**Endpoint:** `GET /manage/knowledge-bases/`

**Description:** Get list of all knowledge bases available for querying

**Response:**
```json
[
  "customer-docs",
  "product-manuals",
  "internal-policies"
]
```

---

### 8. Query Knowledge Base (RAG)
**Endpoint:** `POST /query/`

**Description:** Ask questions about documents in your knowledge base

**Request:**
```json
{
  "query": "What is the refund policy?",
  "kb_name": "customer-docs",
  "chat_history": []
}
```

**With conversation context:**
```json
{
  "query": "What about exchanges?",
  "kb_name": "customer-docs",
  "chat_history": [
    "user: What is the refund policy?",
    "assistant: Our refund policy allows returns within 30 days..."
  ]
}
```

**Response:**
```json
{
  "answer": "Our refund policy allows returns within 30 days of purchase for a full refund. Items must be in original condition with tags attached.",
  "sources": [
    {
      "filename": "policies.txt",
      "chunk_index": 5,
      "relevance_score": 0.92
    }
  ]
}
```

---

## AI Agent Usage Flow

### Check Agent Status:
```
1. GET /db/status                    → Check database connection
2. GET /manage/knowledge-bases/      → List available knowledge bases
```

### For Database Questions (Remote DB):
```
1. POST /db/connect          → Connect to database
2. GET /db/schema            → View available tables
3. POST /db/generate-query   → Ask question in natural language
4. POST /db/execute-query    → Get the results
```

### For Database Questions (SQLite Upload):
```
1. POST /db/upload-sqlite    → Upload SQLite file
2. POST /db/connect          → Connect using returned file_path
3. GET /db/schema            → View available tables
4. POST /db/generate-query   → Ask question in natural language
5. POST /db/execute-query    → Get the results
```

### For Document Questions:
```
1. GET /manage/knowledge-bases/      → List available KBs
2. POST /query/                      → Ask question about documents
```

### Combined Agent Workflow:
The AI agent can intelligently route questions to either:
- **Database** - for structured data queries (sales, users, metrics)
- **Knowledge Base** - for document-based questions (policies, FAQs, guides)

---

## Example Use Cases

### Database Query Example:
```
User: "Show me top 10 customers by revenue"
↓
Agent generates SQL: SELECT customer_name, SUM(order_total) as revenue 
                     FROM orders GROUP BY customer_name 
                     ORDER BY revenue DESC LIMIT 10
↓
Returns results with customer names and revenue
```

### Knowledge Base Query Example:
```
User: "What are the shipping options?"
↓
Agent searches documents in knowledge base
↓
Returns: "We offer Standard (5-7 days), Express (2-3 days), 
         and Overnight shipping options..."
```

---

## Request/Response Summary

| Endpoint | Method | Purpose | Key Request Fields | Key Response Fields |
|----------|--------|---------|-------------------|-------------------|
| `/db/status` | GET | Check DB connection | - | `connected`, `database{}` |
| `/manage/knowledge-bases/` | GET | List KBs | - | Array of KB names |
| `/db/upload-sqlite` | POST | Upload SQLite | `file` (multipart) | `file_path`, `filename`, `size_mb` |
| `/db/connect` | POST | Connect DB | `db_uri` | `message` |
| `/db/schema` | GET | Get structure | - | `tables[]`, `relationships[]` |
| `/db/generate-query` | POST | NL to SQL | `question` | `query`, `explanation` |
| `/db/execute-query` | POST | Run SQL | `query` | Array of results |
| `/query/` | POST | Ask documents | `query`, `kb_name`, `chat_history[]` | `answer`, `sources[]` |

---

## Error Responses

All endpoints return errors in this format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

Common error codes:
- `400` - Bad request (missing fields, invalid format)
- `401` - Not authenticated
- `403` - No permission
- `404` - Resource not found (KB, connection, etc.)
- `500` - Server error

---

## Notes

1. **Database Connection**: Only one active database connection per session. Reconnecting will replace the previous connection.

2. **Chat History**: For conversational queries, maintain the chat history array on the frontend and send it with each request.

3. **Knowledge Base**: Documents must be uploaded and processed before querying. See main API docs for upload endpoints.

4. **Query Routing**: The agent automatically determines whether to use database or knowledge base based on the question type.

5. **Security**: Database credentials are never exposed to the frontend. Connection strings are processed server-side only.
