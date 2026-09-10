-- Remove remaining database ENUM types. Values remain data and can be managed
-- through reference/configuration tables instead of being compiled into schema.

ALTER TABLE platform_users MODIFY COLUMN status VARCHAR(40) NOT NULL DEFAULT 'active';
ALTER TABLE tenants MODIFY COLUMN status VARCHAR(40) NOT NULL DEFAULT 'provisioning', MODIFY COLUMN database_mode VARCHAR(30) NOT NULL DEFAULT 'shared';
ALTER TABLE tenant_users MODIFY COLUMN status VARCHAR(40) NOT NULL DEFAULT 'active';
ALTER TABLE tenant_memberships MODIFY COLUMN status VARCHAR(40) NOT NULL DEFAULT 'active';
ALTER TABLE auth_sessions MODIFY COLUMN user_type VARCHAR(30) NOT NULL;
ALTER TABLE identity_audit_log MODIFY COLUMN actor_type VARCHAR(30) NOT NULL;
ALTER TABLE students MODIFY COLUMN gender VARCHAR(30) NOT NULL DEFAULT 'unspecified', MODIFY COLUMN status VARCHAR(40) NOT NULL DEFAULT 'active';
ALTER TABLE guardians MODIFY COLUMN preferred_contact_method VARCHAR(40) NOT NULL DEFAULT 'phone', MODIFY COLUMN status VARCHAR(40) NOT NULL DEFAULT 'active';
ALTER TABLE student_enrollments MODIFY COLUMN status VARCHAR(40) NOT NULL DEFAULT 'active';
ALTER TABLE account_activation_tokens MODIFY COLUMN purpose VARCHAR(40) NOT NULL;
