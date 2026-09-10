-- ShuleLink Attendance Engine — Phase D
-- Corrections, leave and sickbay approval workflow.
-- All records are tenant-scoped and all state transitions are performed by services.

ALTER TABLE attendance_exemptions
    ADD COLUMN requested_by_user_id CHAR(36) NULL,
    ADD COLUMN resolved_at DATETIME NULL;

CREATE INDEX ix_attendance_exemption_student_dates
    ON attendance_exemptions (tenant_id, student_id, starts_at, ends_at, status);

CREATE INDEX ix_attendance_exemption_workflow
    ON attendance_exemptions (tenant_id, status, created_at);

CREATE INDEX ix_attendance_correction_requester
    ON attendance_corrections (tenant_id, requested_by_user_id, requested_at);

INSERT IGNORE INTO tenant_permissions (id, tenant_id, code, name)
SELECT UUID(), t.id, p.code, p.name
FROM tenants t
CROSS JOIN (
    SELECT 'attendance.leave.manage' AS code, 'Manage attendance leave and exemptions' AS name
    UNION ALL SELECT 'attendance.sickbay.manage', 'Manage sickbay attendance exemptions'
) p;

INSERT IGNORE INTO tenant_role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM tenant_roles r
JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='school_admin' AND p.code IN ('attendance.leave.manage','attendance.sickbay.manage');

INSERT IGNORE INTO tenant_role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM tenant_roles r
JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='registrar' AND p.code='attendance.leave.manage';
