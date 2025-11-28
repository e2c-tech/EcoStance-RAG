# Knowledge Base Listing - Final Fix

## Problem
Knowledge bases were not showing up in the UI's "Knowledge Base Management" page after creation.

## Root Cause
The auto-formatter reverted the fix in `app/routers/management_router.py`, restoring the incorrect collection name parsing logic.

## Solution Applied
Fixed the `list_knowledge_bases()` endpoint to properly parse tenant collection names using the `TenantService.parse_collection_name()` method.

### Correct Implementation
```python
@router.get("/knowledge-bases/", response_model=List[str])
async def list_knowledge_bases(tenant_id: str = Depends(get_tenant_id)):
    """
    Lists all available knowledge bases (Qdrant collections) for the tenant.
    """
    try:
        # Get all collections and filter for tenant
        all_kbs = get_all_knowledge_bases()
        qdrant_client = get_qdrant_client()
        tenant_service = get_tenant_service(qdrant_client)
        
        # Filter collections that belong to this tenant using proper parsing
        tenant_kbs = []
        for collection_name in all_kbs:
            # Parse collection name to extract tenant_id and kb_name
            parsed = tenant_service.parse_collection_name(collection_name)
            
            # Check if this collection belongs to the current tenant
            if parsed and parsed["tenant_id"] == tenant_service._sanitize_name(tenant_id):
                # Add the KB name (not the full collection name)
                tenant_kbs.append(parsed["kb_name"])
        
        return tenant_kbs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve knowledge bases: {e}")
```

## Verification

### API Test Results
```bash
# Test script output
python test_ui_kb_listing.py

✅ SUCCESS! UI should show 1 KB(s): ['demo']
✅ Details retrieved:
   - Vectors: 6
   - Files: 1
✅ Found 1 file(s):
   - FAQs for CertifyDigital Inc..pdf: 6 chunks
```

### Manual API Test
```bash
# Login
POST http://127.0.0.1:8000/api/v1/auth/login
{"tenant_id": "default-tenant"}

# List KBs
GET http://127.0.0.1:8000/api/v1/manage/knowledge-bases/
Response: ["demo"]

# Get KB details
GET http://127.0.0.1:8000/api/v1/manage/knowledge-bases/demo/details
Response: {
  "name": "demo",
  "vectors_count": 6,
  "files_count": 1,
  ...
}
```

## How to See KBs in UI

### Option 1: Refresh the Streamlit UI
If the UI is already running, refresh the browser page (F5 or Ctrl+R).

### Option 2: Restart the Streamlit UI
```bash
# Stop the current UI process (Ctrl+C)
# Then restart:
python run_ui.py
```

### Option 3: Clear Streamlit Cache
In the Streamlit UI, click the menu (☰) in the top right and select "Clear cache", then refresh.

## Expected UI Behavior

### Dashboard Page
- Should show "📚 Knowledge Bases: 1"
- Should list "demo" under Knowledge Bases section

### Knowledge Base Management Page
- **Tab 1 (Upload & Create)**: Upload files to existing or new KBs
- **Tab 2 (Manage Knowledge Bases)**:
  - Dropdown should show "demo"
  - When selected, shows:
    - 📊 Total Vectors: 6
    - 📄 Files: 1
    - File list with "FAQs for CertifyDigital Inc..pdf" (6 chunks)

### Knowledge Base Chat Page
- Dropdown should show "demo"
- Can select and chat with the KB

## Collection Naming Reference

### Format
```
tenant_{tenant_id}_{kb_name}
```

### Examples
| Tenant ID | KB Name | Collection Name |
|-----------|---------|-----------------|
| default-tenant | demo | tenant_default-tenant_demo |
| acme-corp | products | tenant_acme-corp_products |
| acme-corp | support | tenant_acme-corp_support |

### Parsing Logic
The `TenantService.parse_collection_name()` method:
1. Splits on `_`
2. Checks first part is "tenant"
3. Extracts tenant_id (second part)
4. Extracts kb_name (remaining parts joined with `_`)

This allows KB names to contain underscores while maintaining proper parsing.

## Files Modified
- ✅ `app/routers/management_router.py` - Fixed KB listing logic (again)

## Testing Scripts
- `test_kb_management.py` - Basic KB management test
- `test_ui_kb_listing.py` - Complete UI flow test

## Current Status
- ✅ Backend API working correctly
- ✅ Returns ["demo"] for default-tenant
- ✅ KB details endpoint working
- ✅ KB files endpoint working
- ⏳ UI needs refresh to see changes

## Next Steps
1. Refresh or restart your Streamlit UI
2. Login as "default-tenant"
3. Navigate to "Knowledge Base Management"
4. You should see "demo" in the dropdown
5. Select it to see the file and manage it

## Troubleshooting

### If KB still doesn't show up:
1. Check browser console for errors (F12)
2. Verify you're logged in as "default-tenant"
3. Check the API directly:
   ```bash
   python test_ui_kb_listing.py
   ```
4. Restart both backend and frontend:
   ```bash
   # Backend (if needed)
   .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
   
   # Frontend
   python run_ui.py
   ```

### If you see authentication errors:
- Make sure the backend is running on port 8000
- Check BACKEND_URL in ui/app_multitenant.py (should be http://127.0.0.1:8000/api/v1)

### If you see empty list but API works:
- Clear Streamlit cache
- Hard refresh browser (Ctrl+Shift+R)
- Check browser network tab to see actual API responses
