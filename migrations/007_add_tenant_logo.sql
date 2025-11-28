-- Migration: Add logo fields to tenants table
-- Date: 2025-11-17
-- Description: Add logo_url and logo_filename columns for tenant branding

-- Add logo fields
ALTER TABLE tenants ADD COLUMN logo_url VARCHAR(500);
ALTER TABLE tenants ADD COLUMN logo_filename VARCHAR(255);

-- Create index for faster lookups
CREATE INDEX idx_tenants_logo_filename ON tenants(logo_filename);
