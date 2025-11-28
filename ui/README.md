# Multitenant Streamlit UI

Modern, tenant-aware Streamlit interface for the RAG system with full multitenancy support.

## Features

### 🔐 Authentication
- Tenant-based login with JWT tokens
- Secure session management
- Easy logout functionality

### 📊 Dashboard
- Overview of files, knowledge bases, and storage
- Real-time storage usage metrics
- Recent files and KB listings

### 📁 File Management
- Upload files with quota checking
- View all tenant files
- Delete files
- Direct upload & process to Qdrant
- Storage usage tracking

### 💬 Knowledge Base Chat
- Select from tenant knowledge bases
- Chat with your documents
- Conversation history
- Context-aware responses

### 🗄️ Database Chat
- Coming soon: Natural language to SQL
- Tenant-isolated database connections

## Installation

```bash
# Install dependencies (if not already installed)
pip install streamlit requests pandas

# Or use requirements.txt
pip install -r requirements.txt
```

## Running the UI

### Start Backend First
```bash
# In project root
uvicorn app.main:app --reload
```

### Start Streamlit UI
```bash
# In project root
streamlit run ui/app_multitenant.py

# Or specify port
streamlit run ui/app_multitenant.py --server.port 8501
```

## Usage

### 1. Login
- Enter your tenant ID (e.g., `default-tenant`)
- Optionally enter user ID
- Click "Login"

### 2. Dashboard
- View your storage usage
- See recent files
- Check knowledge bases

### 3. Upload Files
- Go to "File Management" → "Upload" tab
- Choose a file
- Either:
  - Upload only (for later processing)
  - Upload & Process (directly to knowledge base)

### 4. Chat with Documents
- Go to "Knowledge Base Chat"
- Select a knowledge base
- Ask questions about your documents
- Get AI-powered answers

## Configuration

### Backend URL
Set the backend URL via environment variable:
```bash
export BACKEND_URL=http://localhost:8000/api/v1
```

Or modify in the code:
```python
BACKEND_URL = "http://127.0.0.1:8000/api/v1"
```

## Features by Page

### Dashboard (📊)
- **Metrics**: Files, KBs, Storage, Quota
- **Recent Files**: Last 5 uploaded files
- **Knowledge Bases**: List of available KBs

### File Management (📁)
**Upload Tab:**
- Drag & drop file upload
- Quota checking before upload
- Direct processing to Qdrant
- Custom KB naming

**My Files Tab:**
- List all tenant files
- File size and date
- Delete functionality
- Refresh button

### Knowledge Base Chat (💬)
- KB selection dropdown
- Chat interface
- Message history
- Clear chat option
- Context-aware responses

### Database Chat (🗄️)
- Coming in Phase 3
- Natural language to SQL
- Query execution
- Results visualization

## Tenant Isolation

All operations are tenant-isolated:
- ✅ Files stored in `uploads/{tenant_id}/`
- ✅ Collections named `tenant_{tenant_id}_{kb_name}`
- ✅ Storage quotas per tenant
- ✅ Separate chat histories
- ✅ Secure JWT authentication

## Storage Quotas

- **Default Quota**: 10 GB per tenant
- **Tracking**: Real-time usage display
- **Enforcement**: Upload rejected if quota exceeded
- **Display**: Progress bar and percentage

## Troubleshooting

### Backend Connection Error
```
Error: Connection refused
```
**Solution**: Make sure backend is running on port 8000

### Authentication Failed
```
Error: Login failed
```
**Solution**: 
- Check tenant ID is correct
- Ensure backend is running
- Try `default-tenant` for testing

### Upload Quota Exceeded
```
Error: Storage quota exceeded
```
**Solution**:
- Delete old files
- Contact admin to increase quota

### No Knowledge Bases
```
Warning: No knowledge bases available
```
**Solution**:
- Upload files first
- Process them to Qdrant
- Refresh the page

## Development

### File Structure
```
ui/
├── app_multitenant.py    # New multitenant UI
├── app.py                 # Legacy UI
├── app_fixed.py          # Legacy fixed UI
└── README.md             # This file
```

### Adding New Features

1. **Add API Function**:
```python
def new_api_call() -> Optional[Dict]:
    try:
        response = requests.get(
            f"{BACKEND_URL}/new-endpoint/",
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed: {e}")
        return None
```

2. **Add New Page**:
```python
def show_new_page():
    st.title("New Feature")
    # Your code here

# In show_main_app():
page = st.radio(
    "Select Page",
    ["Dashboard", "Files", "Chat", "New Feature"]
)

if page == "New Feature":
    show_new_page()
```

## Screenshots

### Login Page
- Clean, centered login form
- Tenant ID and User ID inputs
- Demo tenant suggestion

### Dashboard
- 4 metric cards (Files, KBs, Storage, Quota)
- Recent files table
- Knowledge bases list
- Tenant header with gradient

### File Management
- Two-tab interface (Upload / My Files)
- Drag & drop upload
- File list with delete buttons
- Storage usage in sidebar

### Knowledge Base Chat
- KB selector dropdown
- Chat interface with history
- User and assistant messages
- Clear chat button

## Tips

1. **Use Default Tenant**: Start with `default-tenant` for testing
2. **Check Storage**: Monitor usage in sidebar
3. **Clear Chat**: Use clear button to start fresh conversations
4. **Refresh Files**: Click refresh after uploads
5. **Logout**: Always logout when switching tenants

## Next Steps

- [ ] Add database chat functionality
- [ ] Add admin interface
- [ ] Add usage analytics
- [ ] Add file preview
- [ ] Add bulk operations
- [ ] Add export functionality

## Support

For issues or questions:
- Check backend logs
- Verify authentication
- Check network connectivity
- Review API documentation
