-- Phase 6: dynamic platform authorization hardening.
--
-- Platform administrators are a true super-admin role: they retain access to
-- every platform permission, including permissions introduced by later
-- migrations. Other platform roles remain explicitly permission-based.
-- Safe to run repeatedly.

ALTER TABLE platform_roles
    ADD COLUMN IF NOT EXISTS is_super_admin TINYINT(1) NOT NULL DEFAULT 0;

UPDATE platform_roles
SET is_super_admin = 1
WHERE code = 'platform_admin';

-- Keep the permission catalog explicit for the existing academic settings API.
INSERT IGNORE INTO platform_permissions (id, code, name)
VALUES
    (UUID(), 'academic.settings.manage', 'Manage platform academic settings');

-- Repair existing platform administrators so the database also reflects the
-- effective permission set. Future permissions do not require another repair
-- because is_super_admin is enforced dynamically by the authorization layer.
INSERT IGNORE INTO platform_role_permissions (platform_role_id, platform_permission_id)
SELECT r.id, p.id
FROM platform_roles r
CROSS JOIN platform_permissions p
WHERE r.code = 'platform_admin';
