# Multitenancy Implementation - Remaining Tasks

**Status as of:** November 17, 2025  
**Completed:** Phases 1, 2, 3, and 4 (100% complete)  
**Remaining:** Phase 5, Phase 6

---

## Phase 3: Security & Access Control ✅ COMPLETE

### 3.1 Authorization Layer ✅ COMPLETE

- [x] **Add permission checks to endpoints**
  - [x] Update app/routers/upload.py with permission checks
  - [x] Update app/routers/qdrant_upload.py with permission checks
  - [x] Update app/routers/query_router.py with permission checks
  - [x] Update app/routers/management_router.py with permission checks
  - [x] Update app/routers/db_router_v2.py with permission checks
  - [x] Update app/routers/file_router.py with permission checks
  - [x] Update app/routers/tenant_router.py with permission checks (admin endpoints already secured)
  - [x] Add @require_permission decorators where appropriate (created app/auth/decorators.py)
  - [x] Ensure all endpoints return 403 for unauthorized access
  - [x] Test each endpoint with different user roles (created test_permission_integration.py)

### 3.2 Data Security

- [x] **Set up secrets management** ✅ COMPLETE
  - [x] Choose secrets manager (HashiCorp Vault - free for development)
  - [x] Install and configure secrets manager (hvac library added)
  - [x] Migrate encryption keys to secrets manager (vault_service.py created)
  - [x] Update credential_service.py to use secrets manager (Vault integration added)
  - [x] Implement key rotation mechanism (rotate_encryption_key.py script)
  - [x] Document secrets management setup (VAULT_SETUP.md, VAULT_QUICKSTART.md)
  - [x] Test key rotation process (test_vault_integration.py created)

- [x] **Implement tenant isolation verification** ✅ COMPLETE
  - [x] Create test_tenant_isolation.py (18 comprehensive tests)
  - [x] Test Qdrant collection isolation (cross-tenant access prevention)
  - [x] Test database connection isolation
  - [x] Test file storage isolation
  - [x] Verify all queries include tenant_id filters
  - [x] Test with multiple concurrent tenants
  - [x] Document isolation test results (TENANT_ISOLATION_TEST_RESULTS.md)

### 3.3 API Security ✅ COMPLETE

- [x] **API key management** ✅ COMPLETE
  - [x] Create tenant_api_keys table migration (already existed from Phase 1)
  - [x] Create app/services/api_key_service.py
  - [x] Implement API key generation endpoint (POST /api/v1/api-keys/)
  - [x] Implement API key listing endpoint (GET /api/v1/api-keys/)
  - [x] Implement API key revocation endpoint (DELETE /api/v1/api-keys/{key_id})
  - [x] Store hashed API keys in database (bcrypt with 12 rounds)
  - [x] Implement API key validation in auth middleware
  - [x] Add API key rotation mechanism (POST /api/v1/api-keys/{key_id}/rotate)
  - [x] Support multiple keys per tenant (max 10)
  - [x] Add API key expiration dates (optional per key)
  - [x] Test API key authentication flow (14 comprehensive tests)

- [x] **Request validation** ✅ COMPLETE
  - [x] Create app/middleware/validation_middleware.py
  - [x] Add input sanitization for all text inputs
  - [x] Validate tenant_id format (UUID validation)
  - [x] Add SQL injection prevention (pattern detection)
  - [x] Validate file uploads (type whitelist, size limits)
  - [x] Add request size limits (100MB max)
  - [x] Validate JSON payloads (Pydantic models)
  - [x] Add XSS prevention for text fields
  - [x] Test with malicious inputs (included in tests)

- [x] **API usage tracking** ✅ COMPLETE
  - [x] Create migrations/004_create_api_usage_table.sql
  - [x] Create app/models/api_usage.py (in usage_tracking_service.py)
  - [x] Create app/services/usage_tracking_service.py
  - [x] Track requests per tenant per endpoint
  - [x] Log response times (with percentiles)
  - [x] Track error rates per tenant
  - [x] Create usage analytics endpoints (GET /api/v1/usage/stats, /endpoint/{path}, /export)
  - [x] Add usage export functionality

---

## Phase 4: Resource Management ✅ COMPLETE

**All tasks completed on November 17, 2025**

See `docs/PHASE_4_RESOURCE_MANAGEMENT.md` for complete documentation.
See `docs/PHASE_4_QUICK_REFERENCE.md` for quick reference.
See `PHASE_4_COMPLETE.md` for implementation summary.

### Summary of Completed Work:

- ✅ **Quotas & Limits (4.1)** - Complete quota management system with tier-based limits
- ✅ **Monitoring & Metrics (4.2)** - Comprehensive metrics collection, aggregation, and alerting
- ✅ **Cleanup & Maintenance (4.3)** - Automated cleanup and tenant data management
- ✅ **Background Scheduler** - Automated hourly, daily, and monthly tasks
- ✅ **15 new files created** - Services, routers, migrations, tests, documentation
- ✅ **Database migrations applied** - 2 new migration files
- ✅ **API endpoints** - 25+ new endpoints for resource management
- ✅ **Tests created** - Comprehensive quota service tests

---

## Phase 4: Resource Management (Week 6) - ARCHIVED

### 4.1 Quotas & Limits

- [ ] **Implement quota service**
  - [ ] Create app/services/quota_service.py
  - [ ] Implement check_query_quota(tenant_id) -> bool
  - [ ] Implement check_document_quota(tenant_id) -> bool
  - [ ] Implement check_connection_quota(tenant_id) -> bool
  - [ ] Implement get_quota_status(tenant_id) -> dict
  - [ ] Add quota configuration per tenant tier
  - [ ] Create quota exceeded exceptions

- [ ] **Add quota enforcement**
  - [ ] Add query quota check in query_router.py
  - [ ] Add document quota check in upload.py
  - [ ] Add connection quota check in db_router_v2.py
  - [ ] Return 429 with quota info when exceeded
  - [ ] Add quota headers to responses (X-RateLimit-Remaining, etc.)
  - [ ] Test quota enforcement for each resource type

- [ ] **Create quota tracking**
  - [ ] Track query counts (daily/monthly) in database
  - [ ] Track document counts per knowledge base
  - [ ] Track active database connections per tenant
  - [ ] Create tenant_quota_usage table
  - [ ] Implement real-time quota updates
  - [ ] Add quota usage caching for performance

- [ ] **Implement quota reset mechanism**
  - [ ] Create app/services/quota_reset_service.py
  - [ ] Implement daily quota reset job (runs at midnight)
  - [ ] Implement monthly quota reset job (runs on 1st)
  - [ ] Add quota reset to background scheduler
  - [ ] Log quota resets in audit logs
  - [ ] Test quota reset timing

- [ ] **Add quota management endpoints**
  - [ ] GET /api/v1/tenant/quota - view current usage and limits
  - [ ] GET /api/v1/tenant/quota/history - view usage history
  - [ ] PUT /api/v1/admin/tenant/{id}/quota - update limits (admin only)
  - [ ] POST /api/v1/admin/tenant/{id}/quota/reset - manual reset (admin only)
  - [ ] Test quota management endpoints

### 4.2 Monitoring & Metrics

- [ ] **Set up tenant metrics collection**
  - [ ] Create migrations/005_create_tenant_metrics_table.sql
  - [ ] Create app/models/tenant_metrics.py
  - [ ] Track storage usage over time (hourly snapshots)
  - [ ] Track API call counts per endpoint
  - [ ] Track query response times (avg, p50, p95, p99)
  - [ ] Track error rates per tenant
  - [ ] Track success rates per operation type

- [ ] **Implement usage tracking**
  - [ ] Create app/services/metrics_service.py
  - [ ] Log every API call with tenant context
  - [ ] Aggregate metrics hourly (background job)
  - [ ] Aggregate metrics daily (background job)
  - [ ] Calculate costs per tenant based on usage
  - [ ] Store aggregated metrics efficiently
  - [ ] Implement metrics retention policy (90 days)

- [ ] **Create monitoring endpoints**
  - [ ] GET /api/v1/tenant/metrics - tenant usage stats
  - [ ] GET /api/v1/tenant/metrics/storage - storage usage over time
  - [ ] GET /api/v1/tenant/metrics/queries - query volume and performance
  - [ ] GET /api/v1/tenant/metrics/errors - error rates and types
  - [ ] GET /api/v1/admin/metrics - system-wide metrics (admin only)
  - [ ] GET /api/v1/health/tenant/{id} - tenant health check
  - [ ] Add metrics export (CSV, JSON)

- [ ] **Set up alerting**
  - [ ] Create app/services/alerting_service.py
  - [ ] Alert on quota approaching limits (80%, 90%, 95%)
  - [ ] Alert on high error rates per tenant (>5%)
  - [ ] Alert on slow query performance (>5s avg)
  - [ ] Alert on connection pool exhaustion
  - [ ] Alert on storage approaching limits
  - [ ] Configure alert channels (email, webhook, Slack)
  - [ ] Test alerting system

- [ ] **Create tenant dashboards**
  - [ ] Design metrics visualization layout
  - [ ] Create storage usage chart (line chart over time)
  - [ ] Create query volume chart (bar chart by day)
  - [ ] Create cost breakdown chart (pie chart by resource)
  - [ ] Create error rate chart (line chart)
  - [ ] Add real-time metrics updates
  - [ ] Add date range filters
  - [ ] Add export functionality

### 4.3 Cleanup & Maintenance

- [ ] **Implement tenant deletion workflow**
  - [ ] Create app/services/tenant_cleanup.py
  - [ ] Implement delete_tenant_data(tenant_id) function
  - [ ] Delete all Qdrant collections for tenant
  - [ ] Delete all files from storage (uploads/{tenant_id}/)
  - [ ] Delete all database records (cascade delete)
  - [ ] Close all active connections
  - [ ] Create soft-delete option (mark is_active=False)
  - [ ] Add tenant deletion endpoint (DELETE /api/v1/admin/tenants/{id})
  - [ ] Add confirmation step for deletion
  - [ ] Test complete tenant deletion

- [ ] **Add automated cleanup**
  - [ ] Create app/services/automated_cleanup_service.py
  - [ ] Clean up expired sessions (older than 24 hours)
  - [ ] Remove old temporary files (older than 7 days)
  - [ ] Archive old audit logs (older than 90 days)
  - [ ] Clean up inactive connections (idle > 1 hour)
  - [ ] Schedule cleanup jobs (daily at 2 AM)
  - [ ] Add cleanup metrics and logging
  - [ ] Test cleanup service

- [ ] **Implement data retention policies**
  - [ ] Create app/config/retention_policies.py
  - [ ] Configure retention periods per data type
  - [ ] Auto-delete old query history (>90 days)
  - [ ] Archive old documents (>1 year, if configured)
  - [ ] Compress old logs (>30 days)
  - [ ] Add retention policy configuration per tenant
  - [ ] Implement data archival to cold storage
  - [ ] Test retention policies

- [ ] **Create tenant offboarding process**
  - [ ] Create app/services/tenant_offboarding.py
  - [ ] Export tenant data before deletion (JSON/ZIP)
  - [ ] Send notification email before deletion (7 days notice)
  - [ ] Provide data download link (valid for 30 days)
  - [ ] Verify complete data removal after deletion
  - [ ] Generate offboarding report
  - [ ] Add offboarding endpoint (POST /api/v1/admin/tenants/{id}/offboard)
  - [ ] Test complete offboarding workflow

---

## Phase 5: UI & User Experience (Week 7)

### 5.1 Tenant Selection & Login

- [ ] **Create login screen**
  - [ ] Update ui/app_multitenant.py with login page
  - [ ] Add tenant ID/email input field
  - [ ] Add password input field
  - [ ] Add "Remember me" checkbox
  - [ ] Add login button with loading state
  - [ ] Store credentials securely in session state
  - [ ] Add password visibility toggle
  - [ ] Add "Forgot password" link

- [ ] **Implement session management**
  - [ ] Store tenant_id in st.session_state
  - [ ] Store auth token in st.session_state
  - [ ] Add session timeout handling (30 minutes)
  - [ ] Clear session on logout
  - [ ] Add session refresh mechanism
  - [ ] Persist session across page reloads
  - [ ] Add session expiry warning

- [ ] **Create tenant switcher**
  - [ ] Add tenant selector dropdown in sidebar
  - [ ] Support users with multiple tenant access
  - [ ] Reload data on tenant switch
  - [ ] Show current tenant prominently
  - [ ] Add tenant switch confirmation dialog
  - [ ] Test multi-tenant user experience

- [ ] **Add visual tenant identification**
  - [ ] Show tenant name in header/banner
  - [ ] Add tenant logo upload and display
  - [ ] Add color-coding by tenant (optional)
  - [ ] Show tenant tier badge (free/basic/premium)
  - [ ] Add tenant ID display (for support)

- [ ] **Implement logout functionality**
  - [ ] Add logout button in sidebar
  - [ ] Clear all session state on logout
  - [ ] Redirect to login screen
  - [ ] Show logout confirmation
  - [ ] Revoke auth token on server

### 5.2 Tenant-Scoped Features

- [ ] **Update knowledge base listing**
  - [ ] Filter KBs by current tenant_id
  - [ ] Add tenant_id to all KB API calls
  - [ ] Show only tenant-owned collections
  - [ ] Update KB creation to include tenant context
  - [ ] Test KB isolation between tenants

- [ ] **Update database connections UI**
  - [ ] Filter connections by current tenant_id
  - [ ] Add tenant context to all connection API calls
  - [ ] Display connection status per tenant
  - [ ] Update connection creation with tenant context
  - [ ] Test connection isolation

- [ ] **Create usage dashboard**
  - [ ] Create new "Usage" page in UI
  - [ ] Show current storage usage (GB used / GB limit)
  - [ ] Show query count (daily/monthly)
  - [ ] Show remaining quota for each resource
  - [ ] Display usage trends (charts)
  - [ ] Add usage export button
  - [ ] Show cost estimate (if applicable)

- [ ] **Add tenant settings page**
  - [ ] Create new "Settings" page in UI
  - [ ] View tenant information (name, email, tier)
  - [ ] Update tenant name
  - [ ] Update tenant email
  - [ ] Manage API keys (list, create, revoke)
  - [ ] View billing information
  - [ ] Update notification preferences
  - [ ] Test settings updates

### 5.3 Admin Interface

- [ ] **Create admin dashboard**
  - [ ] Create ui/admin_app.py (separate admin UI)
  - [ ] Show all tenants list with status
  - [ ] Display system-wide metrics (total storage, queries, etc.)
  - [ ] Show active users count
  - [ ] Show system health indicators
  - [ ] Add search and filter for tenants
  - [ ] Add tenant quick actions

- [ ] **Implement tenant management UI**
  - [ ] Create new tenant form (name, email, tier)
  - [ ] Edit tenant settings (name, tier, quotas)
  - [ ] View tenant details (usage, users, activity)
  - [ ] Deactivate tenant (soft delete)
  - [ ] Delete tenant (with confirmation)
  - [ ] Reactivate tenant
  - [ ] Test all tenant management operations

- [ ] **Add tenant usage monitoring**
  - [ ] View per-tenant storage usage (sortable table)
  - [ ] View per-tenant query counts (sortable table)
  - [ ] View per-tenant costs (if applicable)
  - [ ] Export usage reports (CSV, PDF)
  - [ ] Add date range filters
  - [ ] Add usage alerts configuration
  - [ ] Show usage trends over time

- [ ] **Create billing management**
  - [ ] View tenant billing information
  - [ ] Update pricing tiers for tenants
  - [ ] Generate invoices (manual or automatic)
  - [ ] Track payments (if integrated)
  - [ ] Show payment history
  - [ ] Add billing alerts
  - [ ] Export billing reports

---

## Phase 6: Advanced Features (Week 8+)

### 6.1 Multi-Region Support

- [ ] **Design region architecture**
  - [ ] Define supported regions (us-east, us-west, eu-west, ap-south)
  - [ ] Map tenants to regions in database
  - [ ] Add region field to tenants table
  - [ ] Document region architecture
  - [ ] Plan data migration strategy

- [ ] **Implement region-specific Qdrant clusters**
  - [ ] Configure multiple Qdrant endpoints (one per region)
  - [ ] Update tenant_service.py to route by region
  - [ ] Add region selection during tenant creation
  - [ ] Implement region-aware collection naming
  - [ ] Test cross-region isolation

- [ ] **Support geo-distributed databases**
  - [ ] Allow tenant databases in different regions
  - [ ] Handle cross-region latency gracefully
  - [ ] Implement region-aware connection routing
  - [ ] Add region to database connection metadata
  - [ ] Test multi-region database connections

- [ ] **Add data residency compliance**
  - [ ] Ensure data stays in tenant's region
  - [ ] Add region validation on all operations
  - [ ] Document compliance features (GDPR, etc.)
  - [ ] Add region migration tool (if needed)
  - [ ] Test data residency enforcement

### 6.2 Tenant Customization

- [ ] **Custom embedding models**
  - [ ] Add embedding_model field to tenant settings
  - [ ] Allow tenant to specify embedding model (sentence-transformers, OpenAI, etc.)
  - [ ] Store model config per tenant
  - [ ] Load correct model for tenant operations
  - [ ] Test with different embedding models
  - [ ] Handle model compatibility issues

- [ ] **Custom LLM configurations**
  - [ ] Add llm_config field to tenant settings
  - [ ] Support different LLM providers per tenant (OpenAI, Gemini, Claude, etc.)
  - [ ] Store API keys per tenant (encrypted)
  - [ ] Configure model parameters per tenant (temperature, max_tokens, etc.)
  - [ ] Test with different LLM providers
  - [ ] Handle provider-specific features

- [ ] **Custom chunking strategies**
  - [ ] Add chunking_config field to tenant settings
  - [ ] Allow tenant-specific chunk sizes (256, 512, 1024 tokens)
  - [ ] Support different chunking methods (fixed, semantic, recursive)
  - [ ] Store chunking config per tenant
  - [ ] Apply chunking config during document processing
  - [ ] Test with different chunking strategies

- [ ] **Tenant branding**
  - [ ] Support custom logos (upload and storage)
  - [ ] Allow custom color schemes (primary, secondary colors)
  - [ ] Add custom domain support (CNAME configuration)
  - [ ] Support custom email templates
  - [ ] Add white-label option
  - [ ] Test branding customization

### 6.3 Billing & Metering

- [ ] **Implement usage metering**
  - [ ] Track billable events (queries, storage, API calls, documents)
  - [ ] Calculate costs based on pricing tiers
  - [ ] Store usage data for billing in database
  - [ ] Implement usage aggregation (daily, monthly)
  - [ ] Add usage export for billing systems
  - [ ] Test usage metering accuracy

- [ ] **Create billing calculation service**
  - [ ] Create app/services/billing_service.py
  - [ ] Calculate monthly costs per tenant
  - [ ] Apply pricing tier discounts
  - [ ] Generate usage summaries
  - [ ] Calculate prorated charges
  - [ ] Handle tier changes mid-month
  - [ ] Test billing calculations

- [ ] **Implement invoice generation**
  - [ ] Create invoice templates (HTML, PDF)
  - [ ] Generate PDF invoices using library (reportlab, weasyprint)
  - [ ] Email invoices to tenants automatically
  - [ ] Store invoice history in database
  - [ ] Add invoice download endpoint
  - [ ] Support multiple currencies
  - [ ] Test invoice generation

- [ ] **Add payment integration**
  - [ ] Choose payment gateway (Stripe, PayPal, etc.)
  - [ ] Integrate with payment gateway API
  - [ ] Handle payment webhooks
  - [ ] Update tenant status on successful payment
  - [ ] Handle failed payments (retry, suspend)
  - [ ] Add payment method management
  - [ ] Test payment flow end-to-end

---

## Migration Strategy - REMAINING TASKS

### Backward Compatibility

- [ ] **Implement dual-mode operation**
  - [ ] Add MULTITENANCY_ENABLED feature flag to config
  - [ ] Support legacy single-tenant mode (when flag is False)
  - [ ] Gradual endpoint migration (v1 vs v2 endpoints)
  - [ ] Test both modes

- [ ] **Implement feature flags**
  - [ ] Create app/config/feature_flags.py
  - [ ] Control multitenancy per endpoint
  - [ ] Allow gradual rollout (percentage-based)
  - [ ] Add feature flag management UI

### Data Migration

- [ ] **Phase 4: Enable authentication**
  - [ ] Require tenant_id in all requests (remove default fallback)
  - [ ] Remove default tenant access
  - [ ] Update all clients to include tenant_id
  - [ ] Test authentication enforcement

- [ ] **Phase 5: Full multitenancy**
  - [ ] Enable all multitenancy features
  - [ ] Remove legacy code paths
  - [ ] Update all documentation
  - [ ] Announce full multitenancy launch

---

## Testing & Validation - REMAINING TASKS

### Unit Tests

- [ ] Test quota enforcement (all resource types)
- [ ] Test metrics collection and aggregation
- [ ] Test cleanup services
- [ ] Test billing calculations
- [ ] Test API key management

### Integration Tests

- [ ] Test tenant isolation in Qdrant (cross-tenant queries)
- [ ] Test cross-tenant access prevention (all endpoints)
- [ ] Test database connection isolation
- [ ] Test file storage isolation
- [ ] Test API rate limiting (all tiers)
- [ ] Test quota enforcement end-to-end
- [ ] Test multi-region operations

### Performance Tests

- [ ] Load test with 100+ concurrent tenants
- [ ] Test connection pool performance under load
- [ ] Test query performance with tenant filters
- [ ] Test concurrent tenant operations
- [ ] Test metrics collection overhead
- [ ] Benchmark API response times

### Security Tests

- [ ] Penetration testing for tenant isolation
- [ ] Test authentication bypass attempts
- [ ] Test SQL injection prevention
- [ ] Test file access control
- [ ] Audit log verification
- [ ] Test API key security
- [ ] Test secrets management

---

## Documentation - REMAINING TASKS

### User Documentation

- [ ] Create tenant onboarding guide
- [ ] Create UI user guide (with screenshots)
- [ ] Create quota and billing documentation
- [ ] Create API key management guide
- [ ] Create troubleshooting guide for users

### Admin Documentation

- [ ] Create tenant management guide
- [ ] Create monitoring and alerting setup guide
- [ ] Create troubleshooting guide for admins
- [ ] Create backup and recovery procedures
- [ ] Create disaster recovery plan
- [ ] Create scaling guide

---

## Deployment Checklist - REMAINING TASKS

### Pre-Deployment

- [ ] Complete all testing phases
- [ ] Conduct security audit
- [ ] Backup production database
- [ ] Prepare rollback plan
- [ ] Review all documentation
- [ ] Train support team

### Deployment

- [ ] Deploy database migrations (in order)
- [ ] Deploy application updates (blue-green deployment)
- [ ] Configure authentication (JWT secrets, etc.)
- [ ] Enable monitoring (metrics, logs, alerts)
- [ ] Verify health checks
- [ ] Test critical paths

### Post-Deployment

- [ ] Verify tenant isolation (smoke tests)
- [ ] Monitor error rates (first 24 hours)
- [ ] Check performance metrics
- [ ] Validate authentication flow
- [ ] Test admin functions
- [ ] Collect user feedback
- [ ] Address any issues

---

## Priority Recommendations

### High Priority (Do Next)
1. Add permission checks to all existing endpoints (Phase 3.1)
2. Implement quota service and enforcement (Phase 4.1)
3. Set up monitoring and metrics (Phase 4.2)
4. Update UI for tenant-scoped features (Phase 5.2)

### Medium Priority
1. Implement API key management (Phase 3.3)
2. Add automated cleanup (Phase 4.3)
3. Create admin dashboard (Phase 5.3)
4. Implement usage metering (Phase 6.3)

### Low Priority (Future Enhancements)
1. Multi-region support (Phase 6.1)
2. Tenant customization (Phase 6.2)
3. Payment integration (Phase 6.3)
4. White-label branding

---

## Estimated Effort

| Category | Tasks | Estimated Time |
|----------|-------|----------------|
| Phase 3 Remaining | 30 tasks | 1-2 weeks |
| Phase 4 Complete | 45 tasks | 2-3 weeks |
| Phase 5 Complete | 35 tasks | 2-3 weeks |
| Phase 6 Complete | 30 tasks | 3-4 weeks |
| Testing & Validation | 25 tasks | 1-2 weeks |
| Documentation | 15 tasks | 1 week |
| **Total** | **180 tasks** | **10-15 weeks** |

---

## Summary

**Completed:** 3 phases (Foundation, Core Multitenancy, Security & Access Control)  
**Remaining:** ~180 tasks across 3.5 phases  
**Estimated Time:** 10-15 weeks for complete implementation  
**Next Steps:** Focus on Phase 3 remaining tasks, then Phase 4 (Resource Management)
