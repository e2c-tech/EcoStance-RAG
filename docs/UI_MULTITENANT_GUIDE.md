# Multitenant UI Guide

Complete guide for the new Streamlit multitenant interface.

## 🎯 Overview

The new UI provides a modern, tenant-aware interface with:
- Secure authentication
- File management with quota tracking
- Knowledge base chat
- Real-time storage monitoring
- Beautiful, responsive design

## 🚀 Quick Start

### 1. Start Backend
```bash
uvicorn app.main:app --reload
```

### 2. Start UI
```bash
# Option 1: Using run script
python run_ui.py

# Option 2: Direct streamlit
streamlit run ui/app_multitenant.py
```

### 3. Login
- Open http://localhost:8501
- Enter Tenant ID: `default-tenant`
- Click "Login"

## 📱 Features

### Authentication System
- **JWT Token-based**: Secure authentication with tokens
- **Tenant Isolation**: Each tenant sees only their data
- **Session Management**: Automatic session handling
- **Easy Logout**: One-click logout

### Dashboard
- **Metrics Overview**: Files, KBs, Storage, Quota
- **Recent Files**: Last 5 uploaded files
- **Knowledge Bases**: Available KBs list
- **Real-time Updates**: Live storage tracking

### File Management
**Upload Tab:**
- Drag & drop file upload
- Supported formats: PDF, TXT, DOCX, XLSX, MD
- Quota checking before upload
- Direct processing to Qdrant
- Custom knowledge base naming

**My Files Tab:**
- List all tenant files
- File details (size, date)
- Delete functionality
- Refresh button

### Knowledge Base Chat
- Select knowledge base
- Ask questions in natural language
- Get AI-powered answers
- Conversation history
- Context-aware responses
- Clear chat option

### Sidebar
- Account information
- Navigation menu
- Storage usage display
- Progress bar
- Logout button

## 🎨 UI Components

### Tenant Header
```
┌─────────────────────────────────┐
│   🏢 your-tenant-id             │
│   Multitenant RAG System        │
└─────────────────────────────────┘
```

### Metrics Cards
```
┌──────────┬──────────┬──────────┬──────────┐
│ 📁 Files │ 📚 KBs   │ 💾 Storage│ 📊 Quota │
│    5     │    3     │  125 MB  │  1.25%   │
└──────────┴──────────┴──────────┴──────────┘
```

### Storage Progress
```
💾 Storage Usage
Files: 5
Storage: 125.50 MB
[████░░░░░░░░░░░░░░░░] 1.25%
0.123 GB / 10 GB
```

## 📖 Usage Examples

### Example 1: Upload and Process Document

1. **Login**
   - Tenant ID: `acme-corp`
   - Click "Login"

2. **Upload File**
   - Go to "File Management"
   - Click "Upload" tab
   - Choose PDF file
   - Enter KB name: `company-docs`
   - Click "Upload & Process"

3. **Wait for Processing**
   - Job ID displayed
   - Collection name shown
   - Processing happens in background

4. **Query Documents**
   - Go to "Knowledge Base Chat"
   - Select `company-docs`
   - Ask: "What is our refund policy?"
   - Get AI answer

### Example 2: Manage Files

1. **View Files**
   - Go to "File Management"
   - Click "My Files" tab
   - See all uploaded files

2. **Delete Old Files**
   - Click 🗑️ next to file
   - Confirm deletion
   - Storage usage updates

3. **Check Storage**
   - View sidebar
   - See updated usage
   - Monitor quota

### Example 3: Chat with Documents

1. **Select Knowledge Base**
   - Go to "Knowledge Base Chat"
   - Choose KB from dropdown

2. **Ask Questions**
   - Type: "Summarize the main points"
   - Get AI response
   - Ask follow-up: "Tell me more about section 3"

3. **Clear History**
   - Click "Clear Chat"
   - Start fresh conversation

## 🔧 Configuration

### Backend URL
```python
# In ui/app_multitenant.py
BACKEND_URL = "http://127.0.0.1:8000/api/v1"

# Or set environment variable
export BACKEND_URL=http://your-backend:8000/api/v1
```

### Streamlit Config
Create `.streamlit/config.toml`:
```toml
[server]
port = 8501
address = "localhost"

[theme]
primaryColor = "#667eea"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#262730"
textColor = "#fafafa"
```

## 🎨 Customization

### Change Theme Colors
```python
# In inject_custom_css()
.tenant-header {
    background: linear-gradient(90deg, #YOUR_COLOR1 0%, #YOUR_COLOR2 100%);
}
```

### Add Custom Metrics
```python
def show_dashboard():
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col5:
        st.metric("Custom Metric", "Value")
```

### Add New Page
```python
def show_new_feature():
    st.title("New Feature")
    # Your code

# In sidebar
page = st.radio(
    "Select Page",
    ["Dashboard", "Files", "Chat", "New Feature"]
)

if page == "New Feature":
    show_new_feature()
```

## 🔐 Security

### Authentication Flow
```
1. User enters tenant_id
2. UI calls /auth/login
3. Backend returns JWT token
4. Token stored in session_state
5. Token sent in Authorization header
6. Backend validates token
7. Returns tenant-specific data
```

### Session Management
- Tokens stored in `st.session_state`
- Cleared on logout
- Not persisted to disk
- Expires after 30 minutes

### Data Isolation
- All API calls include tenant context
- Backend enforces tenant isolation
- No cross-tenant data access
- Secure file operations

## 📊 Monitoring

### Storage Usage
- Real-time tracking
- Progress bar visualization
- Quota percentage
- MB and GB display

### File Tracking
- Total file count
- Individual file sizes
- Upload timestamps
- Storage breakdown

### Knowledge Base Stats
- Number of KBs
- Documents per KB
- Collection names

## 🐛 Troubleshooting

### Issue: Can't Login
**Symptoms**: Login button doesn't work

**Solutions**:
1. Check backend is running
2. Verify tenant ID is correct
3. Check browser console for errors
4. Try `default-tenant`

### Issue: Upload Fails
**Symptoms**: File upload returns error

**Solutions**:
1. Check file size (quota limit)
2. Verify file format is supported
3. Check backend logs
4. Try smaller file

### Issue: No Knowledge Bases
**Symptoms**: KB dropdown is empty

**Solutions**:
1. Upload files first
2. Process files to Qdrant
3. Wait for processing to complete
4. Refresh page

### Issue: Chat Not Working
**Symptoms**: No response from chat

**Solutions**:
1. Verify KB is selected
2. Check backend is running
3. Ensure documents are processed
4. Check backend logs

## 💡 Tips & Tricks

### Tip 1: Fast File Upload
- Use "Upload & Process" for one-step operation
- Saves time vs separate upload + process

### Tip 2: Monitor Storage
- Check sidebar regularly
- Delete old files to free space
- Plan uploads based on quota

### Tip 3: Better Chat Results
- Ask specific questions
- Reference document sections
- Use follow-up questions
- Clear chat for new topics

### Tip 4: Organize Knowledge Bases
- Use descriptive KB names
- Group related documents
- Separate by topic or project

### Tip 5: Session Management
- Logout when switching tenants
- Don't share login credentials
- Monitor active sessions

## 🔄 Workflow Examples

### Workflow 1: New Document Processing
```
1. Login → 2. Upload File → 3. Process to KB → 4. Chat with Document
```

### Workflow 2: File Cleanup
```
1. Dashboard (check usage) → 2. File Management → 3. Delete old files → 4. Verify storage
```

### Workflow 3: Multi-Document Query
```
1. Upload multiple files → 2. Process to same KB → 3. Chat with all documents
```

## 📈 Best Practices

### File Management
- ✅ Use descriptive filenames
- ✅ Organize by knowledge base
- ✅ Delete processed files if not needed
- ✅ Monitor storage regularly
- ❌ Don't upload duplicate files
- ❌ Don't exceed quota limits

### Knowledge Base Organization
- ✅ Group related documents
- ✅ Use clear KB names
- ✅ Separate by topic
- ✅ Update regularly
- ❌ Don't mix unrelated content
- ❌ Don't create too many KBs

### Chat Usage
- ✅ Ask specific questions
- ✅ Use context from previous answers
- ✅ Clear chat for new topics
- ✅ Reference document sections
- ❌ Don't ask unrelated questions
- ❌ Don't expect answers outside documents

## 🚀 Advanced Features

### Custom API Calls
```python
def custom_api_call():
    response = requests.get(
        f"{BACKEND_URL}/custom-endpoint/",
        headers=get_headers()
    )
    return response.json()
```

### Session State Management
```python
# Store custom data
st.session_state.custom_data = "value"

# Access later
if 'custom_data' in st.session_state:
    data = st.session_state.custom_data
```

### Error Handling
```python
try:
    result = api_call()
except requests.exceptions.RequestException as e:
    st.error(f"Error: {e}")
    if hasattr(e.response, 'json'):
        st.json(e.response.json())
```

## 📝 Keyboard Shortcuts

- `Ctrl + R`: Refresh page
- `Ctrl + K`: Focus search (if implemented)
- `Enter`: Send chat message
- `Esc`: Close modals

## 🎯 Next Steps

After mastering the UI:
1. Explore API documentation
2. Try database chat (coming soon)
3. Set up admin interface
4. Configure custom quotas
5. Integrate with your systems

## 📚 Related Documentation

- [Phase 1 Complete Summary](PHASE_1_COMPLETE_SUMMARY.md)
- [Phase 2 Complete Summary](PHASE_2_COMPLETE_SUMMARY.md)
- [Authentication Guide](AUTHENTICATION_GUIDE.md)
- [File Storage Summary](PHASE_2.3_FILE_STORAGE_SUMMARY.md)

## 🆘 Support

For help:
- Check backend logs: `tail -f errorlog.txt`
- Review API docs: http://localhost:8000/docs
- Check browser console
- Verify authentication token
