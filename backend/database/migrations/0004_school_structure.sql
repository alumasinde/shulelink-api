-- Phase 3: school structure and academic calendar.
-- This migration is safe to retry when a previous run created the tables
-- but failed during permission seeding.

CREATE TABLE IF NOT EXISTS campuses (
    id CHAR(36) NOT NULL PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    code VARCHAR(40) NOT NULL,
    name VARCHAR(160) NOT NULL,
    address VARCHAR(255) NULL,
    phone VARCHAR(40) NULL,
    email VARCHAR(190) NULL,
    is_main TINYINT(1) NOT NULL DEFAULT 0,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_campus_tenant_code (tenant_id, code), UNIQUE KEY uq_campus_tenant_name (tenant_id, name), KEY ix_campuses_tenant (tenant_id),
    CONSTRAINT fk_campuses_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS academic_years (
    id CHAR(36) NOT NULL PRIMARY KEY, tenant_id CHAR(36) NOT NULL, name VARCHAR(80) NOT NULL, start_date DATE NOT NULL, end_date DATE NOT NULL,
    is_current TINYINT(1) NOT NULL DEFAULT 0, is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_academic_year_tenant_name (tenant_id,name), KEY ix_academic_years_tenant (tenant_id),
    CONSTRAINT fk_academic_years_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS academic_terms (
    id CHAR(36) NOT NULL PRIMARY KEY, tenant_id CHAR(36) NOT NULL, academic_year_id CHAR(36) NOT NULL, name VARCHAR(80) NOT NULL, term_number TINYINT UNSIGNED NOT NULL,
    start_date DATE NOT NULL, end_date DATE NOT NULL, is_current TINYINT(1) NOT NULL DEFAULT 0, is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_term_year_number (academic_year_id,term_number), UNIQUE KEY uq_term_year_name (academic_year_id,name), KEY ix_terms_tenant (tenant_id),
    CONSTRAINT fk_terms_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_terms_year FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS departments (
    id CHAR(36) NOT NULL PRIMARY KEY, tenant_id CHAR(36) NOT NULL, code VARCHAR(40) NOT NULL, name VARCHAR(120) NOT NULL, description VARCHAR(500) NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_department_tenant_code (tenant_id,code), UNIQUE KEY uq_department_tenant_name (tenant_id,name), KEY ix_departments_tenant (tenant_id),
    CONSTRAINT fk_departments_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS class_levels (
    id CHAR(36) NOT NULL PRIMARY KEY, tenant_id CHAR(36) NOT NULL, code VARCHAR(40) NOT NULL, name VARCHAR(100) NOT NULL, level_order INT NOT NULL DEFAULT 0,
    is_active TINYINT(1) NOT NULL DEFAULT 1, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_class_level_tenant_code (tenant_id,code), UNIQUE KEY uq_class_level_tenant_name (tenant_id,name), KEY ix_class_levels_tenant (tenant_id),
    CONSTRAINT fk_class_levels_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS streams (
    id CHAR(36) NOT NULL PRIMARY KEY, tenant_id CHAR(36) NOT NULL, class_level_id CHAR(36) NOT NULL, code VARCHAR(40) NOT NULL, name VARCHAR(100) NOT NULL, capacity INT UNSIGNED NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_stream_level_code (class_level_id,code), UNIQUE KEY uq_stream_level_name (class_level_id,name), KEY ix_streams_tenant (tenant_id),
    CONSTRAINT fk_streams_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_streams_level FOREIGN KEY (class_level_id) REFERENCES class_levels(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS subjects (
    id CHAR(36) NOT NULL PRIMARY KEY, tenant_id CHAR(36) NOT NULL, department_id CHAR(36) NULL, code VARCHAR(40) NOT NULL, name VARCHAR(120) NOT NULL, short_name VARCHAR(60) NULL,
    subject_type ENUM('core','elective','co_curricular') NOT NULL DEFAULT 'core', is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_subject_tenant_code (tenant_id,code), UNIQUE KEY uq_subject_tenant_name (tenant_id,name), KEY ix_subjects_tenant (tenant_id),
    CONSTRAINT fk_subjects_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_subjects_department FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS class_subjects (
    id CHAR(36) NOT NULL PRIMARY KEY, tenant_id CHAR(36) NOT NULL, class_level_id CHAR(36) NOT NULL, subject_id CHAR(36) NOT NULL, is_compulsory TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE KEY uq_class_subject (class_level_id,subject_id), KEY ix_class_subjects_tenant (tenant_id),
    CONSTRAINT fk_class_subjects_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_class_subjects_level FOREIGN KEY (class_level_id) REFERENCES class_levels(id) ON DELETE CASCADE,
    CONSTRAINT fk_class_subjects_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS school_settings (
    id CHAR(36) NOT NULL PRIMARY KEY, tenant_id CHAR(36) NOT NULL, setting_key VARCHAR(100) NOT NULL, setting_value TEXT NULL,
    value_type ENUM('string','integer','boolean','json') NOT NULL DEFAULT 'string', updated_by CHAR(36) NULL, updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_school_setting (tenant_id,setting_key), KEY ix_school_settings_tenant (tenant_id),
    CONSTRAINT fk_school_settings_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- MariaDB can misparse INSERT ... SELECT with a derived-table alias immediately
-- before ON DUPLICATE KEY UPDATE. The permission names are static, so INSERT
-- IGNORE gives the desired idempotent behavior without an upsert clause.
INSERT IGNORE INTO tenant_permissions (id,tenant_id,code,name)
SELECT UUID(), t.id, p.code, p.name FROM tenants t CROSS JOIN (
    SELECT 'school.structure.read' code, 'View school structure' name
    UNION ALL SELECT 'school.structure.manage','Manage school structure'
) AS p;

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='school_admin' AND p.code IN ('school.structure.read','school.structure.manage');

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='teacher' AND p.code='school.structure.read';
