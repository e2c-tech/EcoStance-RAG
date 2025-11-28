# AI Agent API Documentation

Complete API reference for integrating the AI Agent feature into your frontend.

---

## Base URL
```
http://localhost:8000/api/v1
```

---

## Authentication
All endpoints require authentication via JWT token:
```
Authorization: Bearer <access_token>
```

---

## 1. Database Connection Management

### 1.1 Connect to Database
**Endpoint:** `POST /db/connect`

**Description:** Connect to any database (PostgreSQL, MySQL, SQLite, MongoDB)

**Request Body:**
```json
{
  "db_uri": "postgresql://username:password@host:port/database"
}
```

**Example URIs:**
- PostgreSQL: `postgresql://user:pass@localhost:5432/mydb`
- MySQL: `mysql://user:pass@localhost:3306/mydb`
- SQLite: `sqlite:///path/to/database.db`
- MongoDB: `mongodb://localhost:27017/mydb`

**Response (Success - 200):**
```json
{
  "message": "Database connection successful and schema loaded."
}
```

**Response (Error - 500):**
```json
{
  "detail": "Connection error message"
}
```

---

### 1.2 Get Database Schema
**Endpoint:** `GET /db/schema`

**Description:** Get the schema of the currently connected database

**Response (Success - 200):**
```json
{
  "tables": [
    {
      "name": "users",
      "columns": [
        {
          "name": "id",
          "type": "INTEGER",
          "nullable": false,
          "default": null
        },
        {
          "name": "email",
          "type": "VARCHAR(255)",
          "nullable": false,
          "default": null
        },
        {
          "name": "created_at",
          "type": "TIMESTAMP",
          "nullable": true,
          "default": "CURRENT_TIMESTAMP"
        }
      ],
      "primary_keys": ["id"],
      "foreign_keys": []
    },
    {
      "name": "orders",
      "columns": [
        {
          "name": "id",
          "type": "INTEGER",
          "nullable": false,
          "default": null
        },
        {
          "name": "user_id",
          "type": "INTEGER",
          "nullable": false,
          "default": null
        },
        {
          "name": "total",
          "type": "DECIMAL(10,2)",
          "nullable": false,
          "default": null
        }
      ],
      "primary_keys": ["id"],
      "foreign_keys": [
        {
          "constrained_columns": ["user_id"],
          "referred_table": "orders",
          "referred_columns": ["id"]
        }
      ]
    }
  ],
  "relationships": [
    {
      "from_table": "orders",
      "from_columns": ["user_id"],
      "to_table": "users",
      "to_columns": ["id"]
    }
  ]
}
```

**Response (Error - 400):**
```json
{
  "detail": "Database not connected. Please connect to a database first."
}
```

---

### 1.3 Generate SQL Query from Natural Language
**Endpoint:** `POST /db/generate-query`

**Description:** Convert natural language question to SQL query

**Request Body:**
```json
{
  "question": "Show me all users who registered in the last 30 days"
}
```

**Response (Success - 200):**
```json
{
  "query": "SELECT * FROM users WHERE created_at >= NOW() - INTERVAL '30 days'",
  "explanation": "This query retrieves all users who registered within the last 30 days by filtering on the created_at timestamp column."
}
```

**Response (Error - 400):**
```json
{
  "detail": "Database not connected or schema not loaded."
}
```

**Response (Error - 500):**
```json
{
  "error": "Failed to generate query: <error message>"
}
```

---

### 1.4 Execute SQL Query
**Endpoint:** `POST /db/execute-query`

**Description:** Execute a SQL query against the connected database

**Request Body:**
```json
{
  "query": "SELECT id, email, created_at FROM users LIMIT 10"
}
```

**Response (Success - 200):**
```json
[
  {
    "id": 1,
    "email": "user1@example.com",
    "created_at": "2025-01-15T10:30:00"
  },
  {
    "id": 2,
    "email": "user2@example.com",
    "created_at": "2025-01-16T14:20:00"
  }
]
```

**Response (Error - 400):**
```json
{
  "detail": "Database not connected."
}
```

**Response (Error - 500):**
```json
{
  "detail": "Query execution failed: <error message>"
}
```

---

### 1.5 Save Database Connection
**Endpoint:** `POST /db/connections/save`

**Description:** Save a database connection profile for later use

**Request Body:**
```json
{
  "name": "Production DB",
  "db_type": "postgresql",
  "host": "db.example.com",
  "port": "5432",
  "username": "admin",
  "password": "secure_password",
  "database": "production"
}
```

**For SQLite:**
```json
{
  "name": "Local SQLite",
  "db_type": "sqlite",
  "db_path": "/path/to/database.db"
}
```

**Response (Success - 200):**
```json
{
  "message": "Connection 'Production DB' saved successfully"
}
```

**Response (Error - 500):**
```json
{
  "detail": "Failed to save connection"
}
```

---

### 1.6 List Saved Connections
**Endpoint:** `GET /db/connections/list`

**Description:** Get list of all saved database connections (passwords excluded)

**Response (Success - 200):**
```json
[
  {
    "name": "Production DB",
    "type": "postgresql",
    "host": "db.example.com",
    "database": "production",
    "username": "admin"
  },
  {
    "name": "Local SQLite",
    "type": "sqlite",
    "host": "",
    "database": "/path/to/database.db",
    "username": ""
  }
]
```

---

### 1.7 Load Saved Connection
**Endpoint:** `GET /db/connections/{name}`

**Description:** Load a saved connection profile with decrypted credentials

**Path Parameters:**
- `name` (string): Name of the saved connection

**Response (Success - 200):**
```json
{
  "type": "postgresql",
  "host": "db.example.com",
  "port": "5432",
  "username": "admin",
  "password": "secure_password",
  "database": "production"
}
```

**Response (Error - 404):**
```json
{
  "detail": "Connection 'Production DB' not found"
}
```

---

### 1.8 Delete Saved Connection
**Endpoint:** `DELETE /db/connections/{name}`

**Description:** Delete a saved connection profile

**Path Parameters:**
- `name` (string): Name of the connection to delete

**Response (Success - 200):**
```json
{
  "message": "Connection 'Production DB' deleted successfully"
}
```

**Response (Error - 404):**
```json
{
  "detail": "Connection 'Production DB' not found"
}
```

---

## 2. Knowledge Base (RAG) Management

### 2.1 Create Knowledge Base
**Endpoint:** `POST /manage/knowledge-bases/`

**Description:** Create a new empty knowledge base

**Request Body:**
```json
{
  "kb_name": "customer-support-docs"
}
```

**Response (Success - 200):**
```json
{
  "message": "Knowledge base 'customer-support-docs' created successfully",
  "kb_name": "customer-support-docs",
  "collection_name": "tenant_abc123_customer-support-docs"
}
```

**Response (Error - 409):**
```json
{
  "detail": "Knowledge base 'customer-support-docs' already exists for this tenant"
}
```

---

### 2.2 List Knowledge Bases
**Endpoint:** `GET /manage/knowledge-bases/`

**Description:** Get list of all knowledge bases for the current tenant

**Response (Success - 200):**
```json
[
  "customer-support-docs",
  "product-manuals",
  "internal-policies"
]
```

---

### 2.3 Get Knowledge Base Details
**Endpoint:** `GET /manage/knowledge-bases/{kb_name}/details`

**Description:** Get detailed information about a specific knowledge base

**Path Parameters:**
- `kb_name` (string): Name of the knowledge base

**Response (Success - 200):**
```json
{
  "name": "customer-support-docs",
  "collection_name": "tenant_abc123_customer-support-docs",
  "vector_count": 1250,
  "points_count": 1250,
  "files": [
    {
      "filename": "faq.pdf",
      "chunk_count": 45
    },
    {
      "filename": "policies.txt",
      "chunk_count": 32
    }
  ]
}
```

**Response (Error - 404):**
```json
{
  "detail": "Knowledge base 'customer-support-docs' not found for tenant"
}
```

---

### 2.4 Get Knowledge Base Files
**Endpoint:** `GET /manage/knowledge-bases/{kb_name}/files`

**Description:** Get list of all files in a knowledge base

**Path Parameters:**
- `kb_name` (string): Name of the knowledge base

**Response (Success - 200):**
```json
{
  "kb_name": "customer-support-docs",
  "collection_name": "tenant_abc123_customer-support-docs",
  "files": [
    {
      "filename": "faq.pdf",
      "chunk_count": 45,
      "last_updated": "2025-11-20T10:30:00"
    },
    {
      "filename": "policies.txt",
      "chunk_count": 32,
      "last_updated": "2025-11-19T15:20:00"
    }
  ]
}
```

---

### 2.5 Upload File
**Endpoint:** `POST /upload/`

**Description:** Upload a file to tenant storage (step 1 of 2)

**Request:** `multipart/form-data`
- `file`: File to upload

**Response (Success - 200):**
```json
{
  "message": "File uploaded successfully. Use the returned path to process the file.",
  "file_path": "uploads/tenant_abc123/document.pdf",
  "tenant_id": "abc123",
  "filename": "document.pdf",
  "size_mb": 2.5,
  "storage_usage": {
    "total_files": 15,
    "total_mb": 125.3,
    "quota_mb": 10000,
    "usage_percent": 1.25
  }
}
```

**Response (Error - 413):**
```json
{
  "detail": {
    "error": "Storage quota exceeded",
    "quota_mb": 10000,
    "current_usage_mb": 9950,
    "available_mb": 50,
    "usage_percent": 99.5
  }
}
```

---

### 2.6 Process File to Knowledge Base
**Endpoint:** `POST /upload-to-qdrant/`

**Description:** Process uploaded file and add to knowledge base (step 2 of 2)

**Request:** `application/x-www-form-urlencoded`
- `file_path` (string): Path returned from upload endpoint
- `kb_name` (string): Name of the knowledge base (default: "default")

**Response (Success - 200):**
```json
{
  "message": "Processing started for 'document.pdf' in knowledge base 'customer-support-docs'.",
  "job_id": "job_abc123xyz",
  "tenant_id": "abc123",
  "kb_name": "customer-support-docs",
  "collection_name": "tenant_abc123_customer-support-docs",
  "status_url": "/api/v1/processing-status/job_abc123xyz"
}
```

**Response (Error - 404):**
```json
{
  "detail": "File not found at the specified path."
}
```

---

### 2.7 Check Processing Status
**Endpoint:** `GET /processing-status/{job_id}`

**Description:** Check the status of a file processing job

**Path Parameters:**
- `job_id` (string): Job ID returned from upload-to-qdrant

**Response (In Progress - 200):**
```json
{
  "job_id": "job_abc123xyz",
  "status": "processing",
  "file_path": "uploads/tenant_abc123/document.pdf",
  "collection_name": "tenant_abc123_customer-support-docs",
  "progress": 45,
  "message": "Processing chunks..."
}
```

**Response (Completed - 200):**
```json
{
  "job_id": "job_abc123xyz",
  "status": "completed",
  "file_path": "uploads/tenant_abc123/document.pdf",
  "collection_name": "tenant_abc123_customer-support-docs",
  "progress": 100,
  "message": "Processing completed successfully"
}
```

**Response (Failed - 200):**
```json
{
  "job_id": "job_abc123xyz",
  "status": "failed",
  "file_path": "uploads/tenant_abc123/document.pdf",
  "collection_name": "tenant_abc123_customer-support-docs",
  "progress": 0,
  "error": "Failed to parse PDF: Invalid format"
}
```

---

### 2.8 Query Knowledge Base
**Endpoint:** `POST /query/`

**Description:** Ask questions against a knowledge base using RAG

**Request Body:**
```json
{
  "query": "What is the refund policy?",
  "kb_name": "customer-support-docs",
  "chat_history": []
}
```

**With Chat History:**
```json
{
  "query": "What about exchanges?",
  "kb_name": "customer-support-docs",
  "chat_history": [
    "user: What is the refund policy?",
    "assistant: Our refund policy allows returns within 30 days of purchase..."
  ]
}
```

**Response (Success - 200):**
```json
{
  "answer": "Our refund policy allows returns within 30 days of purchase for a full refund. Items must be in original condition with tags attached.",
  "sources": [
    {
      "filename": "policies.txt",
      "chunk_index": 5,
      "relevance_score": 0.92
    },
    {
      "filename": "faq.pdf",
      "chunk_index": 12,
      "relevance_score": 0.85
    }
  ]
}
```

**Response (Error - 404):**
```json
{
  "detail": "Knowledge base 'customer-support-docs' not found"
}
```

---

### 2.9 Delete File from Knowledge Base
**Endpoint:** `DELETE /manage/knowledge-bases/{kb_name}/files/{filename}`

**Description:** Remove a specific file from a knowledge base

**Path Parameters:**
- `kb_name` (string): Name of the knowledge base
- `filename` (string): Name of the file to delete

**Response (Success - 200):**
```json
{
  "message": "File 'document.pdf' deleted successfully from 'customer-support-docs'."
}
```

---

### 2.10 Delete Knowledge Base
**Endpoint:** `DELETE /manage/knowledge-bases/{kb_name}`

**Description:** Delete an entire knowledge base and all its data

**Path Parameters:**
- `kb_name` (string): Name of the knowledge base to delete

**Response (Success - 200):**
```json
{
  "message": "Knowledge base 'customer-support-docs' deleted successfully."
}
```

---

## 3. Combined AI Agent Workflow

### Typical Usage Flow:

#### For Database Queries:
1. `POST /db/connect` - Connect to database
2. `GET /db/schema` - Get database schema
3. `POST /db/generate-query` - Generate SQL from natural language
4. `POST /db/execute-query` - Execute the generated query

#### For Knowledge Base Queries:
1. `POST /manage/knowledge-bases/` - Create KB (if needed)
2. `POST /upload/` - Upload file
3. `POST /upload-to-qdrant/` - Process file to KB
4. `GET /processing-status/{job_id}` - Check processing status
5. `POST /query/` - Query the knowledge base

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input or missing required data |
| 401 | Unauthorized - Invalid or missing authentication token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource already exists |
| 413 | Payload Too Large - File size or quota exceeded |
| 500 | Internal Server Error - Server-side error |

---

## Rate Limits

All endpoints are subject to rate limiting based on tenant tier:
- Free tier: 100 requests/minute
- Pro tier: 1000 requests/minute
- Enterprise: Custom limits

---

## Notes

1. **Database Connections**: Currently uses global state - only one database connection per server instance. Multi-tenant isolation coming soon.

2. **File Processing**: File processing is asynchronous. Always check the job status before querying.

3. **Chat History**: For conversational queries, maintain chat history on the frontend and send it with each request.

4. **Security**: Never expose database credentials in frontend code. Store them securely on the backend.

5. **Permissions**: All endpoints require appropriate permissions (KB_VIEW, KB_CREATE, DB_QUERY, etc.)
