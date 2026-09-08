INSERT IGNORE INTO tenant_permissions (id,tenant_id,code,name)
SELECT UUID(),t.id,'accounts.manage','Provision and manage portal accounts'
FROM tenants t;

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code IN ('school_admin','registrar') AND p.code='accounts.manage';
