-- Emergency: Clean old migration records to allow corrected migrations to run
-- Run this in the database directly if migrations fail due to version conflicts

-- Check what's currently applied:
SELECT version, filename FROM schema_migrations ORDER BY version;

-- If you see old 0015/0016/etc entries with wrong filenames, delete 0015 onwards:
DELETE FROM schema_migrations WHERE version >= 15;

-- Verify:
SELECT version, filename FROM schema_migrations ORDER BY version;
