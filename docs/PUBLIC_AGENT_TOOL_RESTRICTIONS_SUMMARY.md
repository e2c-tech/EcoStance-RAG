# Public Agent Tool Restrictions - Implementation Summary

## What Was Implemented

Added **tool-level access control** to the public agent, allowing admins to restrict which database tools customers can use via the `/api/v1/admin/public-agent/config` endpoint.

## Key Changes

### 1. Database Schema
- Added `allowed_tools` column to `public_agent_configs` table
- Default value: `["tracking", "payments", "complaints", "delivery_estimates"]`
- Migration: `010_add_allowed_tools_to_public_agent.sql`

### 2. New Service
- Created `quickship_agent/public_agent_service.py`
- Filters tools based on `allowed_tools` configuration
- Prevents unauthorized tool access

### 3. API Updates
- Updated `PUT /api/v1/admin/public-agent/config` to accept `allowed_tools` array
- Added `GET /api/v1/admin/public-agent/available-tools` to list available tool categories
- Updated `GET /api/v1/admin/public-agent/config` to return `allowed_tools`

### 4. Tool Categories

| Category | Tools | Use Case |
|----------|-------|----------|
| `tracking` | `get_shipment_status`, `track_by_tracking_number` | Track shipments |
| `customer_search` | `search_shipments_by_customer` | Search by phone/email |
| `delivery_estimates` | `get_delivery_estimate` | Get delivery dates |
| `payments` | `check_cod_payment_status` | Check payment status |
| `complaints` | `get_complaint_status` | Check complaints |

## Usage Example

### Restrict to Tracking and Payments Only

```bash
curl -X PUT http://localhost:8000/api/v1/admin/public-agent/config \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "allowed_kbs": ["policies"],
    "allowed_dbs": ["logistics-demo"],
    "allowed_tools": ["tracking", "payments"],
    "welcome_message": "Hi! How can I help you track your shipment?",
    "suggested_questions": ["Track my order", "Check payment status"],
    "branding": {
      "primary_color": "#0066CC",
      "company_name": "QuickShip"
    },
    "rate_limit": {
      "queries_per_minute": 10,
      "max_messages_per_session": 50
    },
    "features": {
      "show_sources": true,
      "allow_feedback": true,
      "show_suggested_questions": true,
      "enable_database_tools": true,
      "enable_knowledge_base": true
    }
  }'
```

### Get Available Tools

```bash
curl -X GET http://localhost:8000/api/v1/admin/public-agent/available-tools \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "tools": [
    {
      "id": "tracking",
      "name": "Shipment Tracking",
      "description": "Track shipments by ID or tracking number",
      "functions": ["get_shipment_status", "track_by_tracking_number"]
    },
    {
      "id": "customer_search",
      "name": "Customer Search",
      "description": "Search shipments by customer phone or email",
      "functions": ["search_shipments_by_customer"]
    },
    {
      "id": "delivery_estimates",
      "name": "Delivery Estimates",
      "description": "Get delivery date estimates",
      "functions": ["get_delivery_estimate"]
    },
    {
      "id": "payments",
      "name": "Payment Information",
      "description": "Check COD and payment status",
      "functions": ["check_cod_payment_status"]
    },
    {
      "id": "complaints",
      "name": "Complaint Status",
      "description": "Check complaint status for shipments",
      "functions": ["get_complaint_status"]
    }
  ]
}
```

## Security Benefits

1. **Prevents Data Leakage**: Customers can't search other customers' data if `customer_search` is disabled
2. **Granular Control**: Enable only the tools needed for customer support
3. **Sales Data Protection**: Sales analytics and internal data are never exposed
4. **Audit Trail**: All tool usage is logged

## Testing

Run the test script:
```bash
python test_tool_restrictions.py
```

Expected output:
- Test 1: 8 tools (full access)
- Test 2: 5 tools (tracking + payments + KB)
- Test 3: 4 tools (tracking + KB)
- Test 4: 2 tools (KB only)

## Frontend Integration

The admin panel should display checkboxes for each tool category:

```
Public Agent Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Database Tools:
☑ Shipment Tracking
  Track shipments by ID or tracking number

☑ Payment Information
  Check COD and payment status

☐ Customer Search
  ⚠️ May expose customer data - use with caution

☑ Delivery Estimates
  Get delivery date estimates

☑ Complaint Status
  Check complaint status for shipments
```

## Files Modified

1. `app/models/public_agent.py` - Added `allowed_tools` column
2. `app/schemas/public_agent.py` - Added `allowed_tools` to schemas
3. `app/services/public_agent_service.py` - Added `allowed_tools` to update logic
4. `app/routers/public_agent_router.py` - Added `/available-tools` endpoint, updated config endpoints
5. `quickship_agent/public_agent_service.py` - New service with tool filtering
6. `migrations/010_add_allowed_tools_to_public_agent.sql` - Migration script

## Next Steps

1. **Frontend**: Add UI for selecting allowed tools in admin panel
2. **Documentation**: Update API docs with new endpoints
3. **Testing**: Add integration tests for tool restrictions
4. **Monitoring**: Add metrics for tool usage by category

## Recommendation

For customer-facing public agents, use:
```json
{
  "allowed_tools": ["tracking", "payments"]
}
```

This provides essential customer service while protecting sensitive data.
