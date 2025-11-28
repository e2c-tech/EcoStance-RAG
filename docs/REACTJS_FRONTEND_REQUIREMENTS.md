# ReactJS Frontend Requirements - Multitenant RAG System

## Overview

This document outlines comprehensive requirements for building a ReactJS frontend for the multitenant RAG (Retrieval-Augmented Generation) system. The frontend should provide a modern, responsive, and intuitive interface for managing knowledge bases, querying documents, interacting with databases, and administering tenants.

---

## Core Features & Pages

### 1. Authentication & Session Management

**Login Page**
- Email/tenant ID input field
- Password input field with show/hide toggle
- "Remember me" checkbox
- Login button with loading state
- "Forgot password" link
- Error message display for failed authentication
- Redirect to dashboard on successful login

**Session Management**
- Store JWT access token in memory (not localStorage for security)
- Store refresh token in httpOnly cookie
- Automatic token refresh before expiration (30 min access token)
- Session timeout warning (5 min before expiry)
- Auto-logout on token expiration
- Persist tenant context across page navigation
- Clear all session data on logout

**Registration Page** (if self-service enabled)
- Tenant name input
- Email input with validation
- Phone number input (optional)
- Billing tier selection (free/starter/professional/enterprise)
- Terms of service checkbox
- Submit button with loading state
- Success message with tenant ID display

---

### 2. Main Dashboard (Home)

**Overview Cards**
- Total knowledge bases count
- Total documents uploaded
- Storage usage (GB used / GB limit) with progress bar
- Query count this month
- Active database connections count

**Quick Actions**
- Upload new document button
- Create knowledge base button
- Connect to database button
- Ask a question (quick search)

**Recent Activity Feed**
- Last 10 queries with timestamps
- Recent file uploads
- Recent database queries
- Processing job status updates

**Usage Charts**
- Storage usage trend (line chart, last 30 days)
- Query volume (bar chart, last 7 days)
- API calls per day (line chart)

---

### 3. Knowledge Base Management

#### **Knowledge Base List Page**

**Layout & Controls:**
- Provide a toggle button in the top-right corner to switch between grid and list views
- Include a search bar that filters knowledge bases in real-time as users type
- Add a sort dropdown with options: Name (A-Z), Date Created (newest/oldest), Document Count (high/low), Size (largest/smallest)
- Place a prominent "Create New KB" button in the top-right as the primary action
- Display an empty state message with a call-to-action button when no knowledge bases exist

**Grid View (Default):**
- Design a responsive grid layout: 3 columns on desktop, 2 on tablet, 1 on mobile
- Each knowledge base card should display:
  - A folder icon or thumbnail at the top
  - The KB name (truncate long names with ellipsis and show full name on hover)
  - Number of documents with an icon
  - Total vectors count (format with commas for readability)
  - Last updated timestamp in relative format (e.g., "2 hours ago")
  - Storage size in MB or GB
  - Three quick action buttons at the bottom:
    - View Details (eye icon) - navigates to the details page
    - Query (chat icon) - opens chat interface with this KB pre-selected
    - Delete (trash icon) - shows confirmation modal before deletion
  - Add hover effects with shadow elevation to indicate interactivity
  - Show a status indicator badge (processing/ready/error) in the corner

**List View:**
- Present knowledge bases in a sortable data table with columns:
  - Name (with folder icon)
  - Documents (count)
  - Vectors (count)
  - Size (MB/GB)
  - Last Updated (formatted date/time)
  - Status (colored badge)
  - Actions (dropdown menu)
- Enable row selection with checkboxes for bulk operations
- Implement pagination with options for 10, 25, 50, or 100 items per page
- Provide an "Export to CSV" option for the current view

**Additional Features:**
- Show loading skeletons while fetching data from the API
- Display error states with a retry button if the API call fails
- Include a refresh button to manually reload the knowledge base list
- Add a filter dropdown to show: All, Ready, Processing, or Error status
- Enable bulk delete for selected KBs with a confirmation dialog

---

#### **Create Knowledge Base Modal**

**Modal Design:**
- Display a centered modal with a semi-transparent backdrop overlay
- Show "Create New Knowledge Base" as the modal title
- Include a close button (X icon) in the top-right corner

**Form Fields:**
- Knowledge Base Name (required):
  - Text input field
  - Placeholder: "e.g., product-documentation"
  - Validation: Must be unique, 3-50 characters, alphanumeric with hyphens and underscores only
  - Help text below: "Use lowercase letters, numbers, hyphens, and underscores"
  - Show validation errors inline below the field
  
- Description (optional):
  - Textarea with 4 rows
  - Placeholder: "Brief description of this knowledge base..."
  - Character limit: 500 characters
  - Show character counter below

**Validation & Behavior:**
- Validate the KB name on blur (when user leaves the field)
- Make an API call to check if the name is already taken
- Display inline error messages in red below the field
- Disable the submit button until all validations pass
- Show a loading spinner on the submit button during API call

**Actions:**
- Cancel button (secondary style) - closes modal without saving
- Create Knowledge Base button (primary style) - disabled until form is valid
- On successful creation, show a success message and redirect to the new KB details page
- On error, display user-friendly error messages without closing the modal

---

#### **Knowledge Base Details Page**

**Page Header:**
- Display breadcrumb navigation: Home > Knowledge Bases > {KB Name}
- Show the KB name as the main page title (make it editable on click)
- Display a status badge next to the title (Ready/Processing/Error)
- Show the last updated timestamp below the title

**Metrics Section:**
- Display four metric cards in a horizontal row:
  - Total Vectors: Show the count formatted with commas, include a number icon
  - Documents: Show document count with a delta indicator (e.g., "+3 today")
  - Vector Size: Display the embedding dimension (e.g., "1536")
  - Total Chunks: Show the sum of all chunks across documents
- Use card components with icons and optional trend indicators

**Action Bar:**
- Upload Document button (primary style, prominent)
- Query This KB button (secondary style)
- Refresh button (icon only, circular)
- Settings dropdown menu with options:
  - Rename KB
  - Export metadata
  - View API usage statistics
  - Delete KB (shown in red as a danger action)
- Search input field: "Search documents in this KB..." with real-time filtering

**Documents Section:**

**Table Layout:**
- Create a sortable table with these columns:
  - Filename (with file type icon, left-aligned)
  - File Type (colored badge: PDF=red, DOCX=blue, TXT=gray, etc.)
  - Upload Date (formatted as "Jan 15, 2024 3:45 PM")
  - Chunks (numeric count)
  - File Size (formatted as KB/MB)
  - Characters (formatted with commas)
  - Status (badge: Processing/Indexed/Failed with appropriate colors)
  - Actions (dropdown menu icon)

**Document Actions:**
- Each row should have a dropdown menu with these options:
  - Download original file
  - Reindex (re-process the document)
  - View chunks (opens modal showing all text chunks)
  - Delete from KB (shows confirmation dialog)

**Expandable Row Details:**
- Allow users to click a row to expand and show additional information:
  - Full file path
  - Processing date and time
  - Chunk size configuration used
  - Embedding model used
  - Processing duration
  - Error logs (if processing failed)
  - Preview of the first chunk of text

**Pagination:**
- Provide a dropdown to select items per page: 10, 25, 50, 100
- Show page numbers with previous/next buttons
- Display text like "Showing 1-10 of 42 documents"
- Include a "Jump to page" input for quick navigation

**Empty State:**
- When no documents exist, show:
  - An illustration or icon
  - Message: "No documents yet"
  - Subtext: "Upload your first document to get started"
  - Upload Document button

**Bulk Actions:**
- Add checkboxes to select individual documents or all at once
- When documents are selected, show a bulk actions bar with:
  - Reindex selected documents
  - Delete selected documents (with confirmation)
  - Export metadata for selected documents

---

#### **Document Upload Interface**

**Upload Modal/Page Structure:**

**Step 1: Select Knowledge Base**
- Show a dropdown selector with options:
  - "Create New Knowledge Base" as the first option
  - List all existing knowledge bases below
- If "Create New" is selected, display an inline text input for the new KB name
- Validate the new KB name in real-time
- Show help text about naming conventions

**Step 2: Upload Files**

**Drag-and-Drop Zone:**
- Create a large rectangular area with a dashed border
- Display a cloud upload icon or document icon in the center
- Show text: "Drag and drop files here"
- Include a clickable link: "or click to browse"
- List supported file formats below the zone
- Enable multiple file selection
- Highlight the zone when files are dragged over it

**File Browser:**
- Clicking the zone or browse link opens the native file picker
- Enable multiple file selection in the picker
- Apply file type filters to show only supported formats

**Supported Formats Display:**
- Show an expandable section or always-visible list:
  - Documents: PDF, DOCX, TXT, MD
  - Spreadsheets: XLSX, XLS, CSV
  - Web & Data: HTML, HTM, SQL, JSONL
- Use icons to represent each category

**File List (After Selection):**
- Display each selected file in a list with:
  - File type icon
  - Filename (truncate if too long)
  - File size (formatted)
  - Remove button (X icon) to deselect
  - Status indicator: Pending/Uploading/Processing/Complete/Failed
  - Progress bar showing upload and processing progress

**Storage Quota Indicator:**
- Display a progress bar showing storage usage
- Show text: "X.XX GB / Y.YY GB used (ZZ%)"
- Color-code the progress bar:
  - Green if under 75%
  - Yellow/orange if 75-90%
  - Red if over 90%
- Show warning message if quota exceeds 90%: "Storage almost full! Consider upgrading."
- Prevent upload if it would exceed the quota limit

**Upload Progress:**
- Show individual progress bars for each file
- Display overall progress: "Uploading 3 of 5 files..."
- Show upload speed (MB/s) and time remaining estimate
- Provide pause/resume buttons if the upload library supports it
- Include a cancel button to abort all uploads

**Processing Status:**
- After upload completes, show processing status for each file
- Update status in real-time using polling (every 3-5 seconds) or WebSocket
- Display status messages:
  - "Extracting text..."
  - "Generating embeddings..."
  - "Indexing vectors..."
  - "Complete!"
- Provide a link to view all processing jobs in the monitor

**Action Buttons:**
- Cancel button (closes modal and cancels any pending uploads)
- Upload & Process button (primary style, disabled until files are selected)
- After completion, show:
  - Upload More button (to add more files)
  - View in KB button (navigates to the KB details page)

**Validation & Error Handling:**
- Validate file size before upload (show maximum allowed size)
- Validate file type and reject unsupported formats with an error message
- Detect duplicate files and warn the user
- Handle network errors with automatic retry or manual retry button
- Display per-file error messages if processing fails
- Show success/error toast notifications for each file

---

#### **Processing Jobs Monitor**

**Location & Layout:**
- Display in a sidebar panel or as a dedicated section on the page
- Make it accessible from any page (e.g., via a notification icon in the header)

**Job List Display:**
- Show each processing job as a card or list item with:
  - Status icon: ⏳ Pending, 🔄 Processing (animated), ✅ Complete, ❌ Failed
  - Filename being processed
  - Knowledge base name (as a clickable link)
  - Current progress message
  - Timestamp (when started or completed)
  - Action buttons: View details, Retry (if failed), Remove

**Job Details (Expandable):**
- Allow users to expand each job to see:
  - Unique job ID
  - Full file path
  - Processing stages with visual indicators:
    - File uploaded (checkmark)
    - Text extracted (checkmark)
    - Generating embeddings (in progress with percentage)
    - Indexing vectors (pending)
  - Error message and stack trace (if failed)
  - Total processing duration
  - Retry button for failed jobs

**Auto-Refresh Behavior:**
- Automatically poll the API every 3-5 seconds for jobs that are pending or processing
- Stop polling when all jobs are completed or failed
- Show a subtle "Refreshing..." indicator during updates
- Use optimistic UI updates for better perceived performance

**Filters:**
- Provide filter tabs or dropdown:
  - All Jobs
  - Active (Pending/Processing)
  - Completed
  - Failed
- Update the count badge on each filter

**Bulk Actions:**
- Clear all completed jobs (removes them from the list)
- Retry all failed jobs (resubmits them for processing)
- Cancel all pending jobs (stops them before processing starts)

---

#### **Query Knowledge Base (Chat Interface)**

**Overall Layout:**
- Design a full-height chat interface similar to modern chat applications
- Include a collapsible sidebar on the left for KB selection and settings
- Main chat area in the center showing conversation history
- Sticky input area at the bottom for typing questions

**KB Selector (Sidebar):**
- Display a searchable dropdown to select the knowledge base
- Show KB metadata below the selector:
  - Number of documents
  - Last updated timestamp
  - Total vectors
- When switching KBs, show a confirmation dialog: "Clear current chat history?"
- Highlight the currently selected KB

**Chat History Display:**
- Create a scrollable message list that auto-scrolls to the bottom on new messages
- Alternate message alignment: user messages on the right, assistant messages on the left
- Use distinct styling for user vs. assistant messages

**User Message Bubble:**
- Display user avatar or icon on the right
- Show the message text in a bubble with rounded corners
- Include a timestamp below the message
- Optionally add edit and delete buttons on hover

**Assistant Message Bubble:**
- Display AI avatar or icon on the left
- Show the answer text with markdown formatting support (bold, italic, lists, code blocks)
- Include an expandable "Sources" section showing:
  - Number of source documents used
  - Each source with: filename, page number (if applicable), chunk number
  - Click to expand and preview the source text
- Display a confidence score badge if available (High/Medium/Low with color coding)
- Add feedback buttons (thumbs up/down) for user ratings
- Include a copy button to copy the answer to clipboard
- Show timestamp below the message

**Source Document Preview:**
- When a user clicks a source, expand it inline to show:
  - The relevant chunk of text
  - Highlighted keywords or phrases
  - Link to view the full document
  - Relevance score or similarity percentage

**Question Input Area:**
- Use a textarea that auto-resizes from 1 to 5 rows as the user types
- Show placeholder text: "Ask a question about {KB name}..."
- Include a character counter if there's a limit
- Add a send button with an icon (arrow or paper plane)
- Disable the input and button while waiting for a response
- Show a loading indicator (typing animation or spinner) during processing

**Chat Actions (Top Bar):**
- New conversation button (clears history with confirmation)
- Save conversation button (saves to backend for later retrieval)
- Export conversation button with format options:
  - Plain text (.txt)
  - JSON (.json)
  - PDF (.pdf)
- Settings dropdown with options:
  - Temperature slider (0.0 to 1.0) for response creativity
  - Max tokens slider for response length
  - Number of source documents to retrieve (1-10)
  - Toggle for streaming responses (typewriter effect)

**Advanced Features:**
- Implement streaming responses that appear word-by-word (typewriter effect)
- Render markdown in responses (headings, lists, code blocks with syntax highlighting)
- Add copy buttons to code blocks
- Save conversations to the backend and allow users to load previous conversations
- Support keyboard shortcuts: Enter to send, Shift+Enter for new line

**Empty State:**
- When no messages exist, show:
  - Welcome message: "Ask me anything about {KB name}"
  - Suggested questions based on KB content (3-5 examples)
  - Quick start guide or tips

**Error Handling:**
- Network errors: Show error message with a retry button
- Rate limit errors: Display warning about quota limits
- No results found: Show message suggesting to rephrase or check KB content
- Timeout errors: Allow user to retry or cancel the request

---

### 4. File Management

#### **File Browser Page**

**Page Header:**
- Display "File Management" as the page title
- Show a prominent storage usage card at the top:
  - Progress bar showing storage used vs. total limit
  - Text: "X.XX GB / Y.YY GB used (ZZ%)"
  - Additional info: "N files • X.XX GB remaining"
  - Color-code based on usage: green (<75%), yellow (75-90%), red (>90%)
- Include an "Upload Files" button as the primary action

**Filters & Search Bar:**
- Create a comprehensive filter bar with these components:
  - Search input: "Search files by name..." with debounced search (300ms delay)
  - File Type dropdown filter:
    - All Types
    - PDF
    - Word Documents
    - Text Files
    - Spreadsheets
    - HTML
    - Other
  - Date Range picker for filtering by upload date
  - Status dropdown filter:
    - All Status
    - Uploaded
    - Processing
    - Indexed
    - Failed
  - Sort dropdown with options:
    - Name (A-Z)
    - Name (Z-A)
    - Size (Largest first)
    - Size (Smallest first)
    - Date (Newest first)
    - Date (Oldest first)
  - Clear Filters button to reset all filters

**File Table:**

**Table Columns:**
1. Checkbox column for selecting files for bulk actions
2. Filename with file type icon (PDF, Word, Excel, etc.), truncate long names with tooltip on hover
3. File Type displayed as a colored badge (PDF=red, DOCX=blue, TXT=gray, XLSX=green, etc.)
4. Size formatted appropriately (KB, MB, or GB)
5. Upload Date formatted as readable date/time with relative time on hover (e.g., "2 hours ago")
6. Status shown as a badge with icon:
   - Indexed (green with checkmark)
   - Processing (blue with spinner animation)
   - Uploaded (gray with clock)
   - Failed (red with X)
7. Used In showing the number of knowledge bases using this file (clickable to show list)
8. Actions column with a dropdown menu icon

**Table Features:**
- Add hover effect that changes background color on row hover
- Make rows clickable to expand and show additional details
- Enable column sorting by clicking column headers
- Allow column resizing by dragging column borders
- Implement smooth animations for row expansion

**Expanded Row Details:**
- When a row is expanded, show:
  - Full file path
  - MD5 hash or unique file ID (with copy button)
  - Full upload timestamp
  - Processing completion timestamp
  - File metadata (number of pages, word count, etc.)
  - List of knowledge bases using this file (with links to each KB)
  - Processing logs or error messages
  - Preview button if the file type supports preview

**Bulk Actions Bar:**
- Display when one or more files are selected
- Show selection count: "3 files selected"
- Provide these bulk action buttons:
  - Download selected files (as a ZIP archive)
  - Delete selected files (with confirmation dialog)
  - Reprocess selected files
  - Add to Knowledge Base (opens dropdown to select KB)
  - Export metadata (as CSV file)
- Include "Select All" and "Deselect All" links

**Pagination:**
- Provide items per page selector: 10, 25, 50, 100
- Show page numbers with ellipsis for many pages (e.g., 1 2 3 ... 10)
- Include Previous and Next navigation buttons
- Add a "Jump to page" input field for quick navigation
- Display total count: "Showing 1-25 of 342 files"

**Empty State:**
- When no files exist, display:
  - An illustration or icon
  - Message: "No files uploaded yet"
  - Subtext: "Upload your first file to get started"
  - Upload Files button

**Loading State:**
- Show skeleton rows with shimmer effect while loading data
- Display loading spinner for long operations

---

#### **File Actions (Dropdown Menu)**

**Per-File Action Menu:**
Each file row should have a dropdown menu with these options:

1. **Download** - Download the original file to the user's device
2. **View Details** - Open a modal or side panel with comprehensive file information
3. **View Metadata** - Display file properties and technical details
4. **Reprocess** - Re-extract text and re-index the file in all associated KBs
5. **Add to KB** - Open a modal to select which knowledge base to add the file to
6. **Copy Path** - Copy the file path to clipboard with visual confirmation
7. **Delete** - Delete the file with a confirmation dialog (shown in red as danger action)

---

#### **View Details Modal**

**Modal Structure:**
- Display the filename as the modal title
- Create a tabbed interface with four tabs:

**Tab 1: Overview**
- Show a metadata list with these items:
  - File Name (full name)
  - File Type (with icon)
  - Size (formatted)
  - Upload Date (full timestamp)
  - Uploaded By (username or tenant)
  - Status (with colored badge)
  - MD5 Hash (with copy button)
  - File Path (with copy button)
- Make copyable fields have a copy icon that shows "Copied!" on click

**Tab 2: Processing**
- Display a visual timeline showing processing stages:
  - Uploaded (with checkmark and timestamp)
  - Text Extracted (with checkmark and timestamp)
  - Generating Embeddings (with progress percentage if in progress)
  - Indexing (with status indicator)
- Show error messages in a red alert box if processing failed
- Include a "Reprocess File" button to retry processing

**Tab 3: Usage**
- Show text: "This file is used in N knowledge base(s):"
- List each knowledge base with:
  - KB name (as a clickable link to the KB details page)
  - Number of chunks from this file
  - Remove button to remove the file from that specific KB
- If not used in any KB, show: "This file is not currently used in any knowledge base"

**Tab 4: Preview**
- If the file type supports preview (PDF, images, text), show an embedded preview
- For unsupported types, display: "Preview not available for this file type"
- Add zoom controls for images and PDFs
- Include a "Download" button to get the full file

**Modal Actions:**
- Close button (secondary style) to dismiss the modal
- Download button (primary style) to download the file

---

#### **Delete Confirmation Modal**

**Modal Design:**
- Title: "Delete File?"
- Message: "Are you sure you want to delete '[filename]'?"
- If the file is used in knowledge bases, show a warning:
  - "This file is used in N knowledge base(s). Deleting it will remove it from all KBs."
  - List the affected knowledge bases
- Confirm button labeled "Delete" in red/danger style
- Cancel button in secondary style
- On confirmation, delete the file and show a success toast notification

---

#### **Reprocess File Action**

**Confirmation Dialog:**
- Show a confirmation message: "This will re-extract and re-index the file. Continue?"
- Explain that this may take a few minutes depending on file size
- Confirm and Cancel buttons

**Processing Behavior:**
- Start a new processing job when confirmed
- Add the job to the processing jobs monitor
- Show progress updates in real-time
- Update the file status in the table automatically
- Display a success notification when complete

---

#### **Add to KB Modal**

**Modal Structure:**
- Title: "Add to Knowledge Base"
- Searchable dropdown to select a knowledge base from the list
- Checkbox option: "Reprocess file for this KB" (checked by default)
- Help text explaining that reprocessing ensures optimal indexing for the selected KB

**Actions:**
- Cancel button (secondary style) to close without action
- Add to KB button (primary style, disabled until a KB is selected)
- On success, show a toast notification and optionally navigate to the KB details page

---

#### **File Upload (Standalone)**

**Upload Interface:**
- Provide the same upload interface as in KB management
- Key difference: files are uploaded to general storage without being assigned to a specific KB
- Users can add files to knowledge bases later from the file browser

**Upload Features:**
- Large drag-and-drop zone with dashed border
- Click to browse and select multiple files
- Show supported file formats
- Display selected files in a list with remove option
- Show individual progress bars for each file during upload
- Display storage quota indicator with warning if near limit
- Validate file size and type before upload
- Show success/error notifications for each file
- After upload, provide options to:
  - Upload more files
  - View uploaded files in the file browser
  - Add files to a knowledge base

**Post-Upload Behavior:**
- Automatically redirect to the file browser after successful upload
- Highlight newly uploaded files
- Show a success message with file count

---

### 5. Database Chat Interface

**Database Connection Manager**
- List of saved connections (cards or table)
- Each connection shows:
  - Connection name
  - Database type (PostgreSQL, MySQL, SQLite, MongoDB)
  - Host/path
  - Status (connected/disconnected)
  - Last used timestamp
  - Actions: Connect, Edit, Delete, Test

**Add/Edit Connection Form**
- Connection name input
- Database type selector
- Connection details based on type:
  - **SQLite**: File path
  - **PostgreSQL/MySQL**: Host, Port, Username, Password, Database name
  - **MongoDB**: Connection URI
- "Save connection" checkbox
- Test connection button
- Save button
- Credentials are encrypted on backend

**Chat with Database Interface**
- Connection selector dropdown (load saved connections)
- Connect button
- Schema viewer (collapsible sidebar):
  - List of tables
  - Expandable to show columns and types
  - Search tables/columns
- Question input area (textarea)
- Chat history display
- For each query:
  - User question
  - Generated SQL query (syntax highlighted)
  - SQL explanation
  - Safety indicator (SAFE/UNSAFE badge)
  - Execute button (only for SAFE queries)
  - Results table (paginated)
  - Export results button (CSV, JSON)
  - Query execution time
- Clear chat button
- Disconnect button

---

### 6. Tenant Settings

**Profile Tab**
- Tenant name (editable)
- Tenant ID (read-only, copyable)
- Email (editable)
- Phone (editable)
- Created date (read-only)
- Billing tier (read-only, with upgrade button)
- Save changes button

**Usage & Quotas Tab**
- Storage quota:
  - Used / Total (GB)
  - Progress bar
  - Percentage
- Query quota:
  - Used / Total (monthly)
  - Progress bar
  - Reset date
- Document quota:
  - Current count / Limit
- Connection quota:
  - Active / Max connections
- Upgrade plan button (if applicable)

**API Keys Tab**
- List of API keys table:
  - Key name
  - Key prefix (e.g., "sk_...abc123")
  - Created date
  - Last used date
  - Permissions
  - Actions: Copy, Revoke
- Generate new API key button
- Modal for key generation:
  - Key name input
  - Permission checkboxes (read, write, admin)
  - Generate button
  - Display full key once (with copy button and warning)

**Billing Tab** (if applicable)
- Current plan details
- Billing cycle
- Next billing date
- Payment method (masked)
- Billing history table
- Download invoice buttons
- Update payment method button
- Upgrade/downgrade plan button

**Notifications Tab**
- Email notification preferences:
  - Quota warnings (80%, 90%, 95%)
  - Processing completion
  - Billing reminders
  - Security alerts
- Toggle switches for each notification type
- Save preferences button

---

### 7. Admin Dashboard (Super Admin Only)

**Tenant Management**
- Tenant list table:
  - Tenant ID
  - Name
  - Email
  - Billing tier
  - Status (active/inactive)
  - Created date
  - Storage used
  - Query count (monthly)
  - Actions: View, Edit, Deactivate, Delete
- Search tenants
- Filter by: tier, status, date range
- Sort by: name, created date, usage
- Create new tenant button
- Pagination

**Tenant Details Modal/Page**
- Tenant information (editable)
- Usage statistics
- User list for tenant
- Activity log
- Quota management:
  - Adjust storage limit
  - Adjust query limit
  - Adjust connection limit
- Billing management:
  - Change tier
  - View invoices
  - Manual billing adjustments
- Danger zone:
  - Deactivate tenant
  - Delete tenant (with confirmation)

**System Metrics Dashboard**
- Total tenants count
- Active tenants count
- Total storage used (all tenants)
- Total queries (last 30 days)
- System health indicators
- Charts:
  - Tenants by tier (pie chart)
  - Storage usage by tenant (bar chart)
  - Query volume over time (line chart)
  - Error rate over time (line chart)

**User Management**
- User list across all tenants
- Columns: User ID, Email, Tenant, Role, Status, Last login
- Search users
- Filter by: tenant, role, status
- Actions: View, Edit role, Deactivate

---

## API Integration Requirements

### Authentication Flow

**Login**
```javascript
POST /api/v1/auth/login
Body: { tenant_id, user_id, api_key }
Response: { access_token, refresh_token, token_type, tenant_id }
```

**Token Refresh**
```javascript
POST /api/v1/auth/refresh
Body: { refresh_token }
Response: { access_token, refresh_token, token_type, tenant_id }
```

**Verify Token**
```javascript
GET /api/v1/auth/verify
Headers: { Authorization: "Bearer <token>" }
Response: { valid: true, message }
```

### Tenant Management

**Register Tenant**
```javascript
POST /api/v1/tenants/register
Body: { name, email, phone?, billing_tier }
Response: { id, name, slug, email, is_active, created_at, billing_tier }
```

**Get Current Tenant**
```javascript
GET /api/v1/tenants/me
Headers: { Authorization: "Bearer <token>" }
Response: { id, name, email, billing_tier, billing_status, ... }
```

**List Tenants (Admin)**
```javascript
GET /api/v1/tenants/?skip=0&limit=100
Response: [{ id, name, email, is_active, ... }]
```

**Update Tenant**
```javascript
PUT /api/v1/tenants/{tenant_id}
Body: { name?, email?, phone?, is_active?, billing_tier? }
Response: { updated tenant object }
```

### File Upload

**Upload File**
```javascript
POST /api/v1/upload/
Headers: { Authorization: "Bearer <token>" }
Body: FormData with file
Response: { message, file_path, tenant_id, filename, size_mb, storage_usage }
```

**List Files**
```javascript
GET /api/v1/files/
Headers: { Authorization: "Bearer <token>" }
Response: [{ filename, size_bytes, size_mb, created_at, path }]
```

**Download File**
```javascript
GET /api/v1/files/{filename}
Headers: { Authorization: "Bearer <token>" }
Response: File download
```

**Delete File**
```javascript
DELETE /api/v1/files/{filename}
Headers: { Authorization: "Bearer <token>" }
Response: { message, tenant_id, filename }
```

**Get Storage Usage**
```javascript
GET /api/v1/files/storage/usage
Headers: { Authorization: "Bearer <token>" }
Response: { total_files, total_bytes, total_mb, total_gb }
```

### Knowledge Base Management

**List Knowledge Bases**
```javascript
GET /api/v1/manage/knowledge-bases/
Headers: { Authorization: "Bearer <token>" }
Response: ["kb1", "kb2", "kb3"]
```

**Get KB Details**
```javascript
GET /api/v1/manage/knowledge-bases/{kb_name}/details
Headers: { Authorization: "Bearer <token>" }
Response: { name, collection_name, vectors_count, files_count, files: [...] }
```

**Delete KB**
```javascript
DELETE /api/v1/manage/knowledge-bases/{kb_name}
Headers: { Authorization: "Bearer <token>" }
Response: { message }
```

**Delete File from KB**
```javascript
DELETE /api/v1/manage/knowledge-bases/{kb_name}/files/{filename}
Headers: { Authorization: "Bearer <token>" }
Response: { message }
```

**Reindex File**
```javascript
POST /api/v1/manage/knowledge-bases/{kb_name}/files/{filename}/reindex
Headers: { Authorization: "Bearer <token>" }
Response: { message }
```

### Document Processing

**Process File to KB**
```javascript
POST /api/v1/upload-to-qdrant/
Headers: { Authorization: "Bearer <token>" }
Body: { file_path, kb_name }
Response: { message, job_id, tenant_id, kb_name, collection_name, status_url }
```

**Get Processing Status**
```javascript
GET /api/v1/processing-status/{job_id}
Response: { job_id, file_path, collection_name, status, created_at, started_at, completed_at, error }
```

**List All Jobs**
```javascript
GET /api/v1/jobs/
Response: { total_jobs, jobs: [...] }
```

### RAG Query

**Query Knowledge Base**
```javascript
POST /api/v1/query/
Headers: { Authorization: "Bearer <token>" }
Body: { kb_name, query, chat_history? }
Response: { answer, tenant_id, kb_name }
```

### Database Interaction

**Connect to Database**
```javascript
POST /api/v1/db/connect
Body: { db_uri }
Response: { message }
```

**Generate SQL Query**
```javascript
POST /api/v1/db/generate-query
Body: { question }
Response: { query, explanation }
```

**Execute SQL Query**
```javascript
POST /api/v1/db/execute-query
Body: { query }
Response: [{ row1 }, { row2 }, ...]
```

**Save Connection**
```javascript
POST /api/v1/db/connections/save
Body: { name, db_type, host?, port?, username?, password?, database?, db_path? }
Response: { message }
```

**List Connections**
```javascript
GET /api/v1/db/connections/list
Response: [{ name, type, host, database, username }]
```

**Load Connection**
```javascript
GET /api/v1/db/connections/{name}
Response: { type, host, port, username, password, database }
```

**Delete Connection**
```javascript
DELETE /api/v1/db/connections/{name}
Response: { message }
```

---

## Technical Requirements

### State Management
- Use React Context API or Redux for global state
- Manage authentication state (token, tenant info)
- Manage user preferences
- Cache API responses where appropriate
- Handle loading and error states consistently

### Routing
- Use React Router for navigation
- Protected routes (require authentication)
- Admin-only routes (require admin role)
- Redirect to login if unauthenticated
- Redirect to dashboard after login
- Handle 404 pages

### HTTP Client
- Use Axios or Fetch API
- Create API service layer with base URL configuration
- Automatic token injection in headers
- Automatic token refresh on 401 errors
- Request/response interceptors for error handling
- Retry logic for failed requests

### Error Handling
- Display user-friendly error messages
- Toast notifications for success/error
- Form validation errors inline
- Network error handling (offline mode)
- 401: Redirect to login
- 403: Show "Access Denied" message
- 404: Show "Not Found" page
- 500: Show "Server Error" message with retry option

### Loading States
- Skeleton loaders for initial page loads
- Spinners for button actions
- Progress bars for file uploads
- Shimmer effects for data tables
- Disable buttons during loading

### Responsive Design
- Mobile-first approach
- Breakpoints: mobile (<768px), tablet (768-1024px), desktop (>1024px)
- Collapsible sidebar on mobile
- Touch-friendly buttons and inputs
- Responsive tables (horizontal scroll or card view on mobile)

### Accessibility
- ARIA labels for all interactive elements
- Keyboard navigation support
- Focus indicators
- Screen reader friendly
- Color contrast compliance (WCAG AA)
- Alt text for images

### Performance
- Code splitting by route
- Lazy loading for heavy components
- Debounce search inputs
- Virtualized lists for large datasets
- Image optimization
- Minimize bundle size

### Security
- Never store tokens in localStorage (use memory + httpOnly cookies)
- Sanitize user inputs
- Escape HTML in user-generated content
- HTTPS only in production
- Content Security Policy headers
- CSRF protection

---

## UI/UX Guidelines

### Design System
- Use a component library (Material-UI, Ant Design, Chakra UI, or custom)
- Consistent color palette:
  - Primary color (brand)
  - Secondary color
  - Success (green)
  - Warning (yellow/orange)
  - Error (red)
  - Info (blue)
  - Neutral grays
- Typography scale (h1-h6, body, caption)
- Spacing scale (4px, 8px, 16px, 24px, 32px, 48px, 64px)
- Border radius (4px, 8px, 16px)
- Shadow levels (none, sm, md, lg, xl)

### Components
- Reusable button component (primary, secondary, danger, ghost)
- Input components (text, password, email, number, textarea, select)
- Card component
- Modal/Dialog component
- Toast/Notification component
- Table component with sorting, filtering, pagination
- Tabs component
- Accordion component
- Progress bar component
- Badge component
- Avatar component
- Dropdown menu component
- Breadcrumb component
- Sidebar/Navigation component
- Header component
- Footer component

### Interactions
- Hover states for all interactive elements
- Active/pressed states
- Disabled states
- Loading states
- Smooth transitions (200-300ms)
- Confirmation dialogs for destructive actions
- Tooltips for icons and truncated text
- Keyboard shortcuts for power users

### Feedback
- Success toast after successful actions
- Error toast for failures
- Inline validation for forms
- Progress indicators for long operations
- Empty states with helpful messages
- Loading skeletons
- Optimistic UI updates where appropriate

---

## Deployment Considerations

### Environment Variables
```
REACT_APP_API_BASE_URL=http://localhost:8000/api/v1
REACT_APP_ENVIRONMENT=development|staging|production
REACT_APP_SENTRY_DSN=<sentry-dsn>
REACT_APP_GOOGLE_ANALYTICS_ID=<ga-id>
```

### Build Configuration
- Production build optimization
- Source maps for debugging
- Environment-specific configs
- CDN for static assets
- Gzip/Brotli compression

### Hosting
- Static hosting (Vercel, Netlify, AWS S3 + CloudFront)
- CI/CD pipeline (GitHub Actions, GitLab CI)
- Automatic deployments on merge to main
- Preview deployments for PRs

### Monitoring
- Error tracking (Sentry, Rollbar)
- Analytics (Google Analytics, Mixpanel)
- Performance monitoring (Web Vitals)
- User session recording (optional)

---

## Development Workflow

### Project Structure
```
src/
├── api/                 # API service layer
│   ├── auth.js
│   ├── tenants.js
│   ├── files.js
│   ├── knowledgeBases.js
│   ├── database.js
│   └── admin.js
├── components/          # Reusable components
│   ├── common/
│   │   ├── Button.jsx
│   │   ├── Input.jsx
│   │   ├── Modal.jsx
│   │   └── ...
│   ├── layout/
│   │   ├── Header.jsx
│   │   ├── Sidebar.jsx
│   │   └── Footer.jsx
│   └── ...
├── pages/               # Page components
│   ├── Login.jsx
│   ├── Dashboard.jsx
│   ├── KnowledgeBases.jsx
│   ├── DatabaseChat.jsx
│   ├── Settings.jsx
│   └── Admin.jsx
├── context/             # React Context
│   ├── AuthContext.jsx
│   └── TenantContext.jsx
├── hooks/               # Custom hooks
│   ├── useAuth.js
│   ├── useApi.js
│   └── useDebounce.js
├── utils/               # Utility functions
│   ├── formatters.js
│   ├── validators.js
│   └── constants.js
├── styles/              # Global styles
│   ├── theme.js
│   └── global.css
├── App.jsx              # Main app component
└── index.jsx            # Entry point
```

### Testing
- Unit tests for utility functions
- Component tests with React Testing Library
- Integration tests for API calls
- E2E tests with Cypress or Playwright
- Minimum 70% code coverage

### Code Quality
- ESLint for linting
- Prettier for formatting
- Husky for pre-commit hooks
- TypeScript (optional but recommended)
- PropTypes for type checking (if not using TypeScript)

---

## Summary

This ReactJS frontend should provide a complete, production-ready interface for the multitenant RAG system with:

1. **Secure authentication** with JWT tokens and automatic refresh
2. **Knowledge base management** with document upload, querying, and organization
3. **Database chat interface** with natural language to SQL conversion
4. **File management** with upload, download, and storage tracking
5. **Tenant settings** with profile, quotas, API keys, and billing
6. **Admin dashboard** for managing tenants and system metrics
7. **Responsive design** that works on all devices
8. **Robust error handling** and loading states
9. **Performance optimization** with code splitting and lazy loading
10. **Accessibility compliance** for all users

The frontend should communicate with the backend API using the documented endpoints, handle authentication properly, and provide an intuitive user experience for both regular users and administrators.
