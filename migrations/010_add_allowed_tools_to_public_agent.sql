-- Migration: Add allowed_tools column to public_agent_configs table
-- This allows admins to restrict which tool categories the public agent can use

-- SQLite version
ALTER TABLE public_agent_configs 
ADD COLUMN allowed_tools TEXT NOT NULL DEFAULT '["tracking", "payments", "complaints", "delivery_estimates"]';

-- Update existing records to have default allowed tools
UPDATE public_agent_configs 
SET allowed_tools = '["tracking", "payments", "complaints", "delivery_estimates"]'
WHERE allowed_tools IS NULL OR allowed_tools = '';
