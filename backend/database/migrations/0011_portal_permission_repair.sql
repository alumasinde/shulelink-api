-- Repair portal roles and permissions for tenants created before portal hardening.
-- Safe to run repeatedly with INSERT IGNORE.

INSERT IGNORE INTO tenant_permissions (id,tenant_id,code,name)
SELECT UUID(),t.id,p.code,p.name FROM tenants t CROSS JOIN (
    SELECT 'portal.dashboard' code,'Access role dashboard' name
    UNION ALL SELECT 'students.self','Access own student profile'
    UNION ALL SELECT 'guardian.self','Access own guardian portal'
) p;

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='student' AND p.code IN ('portal.dashboard','students.self');

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='guardian' AND p.code IN ('portal.dashboard','guardian.self');

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code IN ('school_admin','registrar','teacher','bursar') AND p.code='portal.dashboard';
