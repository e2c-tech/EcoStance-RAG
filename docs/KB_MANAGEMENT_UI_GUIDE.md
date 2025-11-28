# Knowledge Base Management UI Guide

## Overview
The new Knowledge Base Management interface provides an intuitive way to organize and manage your documents by knowledge base, with full tenant isolation.

## Navigation

The main navigation now includes:
- 📊 **Dashboard** - Overview of your tenant's resources
- 📚 **Knowledge Base Management** - Manage KBs and files (NEW!)
- 💬 **Knowledge Base Chat** - Chat with your documents
- 🗄️ **Database Chat** - Coming soon

## Knowledge Base Management

### Tab 1: Upload & Create

**Purpose**: Upload files and add them to knowledge bases

**Features**:
- File uploader supporting PDF, TXT, DOCX, XLSX, MD
- Knowledge base name input
- Single-click upload and processing
- Real-time feedback on upload status
- Automatic KB creation if name doesn't exist

**Workflow**:
1. Select a file from your computer
2. Enter a knowledge base name (e.g., "products", "docs", "support")
3. Click "Upload & Process to Knowledge Base"
4. Wait for processing to complete
5. File is now searchable in that KB

**Example Use Cases**:
- Create a "products" KB with all product documentation
- Create a "support" KB with FAQ and troubleshooting guides
- Create a "legal" KB with contracts and policies

### Tab 2: Manage Knowledge Bases

**Purpose**: View and manage your knowledge bases and their files

**Features**:
- Dropdown to select any KB
- Real-time statistics:
  - Total vectors (chunks) in KB
  - Number of files
- Delete entire knowledge base
- View all files in selected KB
- Delete individual files from KB

**KB Statistics Display**:
```
📊 Total Vectors: 150    📄 Files: 3    🗑️ Delete Knowledge Base
```

**File List Display**:
```
📄 document1.pdf          📦 50 chunks    🗑️
📄 document2.txt          📦 30 chunks    🗑️
📄 document3.docx         📦 70 chunks    🗑️
```

**Workflow**:
1. Select a KB from the dropdown
2. View statistics and files
3. Delete individual files if needed
4. Or delete entire KB (with confirmation)

## Dashboard

Shows overview of your tenant's resources:

**Metrics**:
- 📁 Files - Total files uploaded
- 📚 Knowledge Bases - Number of KBs
- 💾 Storage - Total storage used
- 📊 Quota Used - Percentage of quota

**Recent Files**: Shows last 5 uploaded files

**Knowledge Bases**: Lists all your KBs

## Knowledge Base Chat

**Purpose**: Ask questions about documents in a specific KB

**Features**:
- KB selector dropdown
- Chat interface with history
- Context-aware responses
- Clear chat button

**Workflow**:
1. Select a knowledge base
2. Type your question
3. Get AI-powered answers based on your documents
4. Continue conversation with context

**Example Questions**:
- "What are the main features of our product?"
- "How do I troubleshoot connection issues?"
- "What is our refund policy?"

## Sidebar

**Account Section**:
- Shows current tenant ID
- Logout button

**Navigation**:
- Radio buttons for page selection

**Storage Usage**:
- Real-time storage metrics
- Progress bar showing quota usage
- Detailed breakdown (MB/GB)

## Tenant Isolation

All operations are isolated by tenant:

**What This Means**:
- You only see YOUR knowledge bases
- You only see YOUR files
- You can only delete YOUR resources
- Your data is completely separate from other tenants

**Behind the Scenes**:
- KB "products" → Collection "your-tenant_products"
- Automatic tenant prefix on all operations
- JWT token authentication required
- API-level access control

## Tips & Best Practices

### Organizing Knowledge Bases

**Good KB Organization**:
```
products/          # Product documentation
  - product_guide.pdf
  - features.pdf
  - specs.xlsx

support/           # Customer support
  - faq.pdf
  - troubleshooting.pdf
  - common_issues.txt

legal/             # Legal documents
  - terms.pdf
  - privacy.pdf
  - contracts.pdf
```

**Benefits**:
- Faster, more relevant search results
- Easier to manage and update
- Better chat responses
- Clearer organization

### File Management

**Best Practices**:
1. Use descriptive KB names
2. Group related documents together
3. Delete outdated files regularly
4. Monitor storage usage
5. Test chat after uploading new files

### Storage Management

**Monitor Your Usage**:
- Check sidebar for current usage
- Delete unused files/KBs
- Compress large files before upload
- Use appropriate file formats

**Quota Limits**:
- Default: 10 GB per tenant
- Shown in sidebar and dashboard
- Warning when approaching limit

## Troubleshooting

### "No knowledge bases found"
- Upload and process files first
- Check that processing completed successfully
- Refresh the page

### "Knowledge base not found"
- Ensure you're logged in as correct tenant
- Check KB name spelling
- Refresh the page

### Files not appearing in KB
- Wait for processing to complete
- Check job status in upload response
- Verify file format is supported

### Chat not working
- Ensure KB has files
- Check that files were processed successfully
- Try refreshing the page

## API Integration

For developers integrating with the API:

**Authentication**:
```python
response = requests.post(
    "http://127.0.0.1:8000/api/v1/auth/login",
    json={"tenant_id": "your-tenant"}
)
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
```

**List KBs**:
```python
response = requests.get(
    "http://127.0.0.1:8000/api/v1/manage/knowledge-bases/",
    headers=headers
)
kbs = response.json()  # ["products", "support", "legal"]
```

**Get KB Files**:
```python
response = requests.get(
    "http://127.0.0.1:8000/api/v1/manage/knowledge-bases/products/files",
    headers=headers
)
files = response.json()["files"]
```

## Security

**Authentication**:
- JWT tokens required for all operations
- Tokens expire after 30 minutes
- Refresh tokens valid for 7 days

**Authorization**:
- Tenant ID embedded in token
- All operations scoped to tenant
- No cross-tenant access possible

**Data Isolation**:
- Separate collections per tenant
- Separate file storage per tenant
- Separate credentials per tenant

## Support

For issues or questions:
1. Check this guide
2. Review API documentation
3. Check server logs
4. Contact system administrator

## Future Enhancements

Coming soon:
- Bulk file upload
- File preview
- KB sharing between tenants
- Advanced search filters
- Usage analytics
- Export functionality
