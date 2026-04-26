-- ============================================================================
-- Script: 00_db_bootstrap.sql
-- Owner : TV4 (Orchestration & Setup)
-- Purpose: Bootstrap the CryptoDW-ETL PostgreSQL environment.
--          Creates the application role and database for the project.
-- Run as : a PostgreSQL SUPERUSER (e.g. `postgres`), connected to the
--          maintenance database `postgres`.
-- Idempotent: yes. Safe to re-run.
-- Usage  :
--   psql -h <host> -p <port> -U <superuser> -d postgres -f sql/00_db_bootstrap.sql
-- After this:
--   - role     : crypto_etl  (LOGIN, SUPERUSER for MVP simplicity)
--   - database : crypto_dw_etl  (OWNER = crypto_etl)
--   Schemas (staging, gold) are created later by 01_staging_ddl.sql
--   and 02_gold_ddl.sql.
-- ============================================================================

DO $bootstrap_role$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'crypto_etl'
    ) THEN
        EXECUTE
            'CREATE ROLE crypto_etl LOGIN SUPERUSER PASSWORD ''crypto_etl''';
        RAISE NOTICE 'Created role crypto_etl.';
    ELSE
        RAISE NOTICE 'Role crypto_etl already exists, skipping.';
    END IF;
END
$bootstrap_role$;

-- CREATE DATABASE cannot run inside a DO block / transaction, so we use
-- a server-side gen_random_uuid-style guard via \gexec.
SELECT 'CREATE DATABASE crypto_dw_etl OWNER crypto_etl ENCODING ''UTF8'''
WHERE NOT EXISTS (
    SELECT 1 FROM pg_catalog.pg_database WHERE datname = 'crypto_dw_etl'
)
\gexec
