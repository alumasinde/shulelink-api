-- Phase 2: identity and multi-tenancy foundation.
-- All tenant-owned records carry tenant_id so the same schema works for shared and dedicated databases.

CREATE TABLE IF NOT EXISTS platform_users (
    id CHAR(36) NOT NULL,
    email VARCHAR(190) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status ENUM('active','suspended','disabled') NOT NULL DEFAULT 'active',
    last_login_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_platform_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS platform_roles (
    id CHAR(36) NOT NULL,
    code VARCHAR(80) NOT NULL,
    name VARCHAR(120) NOT NULL,
    description VARCHAR(255) NULL,
    is_system TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id), UNIQUE KEY uq_platform_roles_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS platform_permissions (
    id CHAR(36) NOT NULL,
    code VARCHAR(120) NOT NULL,
    name VARCHAR(150) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id), UNIQUE KEY uq_platform_permissions_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS platform_user_roles (
    platform_user_id CHAR(36) NOT NULL,
    platform_role_id CHAR(36) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (platform_user_id, platform_role_id),
    CONSTRAINT fk_pur_user FOREIGN KEY (platform_user_id) REFERENCES platform_users(id) ON DELETE CASCADE,
    CONSTRAINT fk_pur_role FOREIGN KEY (platform_role_id) REFERENCES platform_roles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS platform_role_permissions (
    platform_role_id CHAR(36) NOT NULL,
    platform_permission_id CHAR(36) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (platform_role_id, platform_permission_id),
    CONSTRAINT fk_prp_role FOREIGN KEY (platform_role_id) REFERENCES platform_roles(id) ON DELETE CASCADE,
    CONSTRAINT fk_prp_permission FOREIGN KEY (platform_permission_id) REFERENCES platform_permissions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tenants (
    id CHAR(36) NOT NULL,
    name VARCHAR(180) NOT NULL,
    slug VARCHAR(80) NOT NULL,
    status ENUM('provisioning','active','suspended','disabled') NOT NULL DEFAULT 'provisioning',
    database_mode ENUM('shared','dedicated') NOT NULL DEFAULT 'shared',
    database_host VARCHAR(255) NULL,
    database_port SMALLINT UNSIGNED NULL,
    database_name VARCHAR(190) NULL,
    database_user VARCHAR(190) NULL,
    database_password_encrypted TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_tenants_slug (slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tenant_domains (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    hostname VARCHAR(253) NOT NULL,
    is_primary TINYINT(1) NOT NULL DEFAULT 0,
    verified_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_tenant_domains_hostname (hostname),
    KEY ix_tenant_domains_tenant (tenant_id),
    CONSTRAINT fk_tenant_domains_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tenant_users (
    id CHAR(36) NOT NULL,
    email VARCHAR(190) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status ENUM('active','suspended','disabled') NOT NULL DEFAULT 'active',
    last_login_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_tenant_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tenant_memberships (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    tenant_user_id CHAR(36) NOT NULL,
    status ENUM('active','invited','suspended','revoked') NOT NULL DEFAULT 'active',
    joined_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_membership_tenant_user (tenant_id, tenant_user_id),
    KEY ix_memberships_user (tenant_user_id),
    CONSTRAINT fk_membership_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_membership_user FOREIGN KEY (tenant_user_id) REFERENCES tenant_users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tenant_roles (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    code VARCHAR(80) NOT NULL,
    name VARCHAR(120) NOT NULL,
    description VARCHAR(255) NULL,
    is_system TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_tenant_roles_code (tenant_id, code),
    CONSTRAINT fk_tenant_roles_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tenant_permissions (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    code VARCHAR(120) NOT NULL,
    name VARCHAR(150) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_tenant_permissions_code (tenant_id, code),
    CONSTRAINT fk_tenant_permissions_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tenant_membership_roles (
    membership_id CHAR(36) NOT NULL,
    role_id CHAR(36) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (membership_id, role_id),
    CONSTRAINT fk_tmr_membership FOREIGN KEY (membership_id) REFERENCES tenant_memberships(id) ON DELETE CASCADE,
    CONSTRAINT fk_tmr_role FOREIGN KEY (role_id) REFERENCES tenant_roles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tenant_role_permissions (
    role_id CHAR(36) NOT NULL,
    permission_id CHAR(36) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id),
    CONSTRAINT fk_trp_role FOREIGN KEY (role_id) REFERENCES tenant_roles(id) ON DELETE CASCADE,
    CONSTRAINT fk_trp_permission FOREIGN KEY (permission_id) REFERENCES tenant_permissions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS auth_sessions (
    id CHAR(36) NOT NULL,
    user_type ENUM('platform','tenant') NOT NULL,
    user_id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NULL,
    refresh_token_hash CHAR(64) NOT NULL,
    expires_at DATETIME NOT NULL,
    last_used_at DATETIME NULL,
    revoked_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_auth_sessions_refresh_hash (refresh_token_hash),
    KEY ix_auth_sessions_user (user_type,user_id),
    KEY ix_auth_sessions_tenant (tenant_id),
    CONSTRAINT fk_auth_sessions_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tenant_access_sessions (
    id CHAR(36) NOT NULL,
    platform_user_id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    reason VARCHAR(500) NOT NULL,
    expires_at DATETIME NOT NULL,
    revoked_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_tas_platform_user (platform_user_id),
    KEY ix_tas_tenant (tenant_id),
    CONSTRAINT fk_tas_platform_user FOREIGN KEY (platform_user_id) REFERENCES platform_users(id) ON DELETE CASCADE,
    CONSTRAINT fk_tas_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS identity_audit_log (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    actor_type ENUM('platform','tenant','system') NOT NULL,
    actor_id CHAR(36) NULL,
    tenant_id CHAR(36) NULL,
    action VARCHAR(120) NOT NULL,
    target_type VARCHAR(80) NULL,
    target_id CHAR(36) NULL,
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(500) NULL,
    metadata JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_identity_audit_tenant (tenant_id,created_at),
    KEY ix_identity_audit_actor (actor_type,actor_id,created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO platform_roles (id,code,name,description,is_system)
VALUES ('00000000-0000-0000-0000-000000000001','platform_admin','Platform Administrator','Full ShuleLink platform administration',1)
ON DUPLICATE KEY UPDATE name=VALUES(name), description=VALUES(description);

INSERT INTO platform_permissions (id,code,name)
VALUES
('00000000-0000-0000-0000-000000000101','platform.manage','Manage platform configuration'),
('00000000-0000-0000-0000-000000000102','tenants.manage','Create and manage school tenants'),
('00000000-0000-0000-0000-000000000103','tenant.access','Establish audited access to a tenant')
ON DUPLICATE KEY UPDATE name=VALUES(name);

INSERT IGNORE INTO platform_role_permissions (platform_role_id,platform_permission_id)
SELECT '00000000-0000-0000-0000-000000000001', id FROM platform_permissions;
