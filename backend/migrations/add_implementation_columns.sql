-- Migration: Add implementation system columns
-- Run this against your PostgreSQL database

-- Add implementation_profile to projects (versioned company context)
ALTER TABLE projects ADD COLUMN IF NOT EXISTS implementation_profile JSONB;

-- Add discovery_metadata to hooks (f3iche, industry from discovery)
ALTER TABLE hooks ADD COLUMN IF NOT EXISTS discovery_metadata JSONB;
