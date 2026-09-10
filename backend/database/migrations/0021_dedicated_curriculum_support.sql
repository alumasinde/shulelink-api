-- Tenant-side companion for the central curriculum catalog migration.
-- Dedicated tenant databases intentionally do not contain platform catalog tables.
-- The provisioner skips 0022 there and applies this portable tenant schema instead.
-- CORRECTED: Removed duplicate teacher_subjects table (already created in 0015_teacher_subjects.sql)

CREATE TABLE IF NOT EXISTS tenant_curriculum_profiles (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    platform_template_id CHAR(36) NOT NULL,
    template_code VARCHAR(100) NOT NULL,
    template_version INT UNSIGNED NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    selected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    selected_by CHAR(36) NULL,
    allow_local_customization TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_tenant_curriculum_profile (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add platform_source_id for tracking tenant data provenance in dedicated databases
ALTER TABLE curriculum_frameworks ADD COLUMN IF NOT EXISTS platform_source_id CHAR(36) NULL;
ALTER TABLE curriculum_versions ADD COLUMN IF NOT EXISTS platform_source_id CHAR(36) NULL;
ALTER TABLE education_levels ADD COLUMN IF NOT EXISTS platform_source_id CHAR(36) NULL;
ALTER TABLE grades ADD COLUMN IF NOT EXISTS platform_source_id CHAR(36) NULL;
ALTER TABLE learning_areas ADD COLUMN IF NOT EXISTS platform_source_id CHAR(36) NULL;
ALTER TABLE subjects ADD COLUMN IF NOT EXISTS platform_source_id CHAR(36) NULL;
ALTER TABLE class_subjects ADD COLUMN IF NOT EXISTS platform_source_id CHAR(36) NULL;
ALTER TABLE pathways ADD COLUMN IF NOT EXISTS platform_source_id CHAR(36) NULL;
ALTER TABLE tracks ADD COLUMN IF NOT EXISTS platform_source_id CHAR(36) NULL;
ALTER TABLE subject_combinations ADD COLUMN IF NOT EXISTS platform_source_id CHAR(36) NULL;
ALTER TABLE subject_combination_subjects ADD COLUMN IF NOT EXISTS platform_source_id CHAR(36) NULL;
