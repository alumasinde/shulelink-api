-- Phase 4 hardening: per-school admission number configuration and concurrency-safe sequences.

CREATE TABLE IF NOT EXISTS admission_number_sequences (
    tenant_id CHAR(36) NOT NULL,
    sequence_key VARCHAR(40) NOT NULL,
    current_number BIGINT UNSIGNED NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (tenant_id, sequence_key),
    CONSTRAINT fk_admission_sequences_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO school_settings (id, tenant_id, setting_key, setting_value, value_type)
SELECT UUID(), t.id, 'admission_number_prefix', 'ADM', 'string'
FROM tenants t;

INSERT IGNORE INTO school_settings (id, tenant_id, setting_key, setting_value, value_type)
SELECT UUID(), t.id, 'admission_number_separator', '-', 'string'
FROM tenants t;

INSERT IGNORE INTO school_settings (id, tenant_id, setting_key, setting_value, value_type)
SELECT UUID(), t.id, 'admission_number_include_year', 'true', 'boolean'
FROM tenants t;

INSERT IGNORE INTO school_settings (id, tenant_id, setting_key, setting_value, value_type)
SELECT UUID(), t.id, 'admission_number_year_format', 'YYYY', 'string'
FROM tenants t;

INSERT IGNORE INTO school_settings (id, tenant_id, setting_key, setting_value, value_type)
SELECT UUID(), t.id, 'admission_number_padding', '4', 'integer'
FROM tenants t;

INSERT IGNORE INTO school_settings (id, tenant_id, setting_key, setting_value, value_type)
SELECT UUID(), t.id, 'admission_number_start', '1', 'integer'
FROM tenants t;

INSERT IGNORE INTO school_settings (id, tenant_id, setting_key, setting_value, value_type)
SELECT UUID(), t.id, 'admission_number_reset_yearly', 'true', 'boolean'
FROM tenants t;
