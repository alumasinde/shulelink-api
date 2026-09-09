-- Phase 5 hardening: subjects a teacher is qualified/assigned to teach.
-- A teacher may have at most two subject preferences/qualifications.
CREATE TABLE IF NOT EXISTS teacher_subjects (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    teacher_id CHAR(36) NOT NULL,
    subject_id CHAR(36) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_teacher_subject (tenant_id, teacher_id, subject_id),
    KEY ix_teacher_subjects_teacher (tenant_id, teacher_id),
    CONSTRAINT fk_teacher_subjects_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_teacher_subjects_teacher FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
    CONSTRAINT fk_teacher_subjects_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
