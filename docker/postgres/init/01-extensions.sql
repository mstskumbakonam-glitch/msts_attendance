-- =============================================================================
-- 01-extensions.sql
-- Runs automatically on first container start (empty volume only).
-- Enables the pgvector extension required for face-embedding similarity search.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- Verify
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
    RAISE EXCEPTION 'pgvector extension failed to install';
  END IF;
END
$$;
