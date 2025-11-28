# Public Agent Tool Restrictions

## Overview

The public agent now supports **tool-level restrictions** to control what data customers can access. Admins can configure which tool categories are available to the public-facing agent, ensuring customers only interact with appropriate data (e.g., tracking and payments) while keeping sensitive data (e.g., sales analytics) restricted.

## Available Tool Categories

| Category | Description | Functions |
|----------|-------------|-----------|
| `tracking` | Shipment tracking by ID or tracking number | `get_shipment_status`, `track_by_tracking_number` |
| `customer_search` | Search shipments by customer phone/email | `search_shipments_by_customer` |
| `delivery_estimates` | Get delivery date estimates | `get_delivery_estimate` |
| `payments` | Check COD and payment status | `check_cod_payment_status` |
| `complaints` | Check complaint status | `get_complaint_status` |

## Configuration

### Get Available Tools

**Endpoint:** `GET /api/v1/admin/public-agent/available-tools`

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

### Update Configuration

**Endpoint:** `PUT /api/v1/admin/public-agent/config`

**Request Body:**
```json
{
  "enabled": true,
  "allowed_kbs": ["policies", "faq"],
  "allowed_dbs": ["logistics-demo"],
  "allowed_tools": ["tracking", "payments"],
  "welcome_message": "Hi! How can I help you today?",
  "suggested_questions": [
    "Track my shipment",
    "Check payment status"
  ],
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
}
```

## Use Cases

### Customer-Facing Agent (Restricted)
Only allow customers to track shipments and check payments:

```json
{
  "allowed_tools": ["tracking", "payments"]
}
```

**What customers CAN do:**
- Track shipments by ID
- Track by tracking number
- Check COD payment status
- Check payment information

**What customers CANNOT do:**
- Search by customer phone/email (prevents data leakage)
- Access sales data
- View internal analytics
- See other customers' data

### Support Agent (Full Access)
Allow support team to access all tools:

```json
{
  "allowed_tools": ["tracking", "customer_search", "delivery_estimates", "payments", "complaints"]
}
```

### Tracking-Only Agent
Only allow shipment tracking (no payment info):

```json
{
  "allowed_tools": ["tracking", "delivery_estimates"]
}
```

## Security Benefits

1. **Data Isolation**: Customers can only access their own shipment data
2. **No Sales Data Access**: Sales reports, revenue, and analytics are never exposed
3. **Controlled Search**: Customer search can be disabled to prevent data enumeration
4. **Granular Control**: Enable/disable specific tool categories as needed
5. **Audit Trail**: All tool usage is logged for compliance

## Implementation Details

### Backend
- `PublicAgentService` in `quickship_agent/public_agent_service.py` filters tools based on `allowed_tools` config
- Tool categories are mapped to specific functions in `TOOL_CATEGORIES` dict
- Unauthorized tool access attempts are logged and rejected

### Database
- `public_agent_configs.allowed_tools` stores JSON array of allowed tool category IDs
- Default: `["tracking", "payments", "complaints", "delivery_estimates"]`

### Migration
- Migration `010_add_allowed_tools_to_public_agent.sql` adds the column
- Existing configs are updated with default allowed tools

## Testing

### Test Restricted Access
1. Configure public agent with only `["tracking"]`
2. Try to search by customer phone - should be rejected
3. Try to track by shipment ID - should work

### Test Full Access
1. Configure with all tool categories
2. All functions should be available

## Frontend Integration

The admin panel should display:
1. List of available tool categories (from `/available-tools`)
2. Checkboxes to enable/disable each category
3. Description of what each category allows
4. Warning when disabling critical tools (e.g., tracking)

Example UI:
```
☑ Shipment Tracking
  Track shipments by ID or tracking number

☑ Payment Information
  Check COD and payment status

☐ Customer Search
  Search shipments by phone/email (may expose customer data)

☑ Delivery Estimates
  Get delivery date estimates

☑ Complaint Status
  Check complaint status for shipments
```

## Best Practices

1. **Start Restrictive**: Begin with minimal tools and add as needed
2. **Customer-Facing**: Only enable `tracking` and `payments` for public agents
3. **Internal Use**: Enable all tools for authenticated support agents
4. **Regular Review**: Audit which tools are being used and adjust accordingly
5. **Documentation**: Keep customers informed about what the agent can help with

## Future Enhancements

- Row-level security (filter by customer ID automatically)
- Time-based restrictions (disable certain tools during peak hours)
- Rate limiting per tool category
- Custom tool categories per tenant
- Tool usage analytics and recommendations
