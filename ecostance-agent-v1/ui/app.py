import streamlit as st
import requests
import os
import time
import pandas as pd

# --- Configuration ---
BACKEND_URL = "http://127.0.0.1:9007/api/v1"

# --- Custom CSS for better chat UI ---
def inject_custom_css():
    st.markdown("""
    <style>
    /* Make chat input sticky */
    div[data-testid="stChatInput"] {
        position: -webkit-sticky; /* for Safari */
        position: sticky;
        bottom: 0;
        z-index: 100;
        background-color: #0e1117; /* Match streamlit dark theme */
    }

    /* Style chat input */
    .stChatInput > div {
        border-radius: 25px !important;
        border: 2px solid #4CAF50 !important;
        box-shadow: 0 2px 10px rgba(76, 175, 80, 0.2) !important;
    }
    
    .stChatInput input {
        font-size: 16px !important;
        padding: 12px 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions to Interact with Backend ---

def get_knowledge_bases():
    """Fetches the list of available knowledge bases from the backend."""
    try:
        response = requests.get(f"{BACKEND_URL}/manage/knowledge-bases/")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching knowledge bases: {e}")
        return []

def upload_file(uploaded_file):
    """Uploads a file to the backend and returns its path."""
    files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
    try:
        response = requests.post(f"{BACKEND_URL}/upload/", files=files)
        response.raise_for_status()
        return response.json().get("file_path")
    except requests.exceptions.RequestException as e:
        st.error(f"Error during file upload: {e}")
        return None

def process_file(file_path, collection_name):
    """Triggers the processing pipeline for an already uploaded file."""
    data = {'file_path': file_path, 'collection_name': collection_name}
    try:
        response = requests.post(f"{BACKEND_URL}/upload-to-qdrant/", data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error during file processing: {e}")
        return None

def get_job_status(job_id):
    """Get the status of a background processing job."""
    try:
        response = requests.get(f"{BACKEND_URL}/processing-status/{job_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error getting job status: {e}")
        return None

def query_rag_agent(collection_name, query):
    """Sends a query to the RAG agent and gets an answer."""
    data = {'collection_name': collection_name, 'query': query}
    try:
        response = requests.post(f"{BACKEND_URL}/query/", data=data)
        response.raise_for_status()
        return response.json().get("answer", "No answer found.")
    except requests.exceptions.RequestException as e:
        st.error(f"Error querying the agent: {e}")
        return "Error: Could not get a response from the backend."

def delete_knowledge_base(collection_name):
    """Deletes a knowledge base."""
    try:
        response = requests.delete(f"{BACKEND_URL}/manage/knowledge-bases/{collection_name}")
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Error deleting knowledge base: {e}")
        return False

def get_knowledge_base_details(collection_name):
    """Gets detailed information about a knowledge base including files."""
    try:
        response = requests.get(f"{BACKEND_URL}/manage/knowledge-bases/{collection_name}/details")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching knowledge base details: {e}")
        return None

def delete_file_from_kb(collection_name, filename):
    """Deletes a specific file from a knowledge base."""
    try:
        response = requests.delete(f"{BACKEND_URL}/manage/knowledge-bases/{collection_name}/files/{filename}")
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Error deleting file: {e}")
        return False

def reindex_file_in_kb(collection_name, filename):
    """Reindexes a specific file in a knowledge base."""
    try:
        response = requests.post(f"{BACKEND_URL}/manage/knowledge-bases/{collection_name}/files/{filename}/reindex")
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Error reindexing file: {e}")
        return False

# --- Database Interaction Functions ---
def db_connect(db_uri):
    try:
        response = requests.post(f"{BACKEND_URL}/db/connect", json={"db_uri": db_uri})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def db_generate_query(question):
    try:
        response = requests.post(f"{BACKEND_URL}/db/generate-query", json={"question": question})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def db_execute_query(query):
    try:
        response = requests.post(f"{BACKEND_URL}/db/execute-query", json={"query": query})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def db_save_connection(name, db_type, host, port, username, password, database, db_path):
    try:
        response = requests.post(f"{BACKEND_URL}/db/connections/save", json={
            "name": name,
            "db_type": db_type,
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "database": database,
            "db_path": db_path
        })
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def db_list_connections():
    try:
        response = requests.get(f"{BACKEND_URL}/db/connections/list")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return []

def db_load_connection(name):
    try:
        response = requests.get(f"{BACKEND_URL}/db/connections/{name}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def db_delete_connection(name):
    try:
        response = requests.delete(f"{BACKEND_URL}/db/connections/{name}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


# --- Streamlit UI ---

st.set_page_config(page_title="EcoStance RAG Agent", layout="wide")

# Inject custom CSS for sticky chat input
inject_custom_css()

st.title("EcoStance RAG Agent 🤖")
st.write("Upload documents, manage your knowledge bases, and ask questions.")

# --- Sidebar for Management ---
with st.sidebar:
    st.header("Configuration")
    
    # Get the list of knowledge bases
    knowledge_bases = get_knowledge_bases()
    
    st.subheader("Select Knowledge Base")
    if 'selected_kb' not in st.session_state or st.session_state.selected_kb not in knowledge_bases:
        st.session_state.selected_kb = knowledge_bases[0] if knowledge_bases else None

    selected_kb = st.selectbox(
        "Choose a knowledge base to chat with:",
        options=knowledge_bases,
        key='selected_kb'
    )
    
    st.divider()

    st.subheader("Manage Knowledge Bases")
    if selected_kb and st.button(f"Delete '{selected_kb}'"):
        with st.spinner(f"Deleting {selected_kb}..."):
            if delete_knowledge_base(selected_kb):
                st.success(f"Knowledge base '{selected_kb}' deleted.")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Deletion failed.")

    st.divider()

    st.subheader("Add New Document")
    new_kb_name = st.text_input("Enter new knowledge base name (or select existing):", value=selected_kb or "")
    uploaded_file = st.file_uploader(
        "Upload a document",
        type=['pdf', 'docx', 'txt', 'md', 'xlsx', 'xls', 'csv', 'html', 'htm', 'sql', 'jsonl'],
        help="Supported formats: PDF, Word, Text, Markdown, Excel, CSV, HTML, SQL, JSONL"
    )

    if st.button("Upload and Process"):
        if uploaded_file and new_kb_name:
            with st.spinner(f"Step 1/2: Uploading '{uploaded_file.name}'..."):
                file_path = upload_file(uploaded_file)

            if file_path:
                st.success(f"File uploaded successfully. Path: {file_path}")
                result = process_file(file_path, new_kb_name)

                if result and 'job_id' in result:
                    job_id = result['job_id']
                    st.success(f"Processing started! Job ID: {job_id}")

                    if 'processing_jobs' not in st.session_state:
                        st.session_state.processing_jobs = []
                    st.session_state.processing_jobs.append({
                        'job_id': job_id,
                        'filename': uploaded_file.name,
                        'kb_name': new_kb_name,
                        'started_at': time.time()
                    })

                    st.info("You can monitor the processing status in the 'Processing Jobs' section below.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to start processing job.")
        else:
            st.warning("Please provide both a file and a knowledge base name.")

    # Processing Jobs Status Section
    if 'processing_jobs' in st.session_state and st.session_state.processing_jobs:
        st.divider()
        st.subheader("📊 Processing Jobs")
        
        jobs_to_remove = []
        for i, job in enumerate(st.session_state.processing_jobs):
            job_status = get_job_status(job['job_id'])

            if job_status:
                status = job_status.get('status', 'unknown')
                progress_msg = job_status.get('progress_message', 'No progress info')

                if status == 'completed':
                    status_icon = "✅"
                elif status == 'failed':
                    status_icon = "❌"
                elif status == 'processing':
                    status_icon = "🔄"
                else:
                    status_icon = "⏳"

                with st.expander(f"{status_icon} {job['filename']} → {job['kb_name']} ({status})"):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.write(f"**Status:** {status}")
                        st.write(f"**Progress:** {progress_msg}")
                        if job_status.get('error_message'):
                            st.error(f"Error: {job_status['error_message']}")

                    with col2:
                        if status in ['completed', 'failed']:
                            if st.button(f"Remove", key=f"remove_job_{i}"):
                                jobs_to_remove.append(i)

                if status in ['completed', 'failed']:
                    elapsed = time.time() - job['started_at']
                    if elapsed > 300:
                        jobs_to_remove.append(i)

        for i in reversed(jobs_to_remove):
            st.session_state.processing_jobs.pop(i)

        active_jobs = [j for j in st.session_state.processing_jobs
                      if get_job_status(j['job_id']) and
                      get_job_status(j['job_id']).get('status') in ['pending', 'processing']]

        if active_jobs:
            time.sleep(2)
            st.rerun()


# --- Main Interface with Tabs ---
tab1, tab2, tab3 = st.tabs(["💬 Chat with Docs", "📁 Manage Files", "🗃️ Chat with Database"])

with tab1:
    st.header(f"Chat with: {selected_kb}" if selected_kb else "Chat")

    if selected_kb:
        if "messages" not in st.session_state or st.session_state.get("current_kb") != selected_kb:
            st.session_state.messages = []
            st.session_state.current_kb = selected_kb

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Ask a question about the documents..."):
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.spinner("Thinking..."):
                response = query_rag_agent(selected_kb, prompt)

            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
    else:
        st.info("Please create or select a knowledge base from the sidebar to begin.")

with tab2:
    st.header("📁 Knowledge Base File Management")

    if selected_kb:
        st.subheader(f"Files in '{selected_kb}'")

        with st.spinner("Loading knowledge base details..."):
            kb_details = get_knowledge_base_details(selected_kb)

        if kb_details and not kb_details.get('error'):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Points", kb_details.get('total_points', 0))
            with col2:
                st.metric("Files Count", kb_details.get('files_count', 0))
            with col3:
                st.metric("Vector Size", kb_details.get('vector_size', 0))
            with col4:
                total_chunks = sum(f.get('chunk_count', 0) for f in kb_details.get('files', []))
                st.metric("Total Chunks", total_chunks)

            st.divider()

            files = kb_details.get('files', [])
            if files:
                st.subheader("📄 Indexed Files")

                for i, file_info in enumerate(files):
                    with st.expander(f"📄 {file_info.get('filename', 'Unknown')} ({file_info.get('chunk_count', 0)} chunks)"):
                        col1, col2 = st.columns([2, 1])

                        with col1:
                            st.write(f"**File Type:** {file_info.get('file_type', 'Unknown')}")
                            st.write(f"**Upload Date:** {file_info.get('upload_date', 'Unknown')}")
                            st.write(f"**File Size:** {file_info.get('file_size', 'Unknown')}")
                            st.write(f"**Total Characters:** {file_info.get('total_characters', 0):,}")
                            st.write(f"**Chunks:** {file_info.get('chunk_count', 0)}")

                        with col2:
                            filename = file_info.get('filename')

                            if st.button(f"🔄 Reindex", key=f"reindex_{i}"):
                                with st.spinner(f"Reindexing {filename}..."):
                                    if reindex_file_in_kb(selected_kb, filename):
                                        st.success(f"Successfully reindexed {filename}")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error("Reindexing failed")

                            if st.button(f"🗑️ Delete", key=f"delete_{i}", type="secondary"):
                                if st.session_state.get(f"confirm_delete_{i}"):
                                    with st.spinner(f"Deleting {filename}..."):
                                        if delete_file_from_kb(selected_kb, filename):
                                            st.success(f"Successfully deleted {filename}")
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error("Deletion failed")
                                else:
                                    st.session_state[f"confirm_delete_{i}"] = True
                                    st.warning("Click delete again to confirm")

            else:
                st.info("No files found in this knowledge base.")

        elif kb_details and kb_details.get('error'):
            st.error(f"Error loading knowledge base: {kb_details.get('error')}")
        else:
            st.error("Failed to load knowledge base details.")

    else:
        st.info("Please select a knowledge base from the sidebar to manage its files.")

with tab3:
    st.header("🗃️ Chat with Your Database")

    if 'db_connected' not in st.session_state:
        st.session_state.db_connected = False
    if 'db_messages' not in st.session_state:
        st.session_state.db_messages = []

    if not st.session_state.db_connected:
        st.subheader("Connect to Database")

        # Saved connections section
        saved_connections = db_list_connections()
        
        if saved_connections:
            st.markdown("**📌 Saved Connections**")
            col1, col2 = st.columns([3, 1])
            
            with col1:
                selected_connection = st.selectbox(
                    "Load a saved connection",
                    options=["-- New Connection --"] + [conn['name'] for conn in saved_connections],
                    key="saved_connection_selector"
                )
            
            with col2:
                if selected_connection != "-- New Connection --":
                    if st.button("🗑️ Delete", key="delete_saved_conn"):
                        result = db_delete_connection(selected_connection)
                        if "error" not in result:
                            st.success(f"Deleted '{selected_connection}'")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Failed to delete: {result['error']}")
            
            # Load connection if selected
            if selected_connection != "-- New Connection --":
                conn_data = db_load_connection(selected_connection)
                if "error" not in conn_data:
                    st.session_state.loaded_connection = conn_data
                    st.info(f"✅ Loaded: {conn_data.get('type', 'Unknown')} - {conn_data.get('database', 'N/A')}")
            else:
                st.session_state.loaded_connection = None
            
            st.divider()

        # Database type selection OUTSIDE the form so it updates immediately
        if 'loaded_connection' in st.session_state and st.session_state.loaded_connection:
            db_type = st.session_state.loaded_connection.get('type', 'SQLite')
        else:
            db_type = st.selectbox("Database Type", ["SQLite", "PostgreSQL", "MySQL"])

        # Now create the form with the appropriate fields
        with st.form("db_connection_form"):
            # Pre-fill with loaded connection data if available
            loaded = st.session_state.get('loaded_connection', {})
            
            if db_type == "SQLite":
                db_path = st.text_input("Database File Path", loaded.get('db_path', 'sqlite.db'))
                host = username = password = dbname = port = None
            else:
                db_path = None
                col1, col2 = st.columns(2)
                with col1:
                    host = st.text_input("Host", loaded.get('host', 'localhost'))
                    username = st.text_input("Username", loaded.get('username', 'postgres' if db_type == "PostgreSQL" else "root"))
                    dbname = st.text_input("Database Name", loaded.get('database', 'mydatabase'))
                with col2:
                    port = st.text_input("Port", loaded.get('port', '5432' if db_type == "PostgreSQL" else '3306'))
                    password = st.text_input("Password", loaded.get('password', ''), type="password")
            
            # Option to save connection
            st.divider()
            save_connection = st.checkbox("💾 Save this connection", value=False)
            connection_name = ""
            if save_connection:
                connection_name = st.text_input("Connection Name", placeholder="e.g., Production DB, Local Dev")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submitted = st.form_submit_button("Connect", type="primary", use_container_width=True)
            with col_btn2:
                clear_btn = st.form_submit_button("Clear", use_container_width=True)

            if clear_btn:
                st.session_state.loaded_connection = None
                st.rerun()
            
            if submitted:
                db_uri = None
                if db_type == "SQLite":
                    if not db_path:
                        st.error("Please provide a database file path")
                    else:
                        db_uri = f"sqlite:///{db_path}"
                else:
                    if not all([host, username, password, dbname, port]):
                        st.error("Please fill in all connection fields")
                    else:
                        driver = "postgresql" if db_type == "PostgreSQL" else "mysql+pymysql"
                        db_uri = f"{driver}://{username}:{password}@{host}:{port}/{dbname}"

                if db_uri:
                    with st.spinner("Connecting to database..."):
                        result = db_connect(db_uri)
                        if "error" in result:
                            st.error(f"Connection failed: {result['error']}")
                        else:
                            # Save connection if requested
                            if save_connection and connection_name:
                                save_result = db_save_connection(
                                    name=connection_name,
                                    db_type=db_type,
                                    host=host,
                                    port=port,
                                    username=username,
                                    password=password,
                                    database=dbname,
                                    db_path=db_path
                                )
                                if "error" not in save_result:
                                    st.success(f"✅ Connection saved as '{connection_name}'")
                            
                            st.session_state.db_connected = True
                            st.session_state.db_type = db_type
                            st.session_state.db_messages = []
                            st.success(result['message'])
                            time.sleep(1)
                            st.rerun()

    if st.session_state.db_connected:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"✅ Connected to {st.session_state.get('db_type', 'database')}")
        with col2:
            if st.button("Disconnect", type="secondary"):
                st.session_state.db_connected = False
                st.session_state.db_messages = []
                for key in ['sql_query', 'explanation', 'safety_check', 'db_type']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

        st.divider()

        for message in st.session_state.db_messages:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.markdown(message["content"])
                else:
                    if "sql" in message:
                        st.markdown("**Generated SQL:**")
                        st.code(message["sql"], language="sql")
                        
                        if "explanation" in message:
                            st.info(f"💡 {message['explanation']}")
                    
                    if "results" in message:
                        if isinstance(message["results"], list) and len(message["results"]) > 0:
                            df = pd.DataFrame(message["results"])
                            st.dataframe(df, use_container_width=True)
                            st.caption(f"📊 {len(message['results'])} rows returned")
                        elif isinstance(message["results"], dict) and "message" in message["results"]:
                            st.success(message["results"]["message"])
                        else:
                            st.info("Query executed successfully (no results to display)")
                    
                    if "error" in message:
                        st.error(f"❌ {message['error']}")

        if prompt := st.chat_input("Ask a question about your database..."):
            st.session_state.db_messages.append({"role": "user", "content": prompt})
            
            with st.spinner("Generating SQL query..."):
                query_result = db_generate_query(prompt)
            
            assistant_message = {"role": "assistant"}
            
            if "error" in query_result:
                assistant_message["error"] = f"Failed to generate query: {query_result['error']}"
            else:
                sql_query = query_result.get("sql_query")
                explanation = query_result.get("explanation")
                safety_check = query_result.get("safety_check")
                
                assistant_message["sql"] = sql_query
                assistant_message["explanation"] = explanation
                
                if safety_check == "SAFE":
                    with st.spinner("Executing query..."):
                        exec_result = db_execute_query(sql_query)
                    
                    if isinstance(exec_result, dict) and "error" in exec_result:
                        assistant_message["error"] = exec_result["error"]
                    else:
                        assistant_message["results"] = exec_result
                else:
                    assistant_message["error"] = "Query failed safety check. Only SELECT queries are allowed."
            
            st.session_state.db_messages.append(assistant_message)
            st.rerun()
    else:
        st.info("👆 Please connect to a database to start chatting with it.")
