# Authentication Migration Example

This document shows how to update existing endpoints to use the new authentication system.

## Before: Endpoint Without Authentication

```python
from fastapi import APIRouter, UploadFile, File
from typing import List

router = APIRouter()

@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload files without tenant context."""
    results = []
    for file in files:
        # Process file
        results.append({
            "filename": file.filename,
            "status": "uploaded"
        })
    return {"files": results}
```

## After: Endpoint With Authentication

### Option 1: Using tenant_id only

```python
from fastapi import APIRouter, UploadFile, File, Depends
from typing import List
from app.auth.dependencies import get_tenant_id

router = APIRouter()

@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    tenant_id: str = Depends(get_tenant_id)
):
    """Upload files with tenant context."""
    results = []
    for file in files:
        # Save file to tenant-specific directory
        file_path = f"uploads/{tenant_id}/{file.filename}"
        
        # Process file with tenant context
        results.append({
            "filename": file.filename,
            "tenant_id": tenant_id,
            "status": "uploaded"
        })
    
    return {
        "tenant_id": tenant_id,
        "files": results
    }
```

### Option 2: Using full tenant object

```python
from fastapi import APIRouter, UploadFile, File, Depends
from typing import List
from app.auth.dependencies import get_current_tenant
from app.models.tenant import Tenant

router = APIRouter()

@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Upload files with full tenant context."""
    # Check tenant settings
    settings = tenant.settings or {}
    max_file_size = settings.get("max_file_size_mb", 10)
    
    results = []
    for file in files:
        # Validate file size against tenant quota
        # Save file to tenant-specific directory
        file_path = f"uploads/{tenant.id}/{file.filename}"
        
        results.append({
            "filename": file.filename,
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "status": "uploaded"
        })
    
    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "files": results
    }
```

### Option 3: With tenant validation

```python
from fastapi import APIRouter, UploadFile, File, Depends
from typing import List
from sqlalchemy.orm import Session
from app.auth.dependencies import get_tenant_id
from app.config.database import get_db
from app.services.tenant_validation import tenant_validation_service

router = APIRouter()

@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db)
):
    """Upload files with tenant validation."""
    # Validate tenant has upload permission
    tenant_validation_service.validate_tenant_permission(
        tenant_id, "upload", db
    )
    
    # Check if advanced features are enabled
    has_ocr = tenant_validation_service.check_tenant_feature_flag(
        tenant_id, "ocr_processing", db
    )
    
    results = []
    for file in files:
        # Process with tenant-specific features
        processing_options = {
            "ocr_enabled": has_ocr
        }
        
        file_path = f"uploads/{tenant_id}/{file.filename}"
        
        results.append({
            "filename": file.filename,
            "tenant_id": tenant_id,
            "processing_options": processing_options,
            "status": "uploaded"
        })
    
    return {
        "tenant_id": tenant_id,
        "files": results
    }
```

## Database Query Updates

### Before: Query Without Tenant Filter

```python
from sqlalchemy.orm import Session
from app.models.document import Document

def get_all_documents(db: Session):
    """Get all documents (no tenant isolation)."""
    return db.query(Document).all()
```

### After: Query With Tenant Filter

```python
from sqlalchemy.orm import Session
from app.models.document import Document

def get_tenant_documents(db: Session, tenant_id: str):
    """Get documents for specific tenant."""
    return db.query(Document).filter(
        Document.tenant_id == tenant_id
    ).all()
```

### Before: Insert Without Tenant

```python
from sqlalchemy.orm import Session
from app.models.document import Document

def create_document(db: Session, filename: str):
    """Create document without tenant."""
    document = Document(filename=filename)
    db.add(document)
    db.commit()
    return document
```

### After: Insert With Tenant

```python
from sqlalchemy.orm import Session
from app.models.document import Document

def create_document(db: Session, tenant_id: str, filename: str):
    """Create document with tenant context."""
    document = Document(
        tenant_id=tenant_id,
        filename=filename
    )
    db.add(document)
    db.commit()
    return document
```

## Qdrant Collection Updates

### Before: Single Collection

```python
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")

def search_documents(query: str):
    """Search in single collection."""
    results = client.search(
        collection_name="documents",
        query_vector=get_embedding(query),
        limit=10
    )
    return results
```

### After: Tenant-Specific Collections

```python
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")

def search_documents(tenant_id: str, query: str):
    """Search in tenant-specific collection."""
    collection_name = f"tenant_{tenant_id}_documents"
    
    results = client.search(
        collection_name=collection_name,
        query_vector=get_embedding(query),
        limit=10
    )
    return results
```

## File Storage Updates

### Before: Shared Directory

```python
import os

def save_file(filename: str, content: bytes):
    """Save file to shared directory."""
    file_path = f"uploads/{filename}"
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path
```

### After: Tenant-Specific Directory

```python
import os

def save_file(tenant_id: str, filename: str, content: bytes):
    """Save file to tenant-specific directory."""
    # Create tenant directory if it doesn't exist
    tenant_dir = f"uploads/{tenant_id}"
    os.makedirs(tenant_dir, exist_ok=True)
    
    # Save file
    file_path = f"{tenant_dir}/{filename}"
    with open(file_path, "wb") as f:
        f.write(content)
    
    return file_path
```

## Testing Authenticated Endpoints

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.jwt_handler import create_access_token

client = TestClient(app)

def test_upload_with_authentication():
    """Test upload endpoint with JWT token."""
    # Create test token
    token_data = {
        "tenant_id": "test-tenant-123",
        "user_id": "test-user-456"
    }
    access_token = create_access_token(token_data)
    
    # Make authenticated request
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    files = {
        "files": ("test.txt", b"test content", "text/plain")
    }
    
    response = client.post(
        "/api/v1/upload",
        headers=headers,
        files=files
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "test-tenant-123"


def test_upload_without_authentication():
    """Test upload endpoint without authentication."""
    files = {
        "files": ("test.txt", b"test content", "text/plain")
    }
    
    response = client.post(
        "/api/v1/upload",
        files=files
    )
    
    # Should return 401 Unauthorized
    assert response.status_code == 401
```

## Checklist for Migrating Endpoints

- [ ] Add `tenant_id: str = Depends(get_tenant_id)` parameter
- [ ] Update database queries to filter by tenant_id
- [ ] Update Qdrant operations to use tenant-specific collections
- [ ] Update file operations to use tenant-specific directories
- [ ] Add tenant validation if needed
- [ ] Check tenant permissions/feature flags if needed
- [ ] Update tests to include authentication
- [ ] Update API documentation
- [ ] Test with multiple tenants to ensure isolation
