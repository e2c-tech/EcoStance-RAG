-- ============================================================
-- CREATE SUPER ADMIN USER
-- ============================================================
-- This script creates a super admin account for platform administration
--
-- Credentials:
--   Email: abhay@superadmin.com
--   Password: abhaysuper18
--   Role: super_admin
--
-- Run this script with:
--   psql -h your-host -U your-user -d your-database -f create_super_admin.sql
-- ============================================================

-- Step 1: Create Platform Administration tenant (if not exists)
INSERT INTO tenants (id, name, slug, email, billing_tier, is_active, created_at, updated_at)
VALUES (
    'platform-admin-tenant-id',
    'Platform Administration',
    'platform-admin',
    'platform@admin.internal',
    'enterprise',
    true,
    NOW(),
    NOW()
)
ON CONFLICT (slug) DO NOTHING;

-- Step 2: Create super admin user
INSERT INTO tenant_users (id, tenant_id, email, password_hash, full_name, role, is_active, created_at, updated_at)
VALUES (
    'super-admin-user-id',
    'platform-admin-tenant-id',
    'abhay@superadmin.com',
    '$2b$12$4lYl/lC/lcvd/.YwYc0bzeTchWGrIC2rc7Hp3H9cUFczMDi6y5o2i',
    'Abhay',
    'super_admin',
    true,
    NOW(),
    NOW()
)
ON CONFLICT (email) DO NOTHING;

-- ============================================================
-- SUCCESS!
-- ============================================================
-- Super admin user created successfully!
--
-- Login credentials:
--   Email: abhay@superadmin.com
--   Password: abhaysuper18
--
-- You can now login at: http://localhost:8000/docs
-- Use POST /api/v1/auth/login with these credentials
--
-- ⚠️  IMPORTANT: Change this password after first login!
-- ============================================================