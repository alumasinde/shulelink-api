-- Allow non-email identities such as student login IDs while preserving email login for staff/guardians.
ALTER TABLE tenant_users
    ADD COLUMN login_identifier VARCHAR(190) NULL AFTER email,
    ADD UNIQUE KEY uq_tenant_users_login_identifier (login_identifier);
