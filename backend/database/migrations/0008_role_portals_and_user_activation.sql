-- Phase 4/5 identity hardening: role-specific portals and secure self-activation.
-- Safe to run repeatedly.

ALTER TABLE guardians
    ADD COLUMN tenant_user_id CHAR(36) NULL,
    ADD UNIQUE KEY uq_guardians_tenant_user (tenant_id, tenant_user_id);

ALTER TABLE students
    ADD COLUMN tenant_user_id CHAR(36) NULL,
    ADD UNIQUE KEY uq_students_tenant_user (tenant_id, tenant_user_id);

CREATE TABLE IF NOT EXISTS account_activation_tokens (
    id CHAR(36) NOT NULL PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    tenant_user_id CHAR(36) NOT NULL,
    token_hash CHAR(64) NOT NULL,
    purpose ENUM('guardian','student','staff') NOT NULL,
    expires_at DATETIME NOT NULL,
    consumed_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_activation_token_hash (token_hash),
    KEY ix_activation_user (tenant_id, tenant_user_id),
    KEY ix_activation_expiry (expires_at, consumed_at),
    CONSTRAINT fk_activation_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_activation_user FOREIGN KEY (tenant_user_id) REFERENCES tenant_users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO tenant_roles (id,tenant_id,code,name,description,is_system)
SELECT UUID(),t.id,r.code,r.name,r.description,1
FROM tenants t CROSS JOIN (
    SELECT 'bursar' code,'Bursar / Finance Officer' name,'Manages fees, payments and finance workflows' description
    UNION ALL SELECT 'registrar','Registrar','Manages admissions, students, guardians and records'
    UNION ALL SELECT 'student','Student','Student self-service portal'
) r;

INSERT IGNORE INTO tenant_permissions (id,tenant_id,code,name)
SELECT UUID(),t.id,p.code,p.name
FROM tenants t CROSS JOIN (
    SELECT 'portal.dashboard' code,'Access role dashboard' name
    UNION ALL SELECT 'finance.read','View finance information'
    UNION ALL SELECT 'finance.manage','Manage finance information'
    UNION ALL SELECT 'students.self','Access own student profile'
    UNION ALL SELECT 'guardian.self','Access own guardian portal'
    UNION ALL SELECT 'account.activate','Activate a provisioned account'
) p;

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='bursar' AND p.code IN ('portal.dashboard','finance.read','finance.manage');

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='registrar' AND p.code IN ('portal.dashboard','students.read','students.manage','students.enroll','students.documents');

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='guardian' AND p.code IN ('portal.dashboard','guardian.self');

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='student' AND p.code IN ('portal.dashboard','students.self');

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='school_admin' AND p.code='portal.dashboard';

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='teacher' AND p.code='portal.dashboard';
