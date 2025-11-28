# Streamlit UI Requirements - Multitenant RAG System

## Overview

This document outlines comprehensive requirements for the Streamlit-based frontend for the multitenant RAG (Retrieval-Augmented Generation) system. The UI provides an intuitive interface for managing knowledge bases, querying documents, interacting with databases, and administering tenants.

---

## Design Philosophy for Streamlit

**Streamlit-Specific Considerations:**
- Leverage Streamlit's native components (st.tabs, st.expander, st.columns, st.metric)
- Use session state for maintaining user context and chat history
- Implement real-time updates with st.rerun() for dynamic content
- Utilize st.spinner() for loading states and user feedback
- Apply custom CSS sparingly via st.markdown() for enhanced styling
- Design for single-page app with tabs for major sections
- Optimize for both desktop and mobile viewing

---

## Core Features & Pages

### 1. Authentication & Session Management

**Login Page (Separate or Sidebar)**

**Streamlit Implementation:**
```python
# In sidebar or main area
with st.form("login_form"):
    tenant_id = st.text_input("Tenant ID", placeholder="your-tenant-id")
    email = st.text_input("Email", placeholder="user@example.com")
    api_key = st.text_input("API Key", type="password", placeholder="sk_...")
    remember_me = st.checkbox("Remember me")
    
    col1, col2 = st.columns(2)
    with col1:
        login_btn = st.form_submit_button("Login", type="primary", use_container_width=True)
    with col2:
        forgot_btn = st.form_submit_button("Forgot Password?", use_container_width=True)
    
    if login_btn:
        # Handle authentication
        pass
```

**Session State Management:**
- Store authentication token in `st.session_state.auth_token`
- Store tenant info in `st.session_state.tenant_info`
- Store user preferences in `st.session_state.user_prefs`
- Implement token refresh logic with background checks
- Clear session state on logout

**Features:**
- Auto-logout on token expiration with warning message
- Persistent tenant context across page reloads
- Session timeout warning (5 min before expiry)
- Error messages displayed with st.error()
- Success messages with st.success()

---

### 2. Main Dashboard (Home Tab)

**Overview Metrics Section**

**Streamlit Implementation:**
```python
st.header("📊 Dashboard Overview")

# Metrics in columns
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Knowledge Bases", kb_count, delta="+2 this week")
with col2:
    st.metric("Total Documents", doc_count, delta="+15")
with col3:
    storage_pct = (storage_used / storage_limit) * 100
    st.metric("Storage Used", f"{storage_used:.2f} GB", 
              delta=f"{storage_pct:.1f}% of limit")
with col4:
    st.metric("Queries (Month)", query_count, delta="+127")
```

**Quick Actions Section:**
```python
st.subheader("⚡ Quick Actions")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("📤 Upload Document", use_container_width=True):
        st.session_state.show_upload_modal = True

with col2:
    if st.button("➕ Create KB", use_container_width=True):
        st.session_state.show_create_kb_modal = True

with col3:
    if st.button("🔌 Connect Database", use_container_width=True):
        st.session_state.active_tab = "database"

with col4:
    if st.button("💬 Ask Question", use_container_width=True):
        st.session_state.active_tab = "chat"
```

**Recent Activity Feed:**
```python
st.subheader("📋 Recent Activity")

with st.expander("View Recent Activity", expanded=True):
    for activity in recent_activities[:10]:
        col1, col2 = st.columns([4, 1])
        with col1:
            icon = "📄" if activity['type'] == 'upload' else "💬"
            st.write(f"{icon} {activity['description']}")
        with col2:
            st.caption(activity['timestamp'])
```

**Usage Charts:**
```python
st.subheader("📈 Usage Trends")

tab1, tab2, tab3 = st.tabs(["Storage", "Queries", "API Calls"])

with tab1:
    # Storage usage line chart
    st.line_chart(storage_data)
    
with tab2:
    # Query volume bar chart
    st.bar_chart(query_data)
    
with tab3:
    # API calls line chart
    st.line_chart(api_data)
```

---

### 3. Knowledge Base Management

#### **Knowledge Base List Page**

**Streamlit Implementation:**
```python
st.header("📚 Knowledge Bases")

# View toggle and search
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    search_query = st.text_input("🔍 Search knowledge bases", 
                                  placeholder="Search by name...")
with col2:
    sort_by = st.selectbox("Sort by", 
                           ["Name", "Date Created", "Document Count", "Size"])
with col3:
    view_mode = st.radio("View", ["Grid", "List"], horizontal=True)

st.divider()

# Display knowledge bases
knowledge_bases = get_knowledge_bases()  # API call

if view_mode == "Grid":
    # Grid view with 3 columns
    cols = st.columns(3)
    for idx, kb in enumerate(knowledge_bases):
        with cols[idx % 3]:
            with st.container():
                st.markdown(f"### 📁 {kb['name']}")
                st.metric("Documents", kb['doc_count'])
                st.metric("Vectors", f"{kb['vector_count']:,}")
                st.caption(f"Updated: {kb['last_updated']}")
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if st.button("👁️", key=f"view_{kb['name']}", 
                                help="View details"):
                        st.session_state.selected_kb = kb['name']
                        st.session_state.show_kb_details = True
                with col_b:
                    if st.button("💬", key=f"query_{kb['name']}", 
                                help="Query KB"):
                        st.session_state.selected_kb = kb['name']
                        st.session_state.active_tab = "chat"
                with col_c:
                    if st.button("🗑️", key=f"del_{kb['name']}", 
                                help="Delete KB"):
                        st.session_state.kb_to_delete = kb['name']
else:
    # List view with table
    kb_df = pd.DataFrame(knowledge_bases)
    st.dataframe(
        kb_df,
        column_config={
            "name": st.column_config.TextColumn("Name", width="medium"),
            "doc_count": st.column_config.NumberColumn("Documents", width="small"),
            "vector_count": st.column_config.NumberColumn("Vectors", width="small"),
            "last_updated": st.column_config.DatetimeColumn("Last Updated", width="medium"),
        },
        hide_index=True,
        use_container_width=True
    )
```

#### **Create Knowledge Base Modal**

**Streamlit Implementation:**
```python
# Triggered by button or session state
if st.session_state.get('show_create_kb_modal', False):
    with st.form("create_kb_form"):
        st.subheader("➕ Create New Knowledge Base")
        
        kb_name = st.text_input(
            "Knowledge Base Name*",
            placeholder="e.g., Product Documentation",
            help="Must be unique and contain only letters, numbers, and underscores"
        )
        
        kb_description = st.text_area(
            "Description (Optional)",
            placeholder="Brief description of this knowledge base...",
            max_chars=500
        )
        
        col1, col2 = st.columns(2)
        with col1:
            create_btn = st.form_submit_button("Create", type="primary", 
                                               use_container_width=True)
        with col2:
            cancel_btn = st.form_submit_button("Cancel", 
                                               use_container_width=True)
        
        if create_btn and kb_name:
            # Validate and create KB
            if validate_kb_name(kb_name):
                result = create_knowledge_base(kb_name, kb_description)
                if result['success']:
                    st.success(f"✅ Knowledge base '{kb_name}' created!")
                    st.session_state.show_create_kb_modal = False
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ {result['error']}")
            else:
                st.error("Invalid KB name. Use only letters, numbers, and underscores.")
        
        if cancel_btn:
            st.session_state.show_create_kb_modal = False
            st.rerun()
```

#### **Knowledge Base Details Page**

**Streamlit Implementation:**
```python
st.header(f"📁 {selected_kb}")

# Fetch KB details
kb_details = get_knowledge_base_details(selected_kb)

# Metadata section
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Vectors", f"{kb_details['total_points']:,}")
with col2:
    st.metric("Files", kb_details['files_count'])
with col3:
    st.metric("Vector Size", kb_details['vector_size'])
with col4:
    total_chunks = sum(f['chunk_count'] for f in kb_details['files'])
    st.metric("Total Chunks", f"{total_chunks:,}")

st.divider()

# Action buttons
col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
with col1:
    if st.button("📤 Upload Document", use_container_width=True):
        st.session_state.show_upload_to_kb = True
with col2:
    if st.button("💬 Query KB", use_container_width=True):
        st.session_state.active_tab = "chat"
with col3:
    search_docs = st.text_input("🔍 Search documents", 
                                placeholder="Search within KB...")
with col4:
    if st.button("🗑️ Delete KB", type="secondary"):
        st.session_state.confirm_delete_kb = True

# Confirmation dialog for KB deletion
if st.session_state.get('confirm_delete_kb', False):
    st.warning(f"⚠️ Are you sure you want to delete '{selected_kb}'? This action cannot be undone.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, Delete", type="primary", use_container_width=True):
            if delete_knowledge_base(selected_kb):
                st.success(f"✅ Deleted '{selected_kb}'")
                st.session_state.confirm_delete_kb = False
                st.session_state.selected_kb = None
                time.sleep(1)
                st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.session_state.confirm_delete_kb = False
            st.rerun()

st.divider()

# Document list
st.subheader("📄 Documents")

files = kb_details.get('files', [])

if files:
    # Pagination
    items_per_page = 10
    total_pages = (len(files) + items_per_page - 1) // items_per_page
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    
    # Page selector
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page = st.selectbox(
            "Page",
            range(1, total_pages + 1),
            index=st.session_state.current_page - 1,
            key="page_selector"
        )
        st.session_state.current_page = page
    
    # Display files for current page
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_files = files[start_idx:end_idx]
    
    for idx, file_info in enumerate(page_files):
        with st.expander(f"📄 {file_info['filename']} ({file_info['chunk_count']} chunks)"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**File Type:** {file_info.get('file_type', 'Unknown')}")
                st.write(f"**Upload Date:** {file_info.get('upload_date', 'Unknown')}")
                st.write(f"**File Size:** {file_info.get('file_size', 'Unknown')}")
                st.write(f"**Characters:** {file_info.get('total_characters', 0):,}")
                st.write(f"**Chunks:** {file_info.get('chunk_count', 0)}")
            
            with col2:
                filename = file_info['filename']
                
                # Download button
                if st.button("⬇️ Download", key=f"dl_{idx}", 
                            use_container_width=True):
                    download_file(selected_kb, filename)
                
                # Reindex button
                if st.button("🔄 Reindex", key=f"reindex_{idx}", 
                            use_container_width=True):
                    with st.spinner(f"Reindexing {filename}..."):
                        if reindex_file_in_kb(selected_kb, filename):
                            st.success(f"✅ Reindexed {filename}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Reindexing failed")
                
                # Delete button with confirmation
                if st.button("🗑️ Delete", key=f"del_{idx}", 
                            type="secondary", use_container_width=True):
                    if st.session_state.get(f"confirm_del_{idx}", False):
                        with st.spinner(f"Deleting {filename}..."):
                            if delete_file_from_kb(selected_kb, filename):
                                st.success(f"✅ Deleted {filename}")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Deletion failed")
                    else:
                        st.session_state[f"confirm_del_{idx}"] = True
                        st.warning("Click again to confirm")
else:
    st.info("📭 No documents in this knowledge base yet. Upload your first document!")
```

#### **Document Upload Interface**

**Streamlit Implementation:**
```python
st.subheader("📤 Upload Documents")

# KB selector
kb_options = ["-- Create New KB --"] + get_knowledge_bases()
selected_kb = st.selectbox(
    "Select Knowledge Base",
    options=kb_options,
    help="Choose existing KB or create a new one"
)

# If creating new KB
if selected_kb == "-- Create New KB --":
    new_kb_name = st.text_input(
        "New Knowledge Base Name*",
        placeholder="e.g., customer-support-docs"
    )
    kb_to_use = new_kb_name
else:
    kb_to_use = selected_kb

st.divider()

# File uploader with drag-and-drop
uploaded_files = st.file_uploader(
    "Choose files to upload",
    type=['pdf', 'docx', 'txt', 'md', 'xlsx', 'xls', 'csv', 'html', 'htm', 'sql', 'jsonl'],
    accept_multiple_files=True,
    help="Drag and drop files here or click to browse"
)

# Display supported formats
with st.expander("ℹ️ Supported File Formats"):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("📄 **Documents**")
        st.write("- PDF (.pdf)")
        st.write("- Word (.docx)")
        st.write("- Text (.txt)")
        st.write("- Markdown (.md)")
    with col2:
        st.write("📊 **Spreadsheets**")
        st.write("- Excel (.xlsx, .xls)")
        st.write("- CSV (.csv)")
    with col3:
        st.write("🌐 **Web & Data**")
        st.write("- HTML (.html, .htm)")
        st.write("- SQL (.sql)")
        st.write("- JSONL (.jsonl)")

# Storage quota indicator
storage_info = get_storage_usage()
storage_pct = (storage_info['used_gb'] / storage_info['limit_gb']) * 100

st.progress(storage_pct / 100)
st.caption(f"Storage: {storage_info['used_gb']:.2f} GB / {storage_info['limit_gb']:.2f} GB ({storage_pct:.1f}%)")

if storage_pct > 90:
    st.warning("⚠️ Storage quota almost full! Consider upgrading your plan.")

st.divider()

# Upload button
if st.button("📤 Upload and Process", type="primary", 
            disabled=not uploaded_files or not kb_to_use,
            use_container_width=True):
    
    if not kb_to_use:
        st.error("Please select or create a knowledge base")
    elif not uploaded_files:
        st.error("Please select at least one file")
    else:
        # Process each file
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Processing {idx + 1}/{len(uploaded_files)}: {uploaded_file.name}")
            
            # Upload file
            with st.spinner(f"Uploading {uploaded_file.name}..."):
                file_path = upload_file(uploaded_file)
            
            if file_path:
                # Process file
                result = process_file(file_path, kb_to_use)
                
                if result and 'job_id' in result:
                    # Add to processing jobs
                    if 'processing_jobs' not in st.session_state:
                        st.session_state.processing_jobs = []
                    
                    st.session_state.processing_jobs.append({
                        'job_id': result['job_id'],
                        'filename': uploaded_file.name,
                        'kb_name': kb_to_use,
                        'started_at': time.time(),
                        'status': 'pending'
                    })
                    
                    st.success(f"✅ {uploaded_file.name} - Processing started")
                else:
                    st.error(f"❌ {uploaded_file.name} - Processing failed")
            else:
                st.error(f"❌ {uploaded_file.name} - Upload failed")
            
            # Update progress
            progress_bar.progress((idx + 1) / len(uploaded_files))
        
        status_text.text("✅ All files processed!")
        time.sleep(2)
        st.rerun()
```

#### **Processing Jobs Status Monitor**

**Streamlit Implementation:**
```python
# In sidebar or dedicated section
if 'processing_jobs' in st.session_state and st.session_state.processing_jobs:
    st.subheader("📊 Processing Jobs")
    
    jobs_to_remove = []
    
    for idx, job in enumerate(st.session_state.processing_jobs):
        # Get current status
        job_status = get_job_status(job['job_id'])
        
        if job_status:
            status = job_status.get('status', 'unknown')
            progress_msg = job_status.get('progress_message', 'No progress info')
            
            # Status icons
            status_icons = {
                'completed': '✅',
                'failed': '❌',
                'processing': '🔄',
                'pending': '⏳'
            }
            icon = status_icons.get(status, '❓')
            
            # Display job status
            with st.expander(f"{icon} {job['filename']} → {job['kb_name']} ({status})"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Status:** {status.upper()}")
                    st.write(f"**Progress:** {progress_msg}")
                    
                    if job_status.get('error_message'):
                        st.error(f"Error: {job_status['error_message']}")
                    
                    # Progress bar for processing
                    if status == 'processing':
                        st.progress(0.5)  # Indeterminate progress
                
                with col2:
                    # Remove button for completed/failed jobs
                    if status in ['completed', 'failed']:
                        if st.button("Remove", key=f"remove_{idx}"):
                            jobs_to_remove.append(idx)
            
            # Auto-remove old completed jobs (after 5 minutes)
            if status in ['completed', 'failed']:
                elapsed = time.time() - job['started_at']
                if elapsed > 300:  # 5 minutes
                    jobs_to_remove.append(idx)
    
    # Remove jobs
    for idx in reversed(jobs_to_remove):
        st.session_state.processing_jobs.pop(idx)
    
    # Auto-refresh if there are active jobs
    active_jobs = [j for j in st.session_state.processing_jobs 
                   if get_job_status(j['job_id']) and 
                   get_job_status(j['job_id']).get('status') in ['pending', 'processing']]
    
    if active_jobs:
        time.sleep(3)
        st.rerun()
```

