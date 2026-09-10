-- Phase 5.1: dynamic Kenyan education/curriculum foundation.
-- Removes application-level ENUM assumptions and introduces platform defaults
-- plus tenant curriculum configuration.

ALTER TABLE teachers
    MODIFY COLUMN gender VARCHAR(30) NOT NULL DEFAULT 'unspecified',
    MODIFY COLUMN status VARCHAR(40) NOT NULL DEFAULT 'active';

ALTER TABLE subjects
    MODIFY COLUMN subject_type VARCHAR(60) NOT NULL DEFAULT 'core',
    ADD COLUMN learning_area_id CHAR(36) NULL;

CREATE TABLE IF NOT EXISTS platform_academic_settings (
    id CHAR(36) NOT NULL,
    setting_key VARCHAR(120) NOT NULL,
    setting_value LONGTEXT NULL,
    value_type VARCHAR(30) NOT NULL DEFAULT 'string',
    description VARCHAR(500) NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    updated_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_platform_academic_setting_key (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS academic_reference_values (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    category VARCHAR(80) NOT NULL,
    value_key VARCHAR(80) NOT NULL,
    label VARCHAR(160) NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_academic_reference (tenant_id,category,value_key),
    KEY ix_academic_reference_category (tenant_id,category,is_active),
    CONSTRAINT fk_academic_reference_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS curriculum_frameworks (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    code VARCHAR(80) NOT NULL,
    name VARCHAR(180) NOT NULL,
    description TEXT NULL,
    country_code VARCHAR(10) NULL,
    is_default TINYINT(1) NOT NULL DEFAULT 0,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_curriculum_framework_code (tenant_id,code),
    CONSTRAINT fk_curriculum_framework_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS curriculum_versions (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    framework_id CHAR(36) NOT NULL,
    code VARCHAR(80) NOT NULL,
    name VARCHAR(180) NOT NULL,
    effective_from DATE NULL,
    effective_to DATE NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_curriculum_version_code (tenant_id,framework_id,code),
    CONSTRAINT fk_curriculum_version_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_curriculum_version_framework FOREIGN KEY (framework_id) REFERENCES curriculum_frameworks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS education_levels (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    curriculum_version_id CHAR(36) NULL,
    code VARCHAR(80) NOT NULL,
    name VARCHAR(160) NOT NULL,
    sequence_no INT NOT NULL DEFAULT 0,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_education_level_code (tenant_id,code),
    CONSTRAINT fk_education_level_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_education_level_version FOREIGN KEY (curriculum_version_id) REFERENCES curriculum_versions(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS grades (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    education_level_id CHAR(36) NOT NULL,
    code VARCHAR(80) NOT NULL,
    name VARCHAR(160) NOT NULL,
    sequence_no INT NOT NULL DEFAULT 0,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_grade_code (tenant_id,code),
    CONSTRAINT fk_grade_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_grade_level FOREIGN KEY (education_level_id) REFERENCES education_levels(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS learning_areas (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    curriculum_version_id CHAR(36) NULL,
    code VARCHAR(80) NOT NULL,
    name VARCHAR(180) NOT NULL,
    description TEXT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_learning_area_code (tenant_id,code),
    CONSTRAINT fk_learning_area_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_learning_area_version FOREIGN KEY (curriculum_version_id) REFERENCES curriculum_versions(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE subjects
    ADD CONSTRAINT fk_subject_learning_area FOREIGN KEY (learning_area_id) REFERENCES learning_areas(id) ON DELETE SET NULL;

ALTER TABLE class_subjects
    ADD COLUMN curriculum_version_id CHAR(36) NULL,
    ADD COLUMN grade_id CHAR(36) NULL,
    ADD COLUMN requirement_type VARCHAR(60) NOT NULL DEFAULT 'required',
    ADD COLUMN weekly_periods DECIMAL(5,2) NULL,
    ADD CONSTRAINT fk_class_subject_version FOREIGN KEY (curriculum_version_id) REFERENCES curriculum_versions(id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_class_subject_grade FOREIGN KEY (grade_id) REFERENCES grades(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS pathways (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    curriculum_version_id CHAR(36) NULL,
    code VARCHAR(80) NOT NULL,
    name VARCHAR(180) NOT NULL,
    description TEXT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_pathway_code (tenant_id,code),
    CONSTRAINT fk_pathway_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_pathway_version FOREIGN KEY (curriculum_version_id) REFERENCES curriculum_versions(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tracks (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    pathway_id CHAR(36) NOT NULL,
    code VARCHAR(80) NOT NULL,
    name VARCHAR(180) NOT NULL,
    description TEXT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_track_code (tenant_id,pathway_id,code),
    CONSTRAINT fk_track_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_track_pathway FOREIGN KEY (pathway_id) REFERENCES pathways(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS subject_combinations (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    grade_id CHAR(36) NULL,
    pathway_id CHAR(36) NULL,
    track_id CHAR(36) NULL,
    code VARCHAR(100) NOT NULL,
    name VARCHAR(180) NOT NULL,
    description TEXT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_subject_combination_code (tenant_id,code),
    CONSTRAINT fk_subject_combination_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_subject_combination_grade FOREIGN KEY (grade_id) REFERENCES grades(id) ON DELETE SET NULL,
    CONSTRAINT fk_subject_combination_pathway FOREIGN KEY (pathway_id) REFERENCES pathways(id) ON DELETE SET NULL,
    CONSTRAINT fk_subject_combination_track FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS subject_combination_subjects (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    combination_id CHAR(36) NOT NULL,
    subject_id CHAR(36) NOT NULL,
    is_required TINYINT(1) NOT NULL DEFAULT 1,
    sort_order INT NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uq_combination_subject (combination_id,subject_id),
    CONSTRAINT fk_combination_subject_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_combination_subject_combination FOREIGN KEY (combination_id) REFERENCES subject_combinations(id) ON DELETE CASCADE,
    CONSTRAINT fk_combination_subject_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO platform_academic_settings (id,setting_key,setting_value,value_type,description)
VALUES
(UUID(),'academic.default_curriculum_framework','kenya_cbc','string','Default curriculum framework for newly configured schools'),
(UUID(),'academic.default_curriculum_version','kenya_cbc_current','string','Default active curriculum version'),
(UUID(),'academic.default_education_structure','[{"code":"pre_primary","name":"Pre-Primary","sequence":1},{"code":"primary","name":"Primary","sequence":2},{"code":"junior_school","name":"Junior School","sequence":3},{"code":"senior_school","name":"Senior School","sequence":4}]','json','Default education levels; schools may customize them'),
(UUID(),'academic.default_teacher_subject_limit','null','integer','Maximum teacher subject eligibility count; null means unlimited'),
(UUID(),'academic.enforce_department_subject_matching','false','boolean','Whether department membership is a validation rule for teacher subject eligibility'),
(UUID(),'academic.default_lessons_per_week','3','integer','Fallback weekly lesson count when no curriculum offering defines one'),
(UUID(),'academic.allow_double_lessons','true','boolean','Allow lessons spanning more than one timetable period'),
(UUID(),'academic.default_school_days','5','integer','Default number of teaching days per week');

INSERT IGNORE INTO academic_reference_values (id,tenant_id,category,value_key,label,sort_order)
SELECT UUID(),t.id,'teacher_gender',x.value_key,x.label,x.sort_order FROM tenants t CROSS JOIN (
    SELECT 'male' value_key,'Male' label,1 sort_order UNION ALL
    SELECT 'female','Female',2 UNION ALL SELECT 'other','Other',3 UNION ALL SELECT 'unspecified','Unspecified',4
) x;
INSERT IGNORE INTO academic_reference_values (id,tenant_id,category,value_key,label,sort_order)
SELECT UUID(),t.id,'teacher_status',x.value_key,x.label,x.sort_order FROM tenants t CROSS JOIN (
    SELECT 'active' value_key,'Active' label,1 sort_order UNION ALL
    SELECT 'inactive','Inactive',2 UNION ALL SELECT 'on_leave','On leave',3 UNION ALL SELECT 'terminated','Terminated',4
) x;
INSERT IGNORE INTO academic_reference_values (id,tenant_id,category,value_key,label,sort_order)
SELECT UUID(),t.id,'subject_requirement_type',x.value_key,x.label,x.sort_order FROM tenants t CROSS JOIN (
    SELECT 'required' value_key,'Required' label,1 sort_order UNION ALL
    SELECT 'optional','Optional',2 UNION ALL SELECT 'elective','Elective',3 UNION ALL SELECT 'co_curricular','Co-curricular',4
) x;

INSERT IGNORE INTO curriculum_frameworks (id,tenant_id,code,name,description,country_code,is_default)
SELECT UUID(),t.id,'kenya_cbc','Kenya Competency Based Curriculum','Kenya CBC/CBE curriculum framework','KE',1 FROM tenants t;
INSERT IGNORE INTO curriculum_versions (id,tenant_id,framework_id,code,name,is_active)
SELECT UUID(),f.tenant_id,f.id,'kenya_cbc_current','Current Kenya CBC curriculum',1
FROM curriculum_frameworks f WHERE f.code='kenya_cbc';
