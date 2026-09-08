-- Phase 4 repair: ensure existing tenants created before Phase 4
-- have the new permissions, role assignments and document types.
-- Safe to run repeatedly.

INSERT IGNORE INTO tenant_permissions (id, tenant_id, code, name)
SELECT UUID(), t.id, p.code, p.name
FROM tenants t CROSS JOIN (
    SELECT 'students.read' AS code, 'View students and guardians' AS name
    UNION ALL SELECT 'students.manage', 'Manage students and guardians'
    UNION ALL SELECT 'students.enroll', 'Enroll and place students'
    UNION ALL SELECT 'students.documents', 'Manage student documents'
) p;

INSERT IGNORE INTO tenant_role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM tenant_roles r
JOIN tenant_permissions p ON p.tenant_id = r.tenant_id
WHERE r.code = 'school_admin'
  AND p.code IN ('students.read','students.manage','students.enroll','students.documents');

INSERT IGNORE INTO tenant_role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM tenant_roles r
JOIN tenant_permissions p ON p.tenant_id = r.tenant_id
WHERE r.code = 'teacher'
  AND p.code = 'students.read';

INSERT IGNORE INTO student_document_types (id, tenant_id, code, name, is_required)
SELECT UUID(), t.id, d.code, d.name, d.is_required
FROM tenants t CROSS JOIN (
    SELECT 'birth_certificate' AS code, 'Birth Certificate' AS name, 0 AS is_required
    UNION ALL SELECT 'previous_school_report', 'Previous School Report', 0
    UNION ALL SELECT 'transfer_certificate', 'Transfer Certificate', 0
) d;
