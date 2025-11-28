# SQLite Upload API Specification

## Endpoint
`POST /api/v1/db/upload-sqlite`

## Description
Upload a SQLite database file to the server for use with the AI Agent. The file is stored in a tenant-specific directory and can be connected to via the `/db/connect` endpoint.

## Authentication
Required: Bearer token

## Request
**Content-Type:** `multipart/form-data`

**Form Fields:**
- `file` (required): SQLite database file (.db, .sqlite, .sqlite3)

## Response

### Success (200 OK)
```json
{
  "message": "SQLite database uploaded successfully",
  "file_path": "sqlite:///uploads/tenant_abc123/databases/mydb.sqlite",
  "filename": "mydb.sqlite",
  "size_mb": 2.5,
  "tenant_id": "abc123"
}
```

### Error Responses

**400 Bad Request - Invalid file type:**
```json
{
  "detail": "Invalid file type. Only SQLite files (.db, .sqlite, .sqlite3) are allowed."
}
```

**413 Payload Too Large - File too big:**
```json
{
  "detail": "File size exceeds maximum allowed size of 100MB"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Failed to save file: <error message>"
}
```

## Usage Flow

1. **Upload SQLite file:**
   ```
   POST /api/v1/db/upload-sqlite
   Form data: file=mydb.sqlite
   ```

2. **Connect to uploaded database:**
   ```
   POST /api/v1/db/connect
   Body: {
     "db_uri": "sqlite:///uploads/tenant_abc123/databases/mydb.sqlite"
   }
   ```

3. **Query the database:**
   ```
   POST /api/v1/db/generate-query
   Body: { "question": "Show me all tables" }
   ```

## File Storage

- Files are stored in: `uploads/{tenant_id}/databases/`
- Maximum file size: 100MB
- Allowed extensions: `.db`, `.sqlite`, `.sqlite3`
- Files are isolated per tenant

## Security Notes

1. Files are stored in tenant-specific directories
2. Only authenticated users can upload
3. File type validation prevents non-SQLite uploads
4. Size limits prevent abuse
5. Uploaded files are only accessible by the uploading tenant

## Example cURL Request

```bash
curl -X POST http://localhost:8000/api/v1/db/upload-sqlite \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/database.sqlite"
```

## Example JavaScript (Frontend)

```javascript
const uploadSQLite = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('http://localhost:8000/api/v1/db/upload-sqlite', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`
    },
    body: formData
  });

  const data = await response.json();
  
  if (response.ok) {
    // Use data.file_path to connect to the database
    console.log('Upload successful:', data.file_path);
    return data;
  } else {
    throw new Error(data.detail);
  }
};
```
