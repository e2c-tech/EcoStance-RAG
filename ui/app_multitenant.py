"""
Multitenant Streamlit UI for RAG System
Supports tenant authentication, file management, knowledge base queries, and database chat.
"""
import streamlit as st
import requests
import os
import time
import pandas as pd
from typing import Optional, Dict, Any

# --- Configuration ---
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000/api/v1")

# --- Page Configuration ---
st.set_page_config(
    page_title="Multitenant RAG System",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
def inject_custom_css():
    st.markdown("""
    <style>
    /* Tenant header */
    .tenant-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    /* Chat styling */
    div[data-testid="stChatInput"] {
        position: sticky;
        bottom: 0;
        z-index: 100;
        background-color: #0e1117;
    }
    
    .stChatInput > div {
        border-radius: 25px !important;
        border: 2px solid #667eea !important;
    }
    
    /* Metrics styling */
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: bold;
    }
    
    /* Success/Error boxes */
    .success-box {
        padding: 1rem;
        border-radius: 5px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    
    .error-box {
        padding: 1rem;
        border-radius: 5px;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Session State Initialization ---
def init_session_state():
    """Initialize session state variables."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'access_token' not in st.session_state:
        st.session_state.access_token = None
    if 'tenant_id' not in st.session_state:
        st.session_state.tenant_id = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'current_kb' not in st.session_state:
        st.session_state.current_kb = None
    if 'show_registration' not in st.session_state:
        st.session_state.show_registration = False

# --- Authentication Functions ---
def login(tenant_id: str, user_id: str = "user") -> bool:
    """Login and get JWT token."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/login",
            json={"tenant_id": tenant_id, "user_id": user_id}
        )
        response.raise_for_status()
        data = response.json()
        
        st.session_state.access_token = data["access_token"]
        st.session_state.tenant_id = tenant_id
        st.session_state.authenticated = True
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Login failed: {e}")
        return False

def logout():
    """Logout and clear session."""
    st.session_state.authenticated = False
    st.session_state.access_token = None
    st.session_state.tenant_id = None
    st.session_state.chat_history = []
    st.session_state.current_kb = None

def get_headers() -> Dict[str, str]:
    """Get authorization headers."""
    return {"Authorization": f"Bearer {st.session_state.access_token}"}

# --- API Functions ---
def upload_file(uploaded_file) -> Optional[str]:
    """Upload file to backend."""
    try:
        files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
        response = requests.post(
            f"{BACKEND_URL}/upload/",
            files=files,
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Upload failed: {e}")
        if hasattr(e.response, 'json'):
            error_detail = e.response.json().get('detail', {})
            if isinstance(error_detail, dict) and 'error' in error_detail:
                st.error(f"Quota: {error_detail['usage_percent']}% used")
        return None

def process_to_qdrant(file_path: str, kb_name: str) -> Optional[str]:
    """Process file and upload to Qdrant."""
    try:
        data = {"file_path": file_path, "kb_name": kb_name}
        response = requests.post(
            f"{BACKEND_URL}/upload-to-qdrant/",
            data=data,
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Processing failed: {e}")
        return None

def query_knowledge_base(kb_name: str, query: str, chat_history: list) -> Optional[str]:
    """Query knowledge base."""
    try:
        data = {
            "kb_name": kb_name,
            "query": query,
            "chat_history": chat_history
        }
        response = requests.post(
            f"{BACKEND_URL}/query/",
            data=data,
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()["answer"]
    except requests.exceptions.RequestException as e:
        st.error(f"Query failed: {e}")
        return None

def list_files() -> list:
    """List tenant files."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/files/",
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to list files: {e}")
        return []

def get_storage_usage() -> Optional[Dict]:
    """Get storage usage."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/files/storage/usage",
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to get storage usage: {e}")
        return None

def delete_file(filename: str) -> bool:
    """Delete a file."""
    try:
        response = requests.delete(
            f"{BACKEND_URL}/files/{filename}",
            headers=get_headers()
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to delete file: {e}")
        return False

def get_knowledge_bases() -> list:
    """Get list of knowledge bases."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/manage/knowledge-bases/",
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to get knowledge bases: {e}")
        return []

def get_kb_details(kb_name: str) -> Optional[Dict]:
    """Get knowledge base details."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/manage/knowledge-bases/{kb_name}/details",
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to get KB details: {e}")
        return None

def get_kb_files(kb_name: str) -> list:
    """Get files in knowledge base."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/manage/knowledge-bases/{kb_name}/files",
            headers=get_headers()
        )
        response.raise_for_status()
        return response.json().get("files", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to get KB files: {e}")
        return []

def delete_kb_file(kb_name: str, filename: str) -> bool:
    """Delete file from knowledge base."""
    try:
        response = requests.delete(
            f"{BACKEND_URL}/manage/knowledge-bases/{kb_name}/files/{filename}",
            headers=get_headers()
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to delete file: {e}")
        return False

def delete_knowledge_base(kb_name: str) -> bool:
    """Delete entire knowledge base."""
    try:
        response = requests.delete(
            f"{BACKEND_URL}/manage/knowledge-bases/{kb_name}",
            headers=get_headers()
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to delete knowledge base: {e}")
        return False

# --- Registration Functions ---
def register_tenant(company_name: str, email: str, password: str, phone: str = "") -> Optional[dict]:
    """Register a new tenant."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/tenants/register",
            json={
                "name": company_name,
                "email": email,
                "password": password,
                "phone": phone if phone else None,
                "billing_tier": "free"
            }
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Registration failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                st.error(f"Details: {error_detail}")
            except:
                pass
        return None

# --- Login/Registration Pages ---
def show_login_page():
    """Display login or registration page."""
    st.title("🏢 Multitenant RAG System")
    
    # Toggle between login and registration
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Create Account"])
        
        with tab1:
            show_login_form()
        
        with tab2:
            show_registration_form()

def show_login_form():
    """Display login form."""
    st.markdown("### Login to Your Account")
    st.markdown("")
    
    tenant_id = st.text_input(
        "Tenant ID",
        placeholder="e.g., acme-corp-abc123",
        help="Enter your tenant identifier (you received this when you registered)",
        key="login_tenant_id"
    )
    
    user_id = st.text_input(
        "User ID (optional)",
        value="user",
        placeholder="e.g., john.doe",
        help="Enter your user identifier",
        key="login_user_id"
    )
    
    st.markdown("")
    
    if st.button("🔐 Login", use_container_width=True, type="primary", key="login_button"):
        if tenant_id:
            with st.spinner("Authenticating..."):
                if login(tenant_id, user_id):
                    st.success("✅ Login successful!")
                    time.sleep(0.5)
                    st.rerun()
        else:
            st.error("Please enter a tenant ID")
    
    st.markdown("---")
    st.info("💡 **Demo:** Use `default-tenant` to try the system")

def show_registration_form():
    """Display registration form."""
    st.markdown("### Create Your Account")
    st.markdown("")
    
    company_name = st.text_input(
        "Company/Organization Name *",
        placeholder="e.g., Acme Corporation",
        help="Enter your company or organization name",
        key="reg_company"
    )
    
    email = st.text_input(
        "Email Address *",
        placeholder="e.g., admin@acme.com",
        help="Enter your email address",
        key="reg_email"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        password = st.text_input(
            "Password *",
            type="password",
            placeholder="Enter password",
            help="Choose a strong password",
            key="reg_password"
        )
    
    with col2:
        confirm_password = st.text_input(
            "Confirm Password *",
            type="password",
            placeholder="Re-enter password",
            help="Confirm your password",
            key="reg_confirm_password"
        )
    
    phone = st.text_input(
        "Phone Number (optional)",
        placeholder="e.g., +1-555-0123",
        help="Enter your phone number",
        key="reg_phone"
    )
    
    st.markdown("")
    
    col1, col2 = st.columns(2)
    
    with col1:
        billing_tier = st.selectbox(
            "Plan",
            ["free", "starter", "professional", "enterprise"],
            help="Select your billing plan"
        )
    
    with col2:
        st.markdown("")
        st.markdown("")
        if billing_tier == "free":
            st.caption("✅ 10GB storage, 1000 queries/day")
        elif billing_tier == "starter":
            st.caption("💼 50GB storage, 5000 queries/day")
        elif billing_tier == "professional":
            st.caption("🚀 200GB storage, 20000 queries/day")
        else:
            st.caption("⭐ Unlimited storage & queries")
    
    st.markdown("")
    
    if st.button("📝 Create Account", use_container_width=True, type="primary", key="register_button"):
        if not company_name or not email or not password or not confirm_password:
            st.error("Please fill in all required fields (marked with *)")
        elif "@" not in email:
            st.error("Please enter a valid email address")
        elif len(password) < 8:
            st.error("Password must be at least 8 characters long")
        elif password != confirm_password:
            st.error("Passwords do not match")
        else:
            with st.spinner("Creating your account..."):
                result = register_tenant(company_name, email, password, phone)
                if result:
                    st.success("✅ Account created successfully!")
                    st.balloons()
                    
                    # Show tenant info
                    st.markdown("---")
                    st.markdown("### 🎉 Welcome to the Multitenant RAG System!")
                    st.markdown("")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"**Tenant ID:**\n\n`{result['id']}`")
                    with col2:
                        st.info(f"**Slug:**\n\n`{result['slug']}`")
                    
                    st.markdown("")
                    st.warning("⚠️ **Important:** Save your Tenant ID! You'll need it to login.")
                    st.markdown("")
                    
                    # Auto-login option
                    if st.button("🚀 Login Now", use_container_width=True, type="primary"):
                        if login(result['id'], "admin"):
                            st.success("✅ Logged in!")
                            time.sleep(0.5)
                            st.rerun()
    
    st.markdown("---")
    st.caption("By creating an account, you agree to our Terms of Service and Privacy Policy")

# --- Main Application ---
def show_main_app():
    """Display main application."""
    inject_custom_css()
    
    # Tenant Header
    st.markdown(f"""
    <div class="tenant-header">
        <h2>🏢 {st.session_state.tenant_id}</h2>
        <p>Multitenant RAG System</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 👤 Account")
        st.write(f"**Tenant:** {st.session_state.tenant_id}")
        
        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()
        
        st.markdown("---")
        
        # Navigation
        st.markdown("### 📋 Navigation")
        page = st.radio(
            "Select Page",
            ["📊 Dashboard", "📚 Knowledge Base Management", "💬 Knowledge Base Chat", "🗄️ Database Chat"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Storage Usage
        st.markdown("### 💾 Storage Usage")
        usage = get_storage_usage()
        if usage:
            st.metric("Files", usage['total_files'])
            st.metric("Storage", f"{usage['total_mb']:.2f} MB")
            st.progress(min(usage['total_mb'] / 10000, 1.0))
            st.caption(f"{usage['total_gb']:.3f} GB / 10 GB")
    
    # Main Content
    if page == "📊 Dashboard":
        show_dashboard()
    elif page == "📚 Knowledge Base Management":
        show_kb_management()
    elif page == "💬 Knowledge Base Chat":
        show_kb_chat()
    elif page == "🗄️ Database Chat":
        show_db_chat()

# --- Dashboard Page ---
def show_dashboard():
    """Display dashboard."""
    st.title("📊 Dashboard")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    usage = get_storage_usage()
    files = list_files()
    kbs = get_knowledge_bases()
    
    with col1:
        st.metric("📁 Files", len(files) if files else 0)
    
    with col2:
        st.metric("📚 Knowledge Bases", len(kbs) if kbs else 0)
    
    with col3:
        if usage:
            st.metric("💾 Storage", f"{usage['total_mb']:.1f} MB")
    
    with col4:
        if usage:
            usage_pct = (usage['total_mb'] / 10000) * 100
            st.metric("📊 Quota Used", f"{usage_pct:.1f}%")
    
    st.markdown("---")
    
    # Recent Files
    st.markdown("### 📄 Recent Files")
    if files:
        df = pd.DataFrame(files)
        df = df[['filename', 'size_mb', 'created_at']].head(5)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No files uploaded yet")
    
    # Knowledge Bases
    st.markdown("### 📚 Knowledge Bases")
    if kbs:
        for kb in kbs:
            st.write(f"- **{kb}**")
    else:
        st.info("No knowledge bases created yet")

# --- Knowledge Base Management Page ---
def show_kb_management():
    """Display knowledge base management page."""
    st.title("📚 Knowledge Base Management")
    
    tab1, tab2 = st.tabs(["📤 Upload & Create", "📋 Manage Knowledge Bases"])
    
    with tab1:
        st.markdown("### Upload Files to Knowledge Base")
        
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['pdf', 'txt', 'docx', 'xlsx', 'md'],
            help="Supported formats: PDF, TXT, DOCX, XLSX, MD"
        )
        
        if uploaded_file:
            st.info(f"📄 **{uploaded_file.name}** ({uploaded_file.size / 1024:.2f} KB)")
            
            kb_name = st.text_input(
                "Knowledge Base Name", 
                value="default",
                help="Enter existing KB name to add to it, or new name to create"
            )
            
            if st.button("🚀 Upload & Process to Knowledge Base", type="primary", use_container_width=True):
                with st.spinner("Uploading..."):
                    result = upload_file(uploaded_file)
                    if result:
                        st.success("✅ File uploaded!")
                        with st.spinner("Processing to Qdrant..."):
                            process_result = process_to_qdrant(result['file_path'], kb_name)
                            if process_result:
                                st.success(f"✅ Processing started! Job ID: {process_result['job_id']}")
                                st.info(f"📚 Knowledge Base: {kb_name}")
                                st.info(f"🗂️ Collection: {process_result['collection_name']}")
                                time.sleep(1)
                                st.rerun()
    
    with tab2:
        st.markdown("### Your Knowledge Bases")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
        kbs = get_knowledge_bases()
        
        if not kbs:
            st.info("No knowledge bases found. Upload files to create your first knowledge base!")
            return
        
        # KB Selection
        selected_kb = st.selectbox(
            "Select Knowledge Base to Manage",
            kbs,
            key="kb_selector"
        )
        
        if selected_kb:
            st.markdown("---")
            
            # Get KB details
            details = get_kb_details(selected_kb)
            files = get_kb_files(selected_kb)
            
            # KB Info
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if details:
                    st.metric("📊 Total Vectors", details.get('vectors_count', 0))
            
            with col2:
                st.metric("📄 Files", len(files) if files else 0)
            
            with col3:
                if st.button("🗑️ Delete Knowledge Base", type="secondary", use_container_width=True):
                    if st.session_state.get(f"confirm_delete_kb_{selected_kb}"):
                        with st.spinner("Deleting knowledge base..."):
                            if delete_knowledge_base(selected_kb):
                                st.success(f"✅ Knowledge base '{selected_kb}' deleted!")
                                if f"confirm_delete_kb_{selected_kb}" in st.session_state:
                                    del st.session_state[f"confirm_delete_kb_{selected_kb}"]
                                time.sleep(1)
                                st.rerun()
                    else:
                        st.session_state[f"confirm_delete_kb_{selected_kb}"] = True
                        st.warning("⚠️ Click again to confirm deletion")
                        st.rerun()
            
            st.markdown("---")
            st.markdown(f"### 📄 Files in '{selected_kb}'")
            
            if files:
                for file_info in files:
                    filename = file_info.get('filename', 'Unknown')
                    chunk_count = file_info.get('chunk_count', 0)
                    file_type = file_info.get('file_type', 'unknown')
                    
                    # File header with expander for details
                    with st.expander(f"📄 {filename}", expanded=False):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Chunks:** {chunk_count}")
                            st.write(f"**Type:** {file_type}")
                        
                        with col2:
                            st.write(f"**Characters:** {file_info.get('total_characters', 'N/A')}")
                            if file_info.get('upload_date'):
                                import datetime
                                upload_time = datetime.datetime.fromtimestamp(file_info['upload_date'])
                                st.write(f"**Uploaded:** {upload_time.strftime('%Y-%m-%d %H:%M')}")
                        
                        st.markdown("---")
                        
                        # Action buttons
                        if st.button("🗑️ Delete from Knowledge Base", key=f"del_{selected_kb}_{filename}", type="secondary", use_container_width=True):
                            with st.spinner(f"Deleting {filename}..."):
                                if delete_kb_file(selected_kb, filename):
                                    st.success("✅ File deleted from knowledge base!")
                                    time.sleep(0.5)
                                    st.rerun()
            else:
                st.info("No files found in this knowledge base")

# --- Knowledge Base Chat Page ---
def show_kb_chat():
    """Display knowledge base chat page."""
    st.title("💬 Knowledge Base Chat")
    
    # KB Selection
    kbs = get_knowledge_bases()
    
    if not kbs:
        st.warning("No knowledge bases available. Upload and process files first!")
        return
    
    selected_kb = st.selectbox(
        "Select Knowledge Base",
        kbs,
        index=kbs.index(st.session_state.current_kb) if st.session_state.current_kb in kbs else 0
    )
    
    if selected_kb != st.session_state.current_kb:
        st.session_state.current_kb = selected_kb
        st.session_state.chat_history = []
    
    st.markdown("---")
    
    # Chat History
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat Input
    if prompt := st.chat_input("Ask a question about your documents..."):
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.write(prompt)
        
        # Get response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Prepare chat history for API
                api_chat_history = []
                for msg in st.session_state.chat_history[:-1]:  # Exclude current message
                    api_chat_history.append(msg["content"])
                
                answer = query_knowledge_base(selected_kb, prompt, api_chat_history)
                
                if answer:
                    st.write(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                else:
                    st.error("Failed to get response")
    
    # Clear Chat
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()

# --- Database Chat Page ---
def show_db_chat():
    """Display database chat page."""
    st.title("🗄️ Database Chat")
    
    st.info("🚧 Database chat functionality coming soon!")
    st.markdown("""
    This feature will allow you to:
    - Connect to your databases
    - Ask questions in natural language
    - Get SQL queries generated automatically
    - View query results
    
    All with tenant isolation and secure credential storage!
    """)

# --- Main Entry Point ---
def main():
    """Main application entry point."""
    init_session_state()
    
    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_main_app()

if __name__ == "__main__":
    main()
