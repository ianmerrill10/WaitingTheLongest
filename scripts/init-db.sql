-- ============================================================================
-- Waiting The Longest™ - Database Initialization Script
-- ============================================================================
-- Run automatically when PostgreSQL container starts for the first time.
-- Creates extensions and sets up initial configuration.
-- ============================================================================

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- Create index on common search patterns (will be applied after tables exist)
-- These are placeholder comments - actual indexes are created by SQLAlchemy/Alembic

-- Grant permissions (useful for production with restricted users)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO waiting_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO waiting_user;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialized for Waiting The Longest™';
END $$;
