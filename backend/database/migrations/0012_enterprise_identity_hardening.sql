-- Enterprise identity hardening: per-account throttling, password recovery and MFA.

CREATE TABLE IF NOT EXISTS auth_login_throttles (
    account_key CHAR(64) NOT NULL,
    user_type ENUM('platform','tenant') NOT NULL,
    failed_attempts INT UNSIGNED NOT NULL DEFAULT 0,
    first_failed_at DATETIME NULL,
    locked_until DATETIME NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (account_key),
    KEY ix_auth_login_throttles_lock (locked_until)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id CHAR(36) NOT NULL,
    user_type ENUM('platform','tenant') NOT NULL,
    user_id CHAR(36) NOT NULL,
    token_hash CHAR(64) NOT NULL,
    expires_at DATETIME NOT NULL,
    used_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_password_reset_token_hash (token_hash),
    KEY ix_password_reset_user (user_type,user_id,created_at),
    KEY ix_password_reset_expiry (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS mfa_factors (
    id CHAR(36) NOT NULL,
    user_type ENUM('platform','tenant') NOT NULL,
    user_id CHAR(36) NOT NULL,
    factor_type ENUM('totp') NOT NULL DEFAULT 'totp',
    secret_encrypted TEXT NOT NULL,
    enabled TINYINT(1) NOT NULL DEFAULT 0,
    verified_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_mfa_factor_user (user_type,user_id,factor_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS mfa_challenges (
    id CHAR(36) NOT NULL,
    user_type ENUM('platform','tenant') NOT NULL,
    user_id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NULL,
    expires_at DATETIME NOT NULL,
    attempts TINYINT UNSIGNED NOT NULL DEFAULT 0,
    used_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_mfa_challenge_expiry (expires_at),
    CONSTRAINT fk_mfa_challenge_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS mfa_recovery_codes (
    id CHAR(36) NOT NULL,
    factor_id CHAR(36) NOT NULL,
    code_hash CHAR(64) NOT NULL,
    used_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_mfa_recovery_code_hash (code_hash),
    KEY ix_mfa_recovery_factor (factor_id),
    CONSTRAINT fk_mfa_recovery_factor FOREIGN KEY (factor_id) REFERENCES mfa_factors(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_identity_audit_action_time ON identity_audit_log(action,created_at);