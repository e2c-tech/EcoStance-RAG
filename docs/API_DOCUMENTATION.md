# Complete API Documentation
## Multitenant RAG System API Reference

**Base URL:** `http://127.0.0.1:8000/api/v1`
**Version:** 1.0
**Last Updated:** November 20, 2024

**Interactive Documentation:**
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

---

## Overview

This document provides comprehensive API documentation for the Multitenant RAG (Retrieval-Augmented Generation) System. The API enables document management, knowledge base operations, natural language querying, database interactions, and administrative functions.

**Key Features:**
- Multi-tenant architecture with complete data isolation
- JWT-based authentication with refresh tokens
- API key management for programmatic access
- File upload and processing with multiple format support
- Vector-based knowledge base management
- Natural language to SQL query generation
- Usage tracking and analytics
- Quota management and monitoring
- Administrative operations

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Tenant Management](#2-tenant-management)
3. [API Key Management](#3-api-key-management)
4. [File Upload & Management](#4-file-upload--management)
5. [Document Processing](#5-document-processing)
6. [Knowledge Base Management](#6-knowledge-base-management)
7. [RAG Query](#7-rag-query)
8. [Database Interaction](#8-database-interaction)
9. [Usage Analytics](#9-usage-analytics)
10. [Quota Management](#10-quota-management)
11. [Metrics & Monitoring](#11-metrics--monitoring)
12. [Admin Operations](#12-admin-operations)

---

## Authentication

All authenticated endpoints require a Bearer token in the Authorization header format:
`Authorization: Bearer {access_token}`

**Token Expiration:**
- Access Token: 30 minutes
- Refresh Token: 7 days

**Security Notes:**
- Tokens are JWT-based and contain tenant information
- Access tokens should be stored securely in memory (not localStorage)
- Refresh tokens should be stored in httpOnly cookies
- Always use HTTPS in production

---

## 1. Authentication

### 1.1 Login

Generate JWT access and refresh tokens for a tenant.

**Endpoint:** `POST /auth/login`
**Authentication:** None (Public)
**Content-Type:** application/json

**Request Body:**
- tenant_id (string, required): Unique tenant identifier
- user_id (string, optional): User identifier within the tenant
- api_key (string, optional): API key for authentication

**Success Response (200 OK):**
- access_token (string): JWT access token for API authentication
- refresh_token (string): JWT refresh token for obtaining new access tokens
- token_type (string): Token type, always "bearer"
- tenant_id (string): Authenticated tenant ID

**Error Responses:**
- 401 Unauthorized: Invalid credentials or tenant not found
- 400 Bad Request: Missing required fields or malformed request
- 403 Forbidden: Tenant account is inactive or suspended
- 500 Internal Server Error: Server-side error during authentication

**Use Cases:**
- Initial authentication for web applications
- Mobile app authentication
- CLI tool authentication
- Service-to-service authentication

### 1.2 Refresh Token

Obtain a new access token using a valid refresh token.

**Endpoint:** `POST /auth/refresh`
**Authentication:** None (uses refresh token)
**Content-Type:** application/json

**Request Body:**
- refresh_token (string, required): Valid refresh token from login

**Success Response (200 OK):**
- access_token (string): New JWT access token
- refresh_token (string): New refresh token (token rotation)
- token_type (string): Token type, always "bearer"
- tenant_id (string): Tenant ID

**Error Responses:**
- 401 Unauthorized: Invalid or expired refresh token
- 400 Bad Request: Missing refresh token
- 403 Forbidden: Tenant account is inactive
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Automatic token refresh before expiration
- Maintaining user sessions without re-authentication
- Background token refresh in SPAs

### 1.3 Verify Token

Verify if the current access token is valid and not expired.

**Endpoint:** `GET /auth/verify`
**Authentication:** Required (Bearer token)

**Success Response (200 OK):**
- valid (boolean): Token validity status, always true if successful
- message (string): Confirmation message
- tenant_id (string): Tenant ID from token
- expires_at (string): Token expiration timestamp

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Tenant account is inactive
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Health checks for authentication status
- Validating tokens before making API calls
- Session management in applications

---

## 2. Tenant Management

### 2.1 Register Tenant

Create a new tenant account with self-service registration.

**Endpoint:** `POST /tenants/register`
**Authentication:** None (Public)
**Content-Type:** application/json

**Request Body:**
- name (string, required, 3-100 chars): Tenant organization name
- email (string, required, valid email): Primary contact email
- phone (string, optional): Contact phone number
- billing_tier (string, optional, default: "free"): Initial billing tier

**Billing Tiers:**
- free: 10GB storage, 1,000 queries/day, 10,000 documents
- starter: 50GB storage, 5,000 queries/day, 50,000 documents
- professional: 200GB storage, 20,000 queries/day, 200,000 documents
- enterprise: 1TB storage, 100,000 queries/day, 1,000,000 documents

**Success Response (200 OK):**
- id (string, UUID): Unique tenant identifier
- name (string): Tenant name
- slug (string): URL-friendly tenant identifier
- email (string): Contact email
- phone (string|null): Contact phone
- is_active (boolean): Account status, always true on creation
- created_at (string, ISO 8601): Account creation timestamp
- billing_tier (string): Assigned billing tier
- billing_status (string): Billing status, always "active" on creation

**Error Responses:**
- 400 Bad Request: Invalid input, duplicate email, or validation errors
- 409 Conflict: Tenant with this email already exists
- 500 Internal Server Error: Server-side error during registration

**Use Cases:**
- Self-service tenant registration
- Automated tenant provisioning
- Trial account creation

### 2.2 Get Current Tenant

Retrieve information about the currently authenticated tenant.

**Endpoint:** `GET /tenants/me`
**Authentication:** Required (Bearer token)

**Success Response (200 OK):**
- id (string, UUID): Tenant identifier
- name (string): Tenant name
- slug (string): URL-friendly identifier
- email (string): Contact email
- phone (string|null): Contact phone
- is_active (boolean): Account status
- created_at (string, ISO 8601): Creation timestamp
- updated_at (string|null, ISO 8601): Last update timestamp
- billing_tier (string): Current billing tier
- billing_status (string): Billing status (active/suspended/cancelled)
- settings (object): Tenant-specific settings and quotas
- logo_url (string|null): Tenant logo URL

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 404 Not Found: Tenant not found
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Loading tenant profile in applications
- Displaying tenant information in dashboards
- Checking account status and quotas

### 2.3 List All Tenants (Admin)

Retrieve a paginated list of all tenants in the system.

**Endpoint:** `GET /tenants/`
**Authentication:** Required (Admin)
**Query Parameters:**
- skip (integer, optional, default: 0): Number of records to skip for pagination
- limit (integer, optional, default: 100, max: 1000): Maximum records to return

**Success Response (200 OK):**
Returns an array of tenant objects, each containing:
- id (string, UUID): Tenant identifier
- name (string): Tenant name
- slug (string): URL-friendly identifier
- email (string): Contact email
- is_active (boolean): Account status
- created_at (string, ISO 8601): Creation timestamp
- billing_tier (string): Current billing tier
- billing_status (string): Billing status

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions (not admin)
- 400 Bad Request: Invalid pagination parameters
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Admin dashboard tenant listing
- Tenant management interfaces
- Reporting and analytics

### 2.4 Get Tenant by ID (Admin)

Retrieve detailed information about a specific tenant.

**Endpoint:** `GET /tenants/{tenant_id}`
**Authentication:** Required (Admin)
**Path Parameters:**
- tenant_id (string, UUID, required): Tenant identifier

**Success Response (200 OK):**
Returns complete tenant object with all fields including settings and metadata.

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Tenant not found
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Viewing tenant details in admin panel
- Tenant support and troubleshooting
- Audit and compliance checks

### 2.5 Update Tenant (Admin)

Update tenant information and settings.

**Endpoint:** `PUT /tenants/{tenant_id}`
**Authentication:** Required (Admin)
**Content-Type:** application/json
**Path Parameters:**
- tenant_id (string, UUID, required): Tenant identifier

**Request Body (all fields optional):**
- name (string): Updated tenant name
- email (string): Updated contact email
- phone (string): Updated contact phone
- is_active (boolean): Account status
- billing_tier (string): Updated billing tier
- billing_status (string): Updated billing status
- settings (object): Updated settings and quotas
- logo_url (string): Updated logo URL

**Success Response (200 OK):**
Returns updated tenant object with all fields.

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Tenant not found
- 400 Bad Request: Invalid input or validation errors
- 409 Conflict: Email already in use by another tenant
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Updating tenant information
- Changing billing tiers
- Modifying quotas and settings
- Account management

### 2.6 Delete Tenant (Admin)

Delete a tenant account (soft delete by default, hard delete optional).

**Endpoint:** `DELETE /tenants/{tenant_id}`
**Authentication:** Required (Admin)
**Path Parameters:**
- tenant_id (string, UUID, required): Tenant identifier
**Query Parameters:**
- hard_delete (boolean, optional, default: false): Permanent deletion if true

**Success Response (200 OK):**
- message (string): Deletion confirmation message
- tenant_id (string): Deleted tenant ID
- deletion_type (string): "soft" or "hard"

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Tenant not found
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Account closure
- GDPR compliance (hard delete)
- Temporary deactivation (soft delete)

### 2.7 Activate Tenant (Admin)

Reactivate a deactivated or suspended tenant account.

**Endpoint:** `POST /tenants/{tenant_id}/activate`
**Authentication:** Required (Admin)
**Path Parameters:**
- tenant_id (string, UUID, required): Tenant identifier

**Success Response (200 OK):**
Returns activated tenant object with is_active set to true.

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Tenant not found
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Restoring suspended accounts
- Reactivating after payment issues resolved
- Account recovery

### 2.8 Deactivate Tenant (Admin)

Deactivate a tenant account, preventing all API access.

**Endpoint:** `POST /tenants/{tenant_id}/deactivate`
**Authentication:** Required (Admin)
**Path Parameters:**
- tenant_id (string, UUID, required): Tenant identifier

**Success Response (200 OK):**
Returns deactivated tenant object with is_active set to false.

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Tenant not found
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Suspending accounts for non-payment
- Temporary account suspension
- Security-related deactivation

---

## 3. API Key Management

### 3.1 Create API Key

Generate a new API key for programmatic access to the API.

**Endpoint:** `POST /api-keys/`
**Authentication:** Required (Bearer token)
**Content-Type:** application/json

**Request Body:**
- name (string, required, 1-255 chars): Friendly name for the API key
- expires_in_days (integer, optional, 1-365): Expiration period in days
- permissions (array of strings, optional): List of permissions for this key

**Success Response (201 Created):**
- id (string, UUID): Unique key identifier
- api_key (string): Full API key (shown only once, save securely)
- key_prefix (string): Key prefix for identification (e.g., "sk_live_abc")
- name (string): Key name
- tenant_id (string): Associated tenant ID
- permissions (array): Assigned permissions
- expires_at (string|null, ISO 8601): Expiration timestamp
- created_at (string, ISO 8601): Creation timestamp
- message (string): Warning to save the key securely

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 400 Bad Request: Invalid input or validation errors
- 403 Forbidden: Insufficient permissions
- 500 Internal Server Error: Server-side error

**Important Notes:**
- The full API key is only shown once in this response
- Store the key securely - it cannot be retrieved again
- Lost keys must be revoked and new ones created

**Use Cases:**
- Creating keys for CI/CD pipelines
- Generating keys for third-party integrations
- Setting up service-to-service authentication
- Creating keys with limited permissions

### 3.2 List API Keys

Retrieve all API keys for the current tenant.

**Endpoint:** `GET /api-keys/`
**Authentication:** Required (Bearer token)

**Success Response (200 OK):**
Returns an array of API key objects, each containing:
- id (string, UUID): Key identifier
- tenant_id (string): Associated tenant ID
- name (string): Key name
- key_prefix (string): Key prefix for identification
- permissions (array): Assigned permissions
- last_used_at (string|null, ISO 8601): Last usage timestamp
- usage_count (integer): Total number of times used
- is_active (boolean): Key status
- expires_at (string|null, ISO 8601): Expiration timestamp
- created_at (string, ISO 8601): Creation timestamp
- updated_at (string|null, ISO 8601): Last update timestamp

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Viewing all active API keys
- Auditing key usage
- Managing key lifecycle

### 3.3 Revoke API Key

Deactivate an API key immediately.

**Endpoint:** `DELETE /api-keys/{key_id}`
**Authentication:** Required (Bearer token)
**Path Parameters:**
- key_id (string, UUID, required): API key identifier

**Success Response (204 No Content):**
No response body. Key is immediately deactivated.

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 404 Not Found: API key not found
- 500 Internal Server Error: Server-side error

**Important Notes:**
- Revocation is immediate and cannot be undone
- All requests using the revoked key will fail
- Consider rotating keys instead of revoking if continuity is needed

**Use Cases:**
- Revoking compromised keys
- Removing keys for decommissioned services
- Security incident response
- Key lifecycle management

### 3.4 Rotate API Key

Create a new API key and revoke the old one in a single operation.

**Endpoint:** `POST /api-keys/{key_id}/rotate`
**Authentication:** Required (Bearer token)
**Content-Type:** application/json
**Path Parameters:**
- key_id (string, UUID, required): API key identifier to rotate

**Request Body:**
- new_key_name (string, optional, max 255 chars): Name for the new key

**Success Response (200 OK):**
- id (string, UUID): New key identifier
- api_key (string): Full new API key (shown only once)
- key_prefix (string): New key prefix
- name (string): New key name
- tenant_id (string): Associated tenant ID
- permissions (array): Inherited permissions from old key
- expires_at (string|null, ISO 8601): Expiration timestamp
- created_at (string, ISO 8601): Creation timestamp
- message (string): Confirmation message

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 404 Not Found: API key not found
- 400 Bad Request: Invalid input
- 500 Internal Server Error: Server-side error

**Important Notes:**
- Old key is immediately revoked after new key creation
- New key inherits permissions from old key
- Full new key is shown only once
- Rotation is atomic - both operations succeed or fail together

**Use Cases:**
- Regular key rotation for security
- Updating keys without service interruption
- Compliance with security policies
- Responding to potential key exposure


---

## 4. File Upload & Management

### 4.1 Upload File

Upload a file to tenant-specific storage.

**Endpoint:** `POST /upload/`
**Authentication:** Required (Bearer token)
**Content-Type:** multipart/form-data

**Request Body:**
- file (file, required): File to upload

**Supported File Formats:**
- Documents: PDF, DOCX, TXT, MD
- Spreadsheets: XLSX, XLS, CSV
- Web: HTML, HTM
- Data: SQL, JSONL

**Success Response (200 OK):**
- message (string): Success confirmation
- file_path (string): Full path to uploaded file
- tenant_id (string): Tenant identifier
- filename (string): Original filename
- size_mb (float): File size in megabytes
- storage_usage (object): Current storage statistics
  - total_files (integer): Total number of files
  - total_mb (float): Total storage used in MB
  - quota_mb (float): Storage quota limit in MB
  - usage_percent (float): Percentage of quota used

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 400 Bad Request: No file provided or invalid file type
- 413 Payload Too Large: File exceeds size limit or storage quota exceeded
  - Returns detailed quota information in error response
- 415 Unsupported Media Type: File format not supported
- 500 Internal Server Error: Server-side error during upload

**Storage Quota Error Response (413):**
- error (string): "Storage quota exceeded"
- quota_mb (float): Total quota limit
- current_usage_mb (float): Current usage
- available_mb (float): Available space
- usage_percent (float): Percentage used

**Use Cases:**
- Uploading documents for processing
- Bulk file uploads
- Document management systems
- Content ingestion pipelines

### 4.2 List Files

Retrieve all files for the authenticated tenant.

**Endpoint:** `GET /files/`
**Authentication:** Required (Bearer token)

**Success Response (200 OK):**
Returns an array of file objects, each containing:
- filename (string): Original filename
- size_bytes (integer): File size in bytes
- size_mb (float): File size in megabytes
- created_at (string, ISO 8601): Upload timestamp
- path (string): Full file path

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Displaying file lists in UI
- File management dashboards
- Storage auditing
- Backup and recovery operations

### 4.3 Download File

Download a previously uploaded file.

**Endpoint:** `GET /files/{filename}`
**Authentication:** Required (Bearer token)
**Path Parameters:**
- filename (string, required): Name of file to download

**Success Response (200 OK):**
Returns the file as a binary stream with appropriate Content-Type header.

**Response Headers:**
- Content-Type: Determined by file extension
- Content-Disposition: attachment; filename="{filename}"
- Content-Length: File size in bytes

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 404 Not Found: File not found
- 403 Forbidden: Access denied to this file
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Downloading original files
- File backup operations
- Exporting documents
- File sharing

### 4.4 Delete File

Delete a file from tenant storage.

**Endpoint:** `DELETE /files/{filename}`
**Authentication:** Required (Bearer token)
**Path Parameters:**
- filename (string, required): Name of file to delete

**Success Response (200 OK):**
- message (string): Deletion confirmation
- tenant_id (string): Tenant identifier
- filename (string): Deleted filename

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 404 Not Found: File not found
- 403 Forbidden: Access denied to this file
- 500 Internal Server Error: Server-side error

**Important Notes:**
- Deletion is permanent and cannot be undone
- If file is used in knowledge bases, it will be removed from all KBs
- Consider backing up important files before deletion

**Use Cases:**
- Cleaning up unused files
- Storage management
- Removing sensitive data
- Compliance with data retention policies

### 4.5 Get Storage Usage

Retrieve storage usage statistics for the tenant.

**Endpoint:** `GET /files/storage/usage`
**Authentication:** Required (Bearer token)

**Success Response (200 OK):**
- total_files (integer): Total number of files
- total_bytes (integer): Total storage in bytes
- total_mb (float): Total storage in megabytes
- total_gb (float): Total storage in gigabytes

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Displaying storage metrics in dashboards
- Monitoring quota usage
- Capacity planning
- Billing calculations

### 4.6 Check Storage Quota

Verify if uploading a file would exceed the storage quota.

**Endpoint:** `POST /files/storage/check-quota`
**Authentication:** Required (Bearer token)
**Content-Type:** application/x-www-form-urlencoded

**Request Body:**
- file_size_mb (float, required): Size of file to check in megabytes

**Success Response (200 OK):**
- within_quota (boolean): Whether upload would be within quota
- quota_mb (float): Total quota limit
- current_usage_mb (float): Current usage
- available_mb (float): Available space
- usage_percent (float): Percentage of quota used

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 400 Bad Request: Invalid file size parameter
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Pre-upload validation
- Client-side quota checks
- Upload planning
- User feedback before upload

### 4.7 Delete All Files

Delete all files for the tenant (use with extreme caution).

**Endpoint:** `DELETE /files/`
**Authentication:** Required (Bearer token)

**Success Response (200 OK):**
- message (string): Deletion confirmation with count
- tenant_id (string): Tenant identifier
- count (integer): Number of files deleted

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 500 Internal Server Error: Server-side error

**Important Notes:**
- This operation is irreversible
- All files will be permanently deleted
- Files will be removed from all knowledge bases
- Requires explicit confirmation in production environments

**Use Cases:**
- Tenant data cleanup
- Account closure
- Testing and development
- Emergency data removal


---

## 5. Document Processing

### 5.1 Process File to Knowledge Base

Process an uploaded file and add it to a knowledge base (Qdrant collection).

**Endpoint:** `POST /upload-to-qdrant/`
**Authentication:** Required (Bearer token)
**Content-Type:** application/x-www-form-urlencoded

**Request Body:**
- file_path (string, required): Path to previously uploaded file
- kb_name (string, optional, default: "default"): Knowledge base name

**Success Response (200 OK):**
- message (string): Processing confirmation message
- job_id (string, UUID): Unique job identifier for tracking
- tenant_id (string): Tenant identifier
- kb_name (string): Knowledge base name
- collection_name (string): Full Qdrant collection name (tenant_tenantid_kbname)
- status_url (string): URL to check processing status

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 400 Bad Request: Invalid file path or KB name
- 404 Not Found: File not found
- 413 Payload Too Large: Document quota exceeded
- 500 Internal Server Error: Server-side error during processing

**Processing Stages:**
1. File validation and reading
2. Text extraction (format-specific)
3. Text chunking
4. Embedding generation
5. Vector indexing in Qdrant

**Use Cases:**
- Adding documents to knowledge bases
- Building searchable document collections
- Creating RAG-enabled knowledge bases
- Batch document processing

### 5.2 Get Processing Status

Check the status of a background processing job.

**Endpoint:** `GET /processing-status/{job_id}`
**Authentication:** None
**Path Parameters:**
- job_id (string, UUID, required): Job identifier from upload-to-qdrant

**Success Response (200 OK):**
- job_id (string, UUID): Job identifier
- file_path (string): Path to file being processed
- collection_name (string): Target collection name
- status (string): Current status (pending/in_progress/completed/failed)
- progress_message (string): Human-readable progress description
- created_at (string, ISO 8601): Job creation timestamp
- started_at (string|null, ISO 8601): Processing start timestamp
- completed_at (string|null, ISO 8601): Completion timestamp
- error (string|null): Error message if failed
- error_message (string|null): Detailed error description

**Status Values:**
- pending: Job queued, not yet started
- in_progress: Currently processing
- completed: Successfully completed
- failed: Processing failed with error

**Error Responses:**
- 404 Not Found: Job ID not found
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Monitoring upload progress
- Displaying processing status in UI
- Polling for completion
- Error handling and retry logic

### 5.3 List All Jobs

Retrieve all processing jobs for monitoring.

**Endpoint:** `GET /jobs/`
**Authentication:** None

**Success Response (200 OK):**
- total_jobs (integer): Total number of jobs
- jobs (array): List of job objects
  - job_id (string, UUID): Job identifier
  - status (string): Current status
  - file_path (string): File being processed
  - collection_name (string): Target collection
  - created_at (string, ISO 8601): Creation timestamp

**Error Responses:**
- 500 Internal Server Error: Server-side error

**Use Cases:**
- System monitoring
- Job queue management
- Performance analysis
- Debugging processing issues


---

## 6. Knowledge Base Management

### 6.1 List Knowledge Bases

Retrieve all knowledge bases for the authenticated tenant.

**Endpoint:** `GET /manage/knowledge-bases/`
**Authentication:** Required (Bearer token)

**Success Response (200 OK):**
Returns an array of knowledge base names (strings).

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Displaying KB list in UI
- KB selection dropdowns
- Dashboard overviews
- Navigation menus

### 6.2 Get Knowledge Base Details

Retrieve detailed information about a specific knowledge base.

**Endpoint:** `GET /manage/knowledge-bases/{kb_name}/details`
**Authentication:** Required (Bearer token)
**Path Parameters:**
- kb_name (string, required): Knowledge base name

**Success Response (200 OK):**
- name (string): Knowledge base name
- collection_name (string): Full Qdrant collection name
- total_points (integer): Total number of vectors/points
- vectors_count (integer): Total vector count
- vector_size (integer): Embedding dimension size
- files_count (integer): Number of files in KB
- files (array): List of file objects
  - filename (string): Original filename
  - chunk_count (integer): Number of chunks from this file
  - file_type (string): File format (pdf, docx, txt, etc.)
  - upload_date (float): Unix timestamp of upload
  - file_size (string): Human-readable file size
  - total_characters (integer): Total character count

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 404 Not Found: Knowledge base not found
- 500 Internal Server Error: Server-side error

**Use Cases:**
- KB details page
- Storage analytics
- File management
- Performance monitoring

### 6.3 Get Knowledge Base Files

Retrieve list of files in a knowledge base.

**Endpoint:** `GET /manage/knowledge-bases/{kb_name}/files`
**Authentication:** Required (Bearer token)
**Path Parameters:**
- kb_name (string, required): Knowledge base name

**Success Response (200 OK):**
- kb_name (string): Knowledge base name
- collection_name (string): Full collection name
- files (array): List of file objects (same structure as in details endpoint)

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 404 Not Found: Knowledge base not found
- 500 Internal Server Error: Server-side error

**Use Cases:**
- File listing in KB
- Document management
- Audit trails
- Content inventory

### 6.4 Delete File from Knowledge Base

Remove a specific file and its vectors from a knowledge base.

**Endpoint:** `DELETE /manage/knowledge-bases/{kb_name}/files/{filename}`
**Authentication:** Required (Bearer token)
**Path Parameters:**
- kb_name (string, required): Knowledge base name
- filename (string, required): File to delete

**Success Response (200 OK):**
- message (string): Deletion confirmation

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 404 Not Found: Knowledge base or file not found
- 500 Internal Server Error: Server-side error

**Important Notes:**
- Removes all vectors/chunks associated with the file
- Does not delete the original file from storage
- Operation is irreversible
- KB remains intact with other files

**Use Cases:**
- Removing outdated documents
- Content management
- Cleaning up KB
- Correcting indexing errors

### 6.5 Delete Knowledge Base

Delete an entire knowledge base and all its contents.

**Endpoint:** `DELETE /manage/knowledge-bases/{kb_name}`
**Authentication:** Required (Bearer token)
**Path Parameters:**
- kb_name (string, required): Knowledge base name

**Success Response (200 OK):**
- message (string): Deletion confirmation

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 404 Not Found: Knowledge base not found
- 500 Internal Server Error: Server-side error

**Important Notes:**
- Deletes the entire Qdrant collection
- Removes all vectors and metadata
- Does not delete original files from storage
- Operation is irreversible
- Consider backing up data before deletion

**Use Cases:**
- Removing unused knowledge bases
- Cleanup operations
- Tenant offboarding
- Testing and development

### 6.6 Reindex File

Re-process and re-index a file in a knowledge base.

**Endpoint:** `POST /manage/knowledge-bases/{kb_name}/files/{filename}/reindex`
**Authentication:** Required (Bearer token)
**Path Parameters:**
- kb_name (string, required): Knowledge base name
- filename (string, required): File to reindex

**Success Response (200 OK):**
- message (string): Reindexing confirmation
- job_id (string, UUID): Processing job identifier

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 404 Not Found: Knowledge base or file not found
- 500 Internal Server Error: Server-side error

**Processing:**
- Removes existing vectors for the file
- Re-extracts text from original file
- Generates new embeddings
- Re-indexes vectors in Qdrant

**Use Cases:**
- Updating embeddings with new models
- Fixing indexing errors
- Refreshing stale content
- Applying new chunking strategies


---

## 7. RAG Query

### 7.1 Query Knowledge Base

Ask a question to a knowledge base and receive an AI-generated answer.

**Endpoint:** `POST /query/`
**Authentication:** Required (Bearer token)
**Content-Type:** application/x-www-form-urlencoded

**Request Body:**
- kb_name (string, required): Knowledge base to query
- query (string, required): Question or search query
- chat_history (array of strings, optional): Previous conversation messages

**Success Response (200 OK):**
- answer (string): AI-generated answer based on retrieved context
- tenant_id (string): Tenant identifier
- kb_name (string): Queried knowledge base name

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 400 Bad Request: Missing required fields
- 404 Not Found: Knowledge base not found
- 429 Too Many Requests: Query quota exceeded
- 500 Internal Server Error: Server-side error

**Query Process:**
1. Query embedding generation
2. Vector similarity search in Qdrant
3. Context retrieval from top matches
4. LLM prompt construction with context
5. Answer generation
6. Response formatting

**Use Cases:**
- Document Q&A applications
- Knowledge base search
- Customer support chatbots
- Research and analysis tools


---

## 8. Database Interaction

### 8.1 Connect to Database

Establish a connection to a database using a connection URI.

**Endpoint:** `POST /db/connect`
**Authentication:** None
**Content-Type:** application/json

**Request Body:**
- db_uri (string, required): Database connection URI

**Supported Database Types:**
- SQLite: sqlite:///path/to/database.db
- PostgreSQL: postgresql://user:password@host:port/database
- MySQL: mysql://user:password@host:port/database
- MongoDB: mongodb://host:port/database

**Success Response (200 OK):**
- message (string): Connection confirmation
- database_type (string): Detected database type
- schema_loaded (boolean): Whether schema was successfully loaded

**Error Responses:**
- 400 Bad Request: Invalid connection URI
- 401 Unauthorized: Database authentication failed
- 500 Internal Server Error: Connection failed or server error

**Important Notes:**
- Connection is stored in session
- Schema is automatically loaded for SQL databases
- Credentials are not persisted unless explicitly saved
- Connection timeout is 30 seconds

**Use Cases:**
- Database exploration
- Ad-hoc queries
- Data analysis
- Database migration planning

### 8.2 Generate SQL Query

Generate SQL query from natural language question.

**Endpoint:** `POST /db/generate-query`
**Authentication:** None
**Content-Type:** application/json

**Request Body:**
- question (string, required): Natural language question about the database

**Success Response (200 OK):**
- sql_query (string): Generated SQL query
- explanation (string): Human-readable explanation of the query
- safety_check (string): Safety status (SAFE/UNSAFE)

**Safety Check:**
- SAFE: Read-only SELECT queries
- UNSAFE: Queries that modify data (INSERT, UPDATE, DELETE, DROP, etc.)

**Error Responses:**
- 400 Bad Request: No database connected or invalid question
- 500 Internal Server Error: Query generation failed

**Important Notes:**
- Requires active database connection
- Uses database schema for context
- Only SELECT queries are marked as SAFE
- Generated queries should be reviewed before execution

**Use Cases:**
- Natural language database queries
- SQL learning and education
- Quick data exploration
- Report generation

### 8.3 Execute SQL Query

Execute a SQL query against the connected database.

**Endpoint:** `POST /db/execute-query`
**Authentication:** None
**Content-Type:** application/json

**Request Body:**
- query (string, required): SQL query to execute

**Success Response (200 OK):**
Returns an array of result objects (rows) or execution confirmation.

For SELECT queries:
- Array of objects where each object represents a row
- Keys are column names, values are cell values

For modification queries:
- message (string): Execution confirmation
- rows_affected (integer): Number of rows affected

**Error Responses:**
- 400 Bad Request: No database connected or invalid query
- 403 Forbidden: Query failed safety check (modification attempt)
- 500 Internal Server Error: Query execution failed

**Important Notes:**
- Only SELECT queries are allowed by default
- Modification queries require explicit permission
- Query timeout is 60 seconds
- Large result sets may be truncated

**Use Cases:**
- Data retrieval
- Report generation
- Database exploration
- Data validation

### 8.4 Save Database Connection

Save a database connection profile for future use.

**Endpoint:** `POST /db/connections/save`
**Authentication:** None
**Content-Type:** application/json

**Request Body:**
- name (string, required): Connection profile name
- db_type (string, required): Database type (sqlite/postgresql/mysql/mongodb)
- host (string, optional): Database host
- port (string, optional): Database port
- username (string, optional): Database username
- password (string, optional): Database password
- database (string, optional): Database name
- db_path (string, optional): Database file path (for SQLite)

**Success Response (200 OK):**
- message (string): Save confirmation

**Error Responses:**
- 400 Bad Request: Invalid input or missing required fields
- 409 Conflict: Connection name already exists
- 500 Internal Server Error: Save failed

**Important Notes:**
- Passwords are encrypted before storage
- Connection profiles are tenant-specific
- Sensitive data is stored securely
- Profiles can be shared across sessions

**Use Cases:**
- Saving frequently used connections
- Team collaboration
- Connection management
- Quick database switching

### 8.5 List Database Connections

Retrieve all saved connection profiles.

**Endpoint:** `GET /db/connections/list`
**Authentication:** None

**Success Response (200 OK):**
Returns an array of connection objects (without passwords):
- name (string): Connection profile name
- type (string): Database type
- host (string): Database host
- database (string): Database name
- username (string): Database username

**Error Responses:**
- 500 Internal Server Error: Retrieval failed

**Use Cases:**
- Connection selection UI
- Connection management
- Quick access to saved databases

### 8.6 Load Database Connection

Load a saved connection profile.

**Endpoint:** `GET /db/connections/{name}`
**Authentication:** None
**Path Parameters:**
- name (string, required): Connection profile name

**Success Response (200 OK):**
- type (string): Database type
- host (string): Database host
- port (string): Database port
- username (string): Database username
- password (string): Decrypted password
- database (string): Database name
- db_path (string): Database file path (for SQLite)

**Error Responses:**
- 404 Not Found: Connection profile not found
- 500 Internal Server Error: Load failed

**Use Cases:**
- Loading saved connections
- Auto-connecting to databases
- Connection restoration

### 8.7 Delete Database Connection

Delete a saved connection profile.

**Endpoint:** `DELETE /db/connections/{name}`
**Authentication:** None
**Path Parameters:**
- name (string, required): Connection profile name

**Success Response (200 OK):**
- message (string): Deletion confirmation

**Error Responses:**
- 404 Not Found: Connection profile not found
- 500 Internal Server Error: Deletion failed

**Use Cases:**
- Removing unused connections
- Connection cleanup
- Security management


---

## 9. Usage Analytics

### 9.1 Get Usage Statistics

Retrieve usage statistics for the current tenant.

**Endpoint:** `GET /usage/stats`
**Authentication:** Required (Bearer token)
**Query Parameters:**
- days (integer, optional, default: 7, range: 1-90): Number of days to analyze

**Success Response (200 OK):**
- total_requests (integer): Total API requests in period
- status_codes (object): Breakdown by HTTP status code
- avg_response_time_ms (float): Average response time in milliseconds
- error_count (integer): Total number of errors
- error_rate_percent (float): Percentage of requests that failed
- top_endpoints (array): Most frequently used endpoints
  - endpoint (string): Endpoint path
  - count (integer): Number of requests
  - avg_response_time_ms (float): Average response time
- period (object): Analysis period
  - start_date (string, ISO 8601): Period start
  - end_date (string, ISO 8601): Period end
  - days (integer): Number of days

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 400 Bad Request: Invalid days parameter
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Usage dashboards
- Performance monitoring
- Capacity planning
- Billing analytics

### 9.2 Get Endpoint Statistics

Retrieve detailed statistics for a specific endpoint.

**Endpoint:** `GET /usage/endpoint/{endpoint:path}`
**Authentication:** Required (Bearer token)
**Path Parameters:**
- endpoint (string, required): Endpoint path (e.g., /api/v1/query)
**Query Parameters:**
- days (integer, optional, default: 7, range: 1-90): Number of days to analyze

**Success Response (200 OK):**
- endpoint (string): Endpoint path
- total_requests (integer): Total requests to this endpoint
- response_times (object): Response time statistics
  - min_ms (float): Minimum response time
  - max_ms (float): Maximum response time
  - avg_ms (float): Average response time
  - p50_ms (float): 50th percentile (median)
  - p95_ms (float): 95th percentile
  - p99_ms (float): 99th percentile

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 400 Bad Request: Invalid parameters
- 404 Not Found: No data for endpoint
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Performance optimization
- SLA monitoring
- Bottleneck identification
- Endpoint-specific analytics

### 9.3 Export Usage Data

Export raw usage data for the current tenant.

**Endpoint:** `GET /usage/export`
**Authentication:** Required (Bearer token)
**Query Parameters:**
- days (integer, optional, default: 30, range: 1-365): Number of days to export

**Success Response (200 OK):**
- tenant_id (string): Tenant identifier
- period (object): Export period
  - start (string, ISO 8601): Period start
  - end (string, ISO 8601): Period end
- total_records (integer): Number of records exported
- data (array): Raw usage records
  - timestamp (string, ISO 8601): Request timestamp
  - endpoint (string): Endpoint path
  - method (string): HTTP method
  - status_code (integer): Response status code
  - response_time_ms (float): Response time
  - user_agent (string): Client user agent

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 400 Bad Request: Invalid days parameter
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Data analysis
- Custom reporting
- Compliance auditing
- Long-term archival


---

## 10. Quota Management

### 10.1 Get Quota Status

Retrieve current quota status including limits, usage, and percentages.

**Endpoint:** `GET /quota/status`
**Authentication:** Required (Bearer token)

**Success Response (200 OK):**
- success (boolean): Always true
- data (object): Quota status information
  - storage (object):
    - limit_bytes (integer): Storage limit in bytes
    - used_bytes (integer): Storage used in bytes
    - available_bytes (integer): Available storage
    - usage_percent (float): Percentage used
  - queries (object):
    - daily_limit (integer): Daily query limit
    - daily_used (integer): Queries used today
    - monthly_limit (integer): Monthly query limit
    - monthly_used (integer): Queries used this month
    - daily_percent (float): Daily usage percentage
    - monthly_percent (float): Monthly usage percentage
  - documents (object):
    - limit (integer): Document count limit
    - used (integer): Current document count
    - available (integer): Available slots
    - usage_percent (float): Percentage used
  - connections (object):
    - max_connections (integer): Maximum concurrent connections
    - active_connections (integer): Currently active connections
  - api_calls (object):
    - hourly_limit (integer): Hourly API call limit
    - hourly_used (integer): API calls this hour
    - minute_limit (integer): Per-minute API call limit
    - minute_used (integer): API calls this minute

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Quota monitoring dashboards
- Usage warnings
- Capacity planning
- Billing displays

### 10.2 Get Quota Limits

Retrieve quota limits for the tenant.

**Endpoint:** `GET /quota/limits`
**Authentication:** Required (Bearer token)

**Success Response (200 OK):**
- success (boolean): Always true
- data (object): Quota limits
  - max_storage_bytes (integer): Storage limit
  - max_queries_per_day (integer): Daily query limit
  - max_queries_per_month (integer): Monthly query limit
  - max_documents (integer): Document limit
  - max_db_connections (integer): Connection limit
  - max_concurrent_queries (integer): Concurrent query limit
  - max_api_calls_per_minute (integer): Per-minute API limit
  - max_api_calls_per_hour (integer): Hourly API limit

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Displaying plan limits
- Upgrade prompts
- Feature availability checks

### 10.3 Get Quota Usage

Retrieve current usage for a specific period.

**Endpoint:** `GET /quota/usage`
**Authentication:** Required (Bearer token)
**Query Parameters:**
- period (string, optional, default: "daily"): Period type (daily/monthly/hourly)

**Success Response (200 OK):**
- success (boolean): Always true
- period (string): Period type
- data (object): Usage data for the period
  - query_count (integer): Number of queries
  - document_count (integer): Number of documents
  - storage_bytes (integer): Storage used
  - api_calls_count (integer): API calls made
  - active_db_connections (integer): Active connections
  - concurrent_queries (integer): Concurrent queries

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 400 Bad Request: Invalid period parameter
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Real-time usage monitoring
- Usage trends analysis
- Quota enforcement

### 10.4 Get Quota History

Retrieve historical quota usage data.

**Endpoint:** `GET /quota/history`
**Authentication:** Required (Bearer token)
**Query Parameters:**
- days (integer, optional, default: 30): Number of days to retrieve

**Success Response (200 OK):**
- success (boolean): Always true
- days (integer): Number of days retrieved
- data (array): Historical usage records
  - date (string, ISO 8601): Record date
  - period_type (string): Period type (daily/monthly/hourly)
  - query_count (integer): Queries in period
  - document_count (integer): Documents in period
  - storage_bytes (integer): Storage used
  - storage_gb (float): Storage in gigabytes
  - api_calls (integer): API calls in period

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 400 Bad Request: Invalid days parameter
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Usage trend analysis
- Historical reporting
- Capacity forecasting
- Billing reconciliation

### 10.5 Update Tenant Quotas (Admin)

Update quota limits for a specific tenant.

**Endpoint:** `PUT /quota/admin/tenant/{tenant_id}`
**Authentication:** Required (Admin)
**Content-Type:** application/json
**Path Parameters:**
- tenant_id (string, UUID, required): Tenant identifier

**Request Body (all fields optional):**
- max_queries_per_day (integer): Daily query limit
- max_queries_per_month (integer): Monthly query limit
- max_documents (integer): Document limit
- max_storage_bytes (integer): Storage limit in bytes
- max_db_connections (integer): Connection limit
- max_concurrent_queries (integer): Concurrent query limit
- max_api_calls_per_minute (integer): Per-minute API limit
- max_api_calls_per_hour (integer): Hourly API limit

**Success Response (200 OK):**
- success (boolean): Always true
- message (string): Update confirmation
- data (object): Updated quota status

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Tenant not found
- 400 Bad Request: Invalid quota values
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Plan upgrades/downgrades
- Custom quota adjustments
- Promotional quota increases
- Emergency quota modifications

### 10.6 Reset Tenant Quotas (Admin)

Manually reset quota usage for a tenant.

**Endpoint:** `POST /quota/admin/tenant/{tenant_id}/reset`
**Authentication:** Required (Admin)
**Path Parameters:**
- tenant_id (string, UUID, required): Tenant identifier
**Query Parameters:**
- period (string, optional, default: "daily"): Period to reset (daily/monthly/hourly)

**Success Response (200 OK):**
- success (boolean): Always true
- message (string): Reset confirmation
- period (string): Period that was reset
- period_start (string, ISO 8601): Period start timestamp

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 400 Bad Request: Invalid period parameter
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Quota reset after billing cycle
- Emergency quota relief
- Testing and development
- Customer support interventions


---

## 11. Metrics & Monitoring

### 11.1 Get Tenant Metrics

Retrieve metrics for the tenant over a specified period.

**Endpoint:** `GET /metrics/`
**Authentication:** Required (Bearer token)
**Query Parameters:**
- metric_type (string, optional, default: "daily"): Metric granularity (hourly/daily/monthly)
- days (integer, optional, default: 30, range: 1-365): Number of days to retrieve

**Success Response (200 OK):**
- success (boolean): Always true
- metric_type (string): Metric granularity
- days (integer): Number of days retrieved
- count (integer): Number of metric records
- data (array): Metric records
  - period_start (string, ISO 8601): Period start timestamp
  - storage (object):
    - bytes (integer): Storage in bytes
    - mb (float): Storage in megabytes
    - gb (float): Storage in gigabytes
    - document_count (integer): Number of documents
  - queries (object):
    - total (integer): Total queries
    - successful (integer): Successful queries
    - failed (integer): Failed queries
    - success_rate (float): Success rate percentage
    - avg_response_time_ms (float): Average response time
  - api (object):
    - total_calls (integer): Total API calls
    - successful_calls (integer): Successful calls
    - failed_calls (integer): Failed calls
    - success_rate (float): Success rate percentage
    - avg_response_time_ms (float): Average response time

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 400 Bad Request: Invalid parameters
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Performance dashboards
- Trend analysis
- Capacity planning
- SLA monitoring

### 11.2 Get Storage Metrics

Retrieve storage usage metrics over time.

**Endpoint:** `GET /metrics/storage`
**Authentication:** Required (Bearer token)
**Query Parameters:**
- days (integer, optional, default: 30, range: 1-365): Number of days to retrieve

**Success Response (200 OK):**
- success (boolean): Always true
- days (integer): Number of days retrieved
- data (array): Storage metric records
  - date (string, ISO 8601): Record date
  - storage_bytes (integer): Storage in bytes
  - storage_gb (float): Storage in gigabytes
  - document_count (integer): Number of documents
  - file_count (integer): Number of files
  - growth_bytes (integer): Growth since previous period
  - growth_percent (float): Growth percentage

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 400 Bad Request: Invalid days parameter
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Storage trend analysis
- Capacity forecasting
- Cost optimization
- Growth monitoring

### 11.3 Get Query Metrics

Retrieve query performance metrics.

**Endpoint:** `GET /metrics/queries`
**Authentication:** Required (Bearer token)
**Query Parameters:**
- days (integer, optional, default: 7, range: 1-90): Number of days to analyze

**Success Response (200 OK):**
- success (boolean): Always true
- days (integer): Number of days analyzed
- data (object): Query performance metrics
  - total_queries (integer): Total queries in period
  - successful_queries (integer): Successful queries
  - failed_queries (integer): Failed queries
  - success_rate (float): Success rate percentage
  - response_times (object):
    - min_ms (float): Minimum response time
    - max_ms (float): Maximum response time
    - avg_ms (float): Average response time
    - p50_ms (float): 50th percentile
    - p95_ms (float): 95th percentile
    - p99_ms (float): 99th percentile
  - by_knowledge_base (array): Metrics per KB
    - kb_name (string): Knowledge base name
    - query_count (integer): Queries to this KB
    - avg_response_time_ms (float): Average response time

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 400 Bad Request: Invalid days parameter
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Performance optimization
- SLA compliance monitoring
- Identifying slow queries
- KB performance comparison

### 11.4 Get Error Metrics

Retrieve error rate and error type metrics.

**Endpoint:** `GET /metrics/errors`
**Authentication:** Required (Bearer token)
**Query Parameters:**
- days (integer, optional, default: 7, range: 1-90): Number of days to analyze

**Success Response (200 OK):**
- success (boolean): Always true
- days (integer): Number of days analyzed
- data (object): Error metrics
  - total_requests (integer): Total requests in period
  - total_errors (integer): Total errors
  - error_rate (float): Error rate percentage
  - by_status_code (object): Errors by HTTP status code
    - 400 (integer): Bad request errors
    - 401 (integer): Unauthorized errors
    - 403 (integer): Forbidden errors
    - 404 (integer): Not found errors
    - 429 (integer): Rate limit errors
    - 500 (integer): Server errors
  - by_endpoint (array): Errors by endpoint
    - endpoint (string): Endpoint path
    - error_count (integer): Number of errors
    - error_rate (float): Error rate for this endpoint
  - trend (array): Daily error counts
    - date (string, ISO 8601): Date
    - error_count (integer): Errors on this date

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 400 Bad Request: Invalid days parameter
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Error monitoring
- Reliability tracking
- Incident detection
- Quality assurance

### 11.5 Get Active Alerts

Retrieve currently active alerts for the tenant.

**Endpoint:** `GET /metrics/alerts`
**Authentication:** Required (Bearer token)

**Success Response (200 OK):**
- success (boolean): Always true
- count (integer): Number of active alerts
- data (array): Alert objects
  - id (string, UUID): Alert identifier
  - type (string): Alert type (quota_warning/error_rate/performance/storage)
  - severity (string): Severity level (info/warning/critical)
  - message (string): Alert message
  - threshold (float): Threshold that triggered alert
  - current_value (float): Current value
  - created_at (string, ISO 8601): Alert creation time
  - acknowledged (boolean): Whether alert has been acknowledged

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Alert dashboards
- Proactive monitoring
- Incident management
- Notification systems

### 11.6 Get Alert History

Retrieve historical alerts for the tenant.

**Endpoint:** `GET /metrics/alerts/history`
**Authentication:** Required (Bearer token)
**Query Parameters:**
- days (integer, optional, default: 7, range: 1-90): Number of days to retrieve
- severity (string, optional): Filter by severity (info/warning/critical)

**Success Response (200 OK):**
- success (boolean): Always true
- days (integer): Number of days retrieved
- severity_filter (string|null): Applied severity filter
- count (integer): Number of alerts
- data (array): Historical alert objects (same structure as active alerts)

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 400 Bad Request: Invalid parameters
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Alert trend analysis
- Incident review
- Compliance reporting
- System health assessment

### 11.7 Export Metrics

Export metrics data in CSV or JSON format.

**Endpoint:** `GET /metrics/export`
**Authentication:** Required (Bearer token)
**Query Parameters:**
- format (string, optional, default: "csv"): Export format (csv/json)
- days (integer, optional, default: 30, range: 1-365): Number of days to export

**Success Response (200 OK):**

For CSV format:
- Content-Type: text/csv
- Content-Disposition: attachment; filename=metrics_{tenant_id}_{date}.csv
- Returns CSV file with columns: date, storage_gb, document_count, query_count, query_success_rate, api_calls, api_success_rate

For JSON format:
- success (boolean): Always true
- format (string): "json"
- tenant_id (string): Tenant identifier
- exported_at (string, ISO 8601): Export timestamp
- data (array): Metric records

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 400 Bad Request: Invalid parameters
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Data analysis
- Custom reporting
- Long-term archival
- Integration with BI tools

### 11.8 Get All Tenant Metrics (Admin)

Retrieve metrics for all tenants in the system.

**Endpoint:** `GET /metrics/admin/all`
**Authentication:** Required (Admin)
**Query Parameters:**
- metric_type (string, optional, default: "daily"): Metric granularity
- limit (integer, optional, default: 100, range: 1-1000): Records per tenant

**Success Response (200 OK):**
- success (boolean): Always true
- metric_type (string): Metric granularity
- tenant_count (integer): Number of tenants
- data (object): Metrics by tenant ID
  - {tenant_id} (object):
    - tenant_name (string): Tenant name
    - tenant_tier (string): Billing tier
    - metrics (array): Metric records for this tenant

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 400 Bad Request: Invalid parameters
- 500 Internal Server Error: Server-side error

**Use Cases:**
- System-wide monitoring
- Multi-tenant dashboards
- Capacity planning
- Performance comparison

### 11.9 Trigger Metrics Aggregation (Admin)

Manually trigger metrics aggregation for all tenants.

**Endpoint:** `POST /metrics/admin/aggregate`
**Authentication:** Required (Admin)
**Query Parameters:**
- period (string, optional, default: "hourly"): Period to aggregate (hourly/daily)

**Success Response (200 OK):**
- success (boolean): Always true
- message (string): Aggregation confirmation
- period (string): Period aggregated
- tenant_count (integer): Number of tenants processed

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 400 Bad Request: Invalid period parameter
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Manual metric updates
- Testing aggregation logic
- Recovery from aggregation failures
- On-demand reporting


---

## 12. Admin Operations

### 12.1 Delete Tenant (Admin)

Delete a tenant and all associated data.

**Endpoint:** `DELETE /admin/tenants/{tenant_id}`
**Authentication:** Required (Admin)
**Content-Type:** application/json
**Path Parameters:**
- tenant_id (string, UUID, required): Tenant identifier

**Request Body:**
- soft_delete (boolean, optional, default: true): Soft delete if true, hard delete if false
- confirm (boolean, required): Must be true to proceed with deletion

**Success Response (200 OK):**
- success (boolean): Deletion success status
- message (string): Deletion confirmation
- data (object): Deletion results
  - tenant_deleted (boolean): Whether tenant was deleted
  - files_deleted (integer): Number of files deleted
  - collections_deleted (integer): Number of KB collections deleted
  - errors (array): Any errors encountered during deletion

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Tenant not found
- 400 Bad Request: Confirmation not provided or invalid input
- 500 Internal Server Error: Server-side error

**Deletion Process:**
1. Deactivate tenant account
2. Delete all files from storage
3. Delete all Qdrant collections
4. Delete all database records (soft or hard)
5. Clean up associated resources

**Use Cases:**
- Account closure
- GDPR compliance
- Data cleanup
- Tenant offboarding

### 12.2 Export Tenant Data (Admin)

Export all data for a tenant to a specified location.

**Endpoint:** `POST /admin/tenants/{tenant_id}/export`
**Authentication:** Required (Admin)
**Content-Type:** application/json
**Path Parameters:**
- tenant_id (string, UUID, required): Tenant identifier

**Request Body:**
- export_path (string, optional): Custom export path

**Success Response (200 OK):**
- success (boolean): Always true
- message (string): Export initiation confirmation
- export_path (string): Path where data will be exported
- status (string): "in_progress"

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Tenant not found
- 500 Internal Server Error: Server-side error

**Export Contents:**
- Tenant metadata and settings
- All uploaded files
- Knowledge base configurations
- Vector embeddings
- Usage statistics
- Audit logs

**Use Cases:**
- Data backup
- Tenant migration
- Compliance requirements
- Data portability

### 12.3 Get Tenant Storage (Admin)

Retrieve detailed storage usage for a tenant.

**Endpoint:** `GET /admin/tenants/{tenant_id}/storage`
**Authentication:** Required (Admin)
**Path Parameters:**
- tenant_id (string, UUID, required): Tenant identifier

**Success Response (200 OK):**
- success (boolean): Always true
- data (object): Storage information
  - total_files (integer): Number of files
  - total_bytes (integer): Total storage in bytes
  - total_gb (float): Total storage in gigabytes
  - by_file_type (object): Storage by file type
    - pdf (integer): PDF file storage
    - docx (integer): Word document storage
    - txt (integer): Text file storage
    - (etc.)
  - knowledge_bases (array): Storage per KB
    - kb_name (string): Knowledge base name
    - file_count (integer): Files in this KB
    - vector_count (integer): Vectors in this KB
    - storage_bytes (integer): Storage used

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Tenant not found
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Storage auditing
- Capacity planning
- Billing verification
- Optimization recommendations

### 12.4 Cleanup Expired Sessions (Admin)

Remove expired sessions from the system.

**Endpoint:** `POST /admin/cleanup/sessions`
**Authentication:** Required (Admin)
**Query Parameters:**
- max_age_hours (integer, optional, default: 24): Maximum session age in hours

**Success Response (200 OK):**
- success (boolean): Always true
- message (string): Cleanup confirmation
- deleted_count (integer): Number of sessions deleted

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Regular maintenance
- Database cleanup
- Performance optimization
- Security hygiene

### 12.5 Cleanup Temporary Files (Admin)

Remove old temporary files from the system.

**Endpoint:** `POST /admin/cleanup/temp-files`
**Authentication:** Required (Admin)
**Query Parameters:**
- max_age_days (integer, optional, default: 7): Maximum file age in days

**Success Response (200 OK):**
- success (boolean): Always true
- message (string): Cleanup confirmation
- deleted_count (integer): Number of files deleted

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Storage cleanup
- Regular maintenance
- Disk space management
- System optimization

### 12.6 Archive Audit Logs (Admin)

Archive old audit logs to reduce database size.

**Endpoint:** `POST /admin/cleanup/audit-logs`
**Authentication:** Required (Admin)
**Query Parameters:**
- max_age_days (integer, optional, default: 90): Maximum log age to keep

**Success Response (200 OK):**
- success (boolean): Always true
- message (string): Archive confirmation
- archived_count (integer): Number of logs archived

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Database maintenance
- Compliance with retention policies
- Performance optimization
- Long-term archival

### 12.7 Run Daily Cleanup (Admin)

Execute all daily cleanup tasks in one operation.

**Endpoint:** `POST /admin/cleanup/all`
**Authentication:** Required (Admin)

**Success Response (200 OK):**
- success (boolean): Always true
- message (string): Cleanup initiation confirmation
- status (string): "in_progress"

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 500 Internal Server Error: Server-side error

**Cleanup Tasks:**
- Expired session cleanup
- Temporary file removal
- Audit log archival
- Orphaned resource cleanup
- Cache invalidation

**Use Cases:**
- Scheduled maintenance
- System health maintenance
- Automated cleanup
- Performance optimization

### 12.8 Get System Health (Admin)

Retrieve system-wide health metrics.

**Endpoint:** `GET /admin/health/system`
**Authentication:** Required (Admin)

**Success Response (200 OK):**
- success (boolean): Always true
- data (object): System health information
  - tenants (object):
    - total (integer): Total tenants
    - active (integer): Active tenants
    - inactive (integer): Inactive tenants
  - storage (object):
    - total_bytes (integer): Total storage used
    - total_gb (float): Total storage in gigabytes
  - api (object):
    - calls_24h (integer): API calls in last 24 hours
    - errors_24h (integer): Errors in last 24 hours
    - error_rate (float): Error rate percentage
  - timestamp (string, ISO 8601): Health check timestamp

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 500 Internal Server Error: Server-side error

**Use Cases:**
- System monitoring
- Health dashboards
- Incident detection
- Capacity planning

### 12.9 Get Dashboard Summary (Admin)

Retrieve high-level summary statistics for admin dashboard.

**Endpoint:** `GET /admin/dashboard/summary`
**Authentication:** Required (Admin)

**Success Response (200 OK):**
- success (boolean): Always true
- data (object): Dashboard summary
  - total_tenants (integer): Total number of tenants
  - active_tenants (integer): Active tenants
  - total_users (integer): Total users across all tenants
  - total_storage_gb (float): Total storage used
  - total_queries_today (integer): Queries today
  - total_api_calls_today (integer): API calls today
  - system_health (string): Overall health status (healthy/degraded/critical)
  - recent_alerts (array): Recent system alerts
    - id (string): Alert ID
    - tenant_id (string): Affected tenant
    - type (string): Alert type
    - severity (string): Severity level
    - message (string): Alert message
    - created_at (string, ISO 8601): Alert timestamp
  - timestamp (string, ISO 8601): Summary timestamp

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Admin dashboard
- Quick system overview
- Executive reporting
- Status monitoring

### 12.10 Search Tenants (Admin)

Search for tenants by name, email, or slug.

**Endpoint:** `GET /admin/tenants/search`
**Authentication:** Required (Admin)
**Query Parameters:**
- q (string, required): Search query
- limit (integer, optional, default: 20): Maximum results to return

**Success Response (200 OK):**
- success (boolean): Always true
- data (object): Search results
  - query (string): Search query used
  - count (integer): Number of results
  - tenants (array): Matching tenant objects
    - id (string, UUID): Tenant ID
    - name (string): Tenant name
    - slug (string): Tenant slug
    - email (string): Contact email
    - is_active (boolean): Account status
    - billing_tier (string): Billing tier
    - billing_status (string): Billing status
    - created_at (string, ISO 8601): Creation date

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 400 Bad Request: Missing search query
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Tenant lookup
- Support operations
- Account management
- Quick search

### 12.11 Update Tenant Tier (Admin)

Update a tenant's billing tier and adjust quotas accordingly.

**Endpoint:** `PATCH /admin/tenants/{tenant_id}/tier`
**Authentication:** Required (Admin)
**Content-Type:** application/json
**Path Parameters:**
- tenant_id (string, UUID, required): Tenant identifier

**Request Body:**
- tier (string, required): New billing tier (free/starter/professional/enterprise)

**Success Response (200 OK):**
- success (boolean): Always true
- message (string): Tier update confirmation
- data (object): Update details
  - tenant_id (string): Tenant ID
  - old_tier (string): Previous tier
  - new_tier (string): New tier
  - quotas (object): New quota limits

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Tenant not found
- 400 Bad Request: Invalid tier value
- 500 Internal Server Error: Server-side error

**Tier Quotas:**
- free: 10GB storage, 1K queries/day, 10K documents
- starter: 50GB storage, 5K queries/day, 50K documents
- professional: 200GB storage, 20K queries/day, 200K documents
- enterprise: 1TB storage, 100K queries/day, 1M documents

**Use Cases:**
- Plan upgrades/downgrades
- Promotional tier changes
- Customer support
- Billing adjustments

### 12.12 Suspend Tenant (Admin)

Suspend a tenant account, preventing all API access.

**Endpoint:** `POST /admin/tenants/{tenant_id}/suspend`
**Authentication:** Required (Admin)
**Content-Type:** application/json
**Path Parameters:**
- tenant_id (string, UUID, required): Tenant identifier

**Request Body:**
- reason (string, required): Suspension reason

**Success Response (200 OK):**
- success (boolean): Always true
- message (string): Suspension confirmation
- data (object): Suspension details
  - tenant_id (string): Tenant ID
  - reason (string): Suspension reason
  - suspended_at (string, ISO 8601): Suspension timestamp

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Tenant not found
- 400 Bad Request: Missing reason
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Non-payment suspension
- Terms of service violations
- Security incidents
- Fraud prevention

### 12.13 Reactivate Tenant (Admin)

Reactivate a suspended tenant account.

**Endpoint:** `POST /admin/tenants/{tenant_id}/reactivate`
**Authentication:** Required (Admin)
**Path Parameters:**
- tenant_id (string, UUID, required): Tenant identifier

**Success Response (200 OK):**
- success (boolean): Always true
- message (string): Reactivation confirmation
- data (object): Reactivation details
  - tenant_id (string): Tenant ID
  - reactivated_at (string, ISO 8601): Reactivation timestamp

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Tenant not found
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Restoring suspended accounts
- Payment issue resolution
- Appeal approvals
- Account recovery

### 12.14 Get Tenant Activity (Admin)

Retrieve activity log for a specific tenant.

**Endpoint:** `GET /admin/tenants/{tenant_id}/activity`
**Authentication:** Required (Admin)
**Path Parameters:**
- tenant_id (string, UUID, required): Tenant identifier
**Query Parameters:**
- days (integer, optional, default: 7): Number of days to retrieve

**Success Response (200 OK):**
- success (boolean): Always true
- data (object): Activity information
  - tenant_id (string): Tenant ID
  - period_days (integer): Period analyzed
  - summary (object):
    - total_api_calls (integer): Total API calls
    - total_errors (integer): Total errors
    - error_rate (float): Error rate percentage
  - recent_activity (array): Recent activity records
    - endpoint (string): Endpoint accessed
    - method (string): HTTP method
    - status_code (integer): Response status
    - timestamp (string, ISO 8601): Request timestamp

**Error Responses:**
- 401 Unauthorized: Invalid or expired token
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Tenant not found
- 500 Internal Server Error: Server-side error

**Use Cases:**
- Tenant monitoring
- Support investigations
- Usage analysis
- Audit trails

---

## Error Response Format

All error responses follow a consistent format:

**Standard Error Response:**
- detail (string|object): Error description or detailed error information

**Detailed Error Response (for specific errors):**
- error (string): Error type
- message (string): Human-readable error message
- code (string): Error code for programmatic handling
- details (object): Additional error context

**Common HTTP Status Codes:**
- 200 OK: Successful request
- 201 Created: Resource successfully created
- 204 No Content: Successful request with no response body
- 400 Bad Request: Invalid input or malformed request
- 401 Unauthorized: Missing or invalid authentication
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Resource not found
- 409 Conflict: Resource conflict (e.g., duplicate)
- 413 Payload Too Large: Request exceeds size limits
- 415 Unsupported Media Type: Invalid content type
- 429 Too Many Requests: Rate limit exceeded
- 500 Internal Server Error: Server-side error
- 503 Service Unavailable: Service temporarily unavailable

---

## Rate Limiting

**Current Implementation:**
- No global rate limiting implemented
- Quota-based limits per tenant
- Per-minute and per-hour API call limits based on billing tier

**Recommended Production Limits:**
- 100 requests per minute per tenant
- 1,000 requests per hour per tenant
- 10,000 requests per day per tenant

**Rate Limit Headers (when implemented):**
- X-RateLimit-Limit: Request limit
- X-RateLimit-Remaining: Remaining requests
- X-RateLimit-Reset: Reset timestamp

---

## Pagination

Endpoints returning lists support pagination:

**Query Parameters:**
- skip (integer, default: 0): Number of records to skip
- limit (integer, default: 100): Maximum records to return

**Response Format:**
- Results are returned as arrays
- Total count may be included in response metadata
- Use skip and limit for pagination

---

## Versioning

**Current Version:** v1

**API Version in URL:** `/api/v1/`

**Version Strategy:**
- Major version in URL path
- Backward compatibility within major versions
- Deprecation notices for breaking changes
- Migration guides for version upgrades

---

## Support & Resources

**Interactive Documentation:**
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

**Additional Resources:**
- API Changelog: Track API updates and changes
- Migration Guides: Version upgrade instructions
- Best Practices: Recommended usage patterns
- Code Examples: Sample implementations

**Support Channels:**
- Technical Documentation: Comprehensive guides
- API Status Page: Real-time service status
- Developer Forum: Community support
- Email Support: Direct technical assistance

---

**Document Version:** 1.0
**Last Updated:** November 20, 2024
**Maintained By:** Development Team

