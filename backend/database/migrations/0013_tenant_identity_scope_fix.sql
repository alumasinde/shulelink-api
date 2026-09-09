-- Tenant identities are global users with tenant memberships; identifiers must be resolved
-- in the tenant context instead of being globally unique across schools.
ALTER TABLE tenant_users
    DROP INDEX uq_tenant_users_email,
    DROP INDEX uq_tenant_users_login_identifier,
    ADD INDEX ix_tenant_users_email (email),
    ADD INDEX ix_tenant_users_login_identifier (login_identifier);
