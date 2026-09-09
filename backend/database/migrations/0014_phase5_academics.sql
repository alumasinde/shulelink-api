-- Phase 5: academics, teachers, teaching assignments and timetable.
-- Tenant scoped; compatible with shared and dedicated tenant databases.

CREATE TABLE IF NOT EXISTS teachers (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    tenant_user_id CHAR(36) NULL,
    teacher_number VARCHAR(80) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100) NULL,
    last_name VARCHAR(100) NOT NULL,
    gender ENUM('male','female','other','unspecified') NOT NULL DEFAULT 'unspecified',
    phone VARCHAR(40) NULL,
    email VARCHAR(190) NULL,
    department_id CHAR(36) NULL,
    employment_type VARCHAR(60) NULL,
    employment_date DATE NULL,
    status ENUM('active','inactive','on_leave','terminated') NOT NULL DEFAULT 'active',
    notes TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_teachers_number (tenant_id, teacher_number),
    UNIQUE KEY uq_teachers_user (tenant_id, tenant_user_id),
    KEY ix_teachers_tenant_status (tenant_id,status),
    CONSTRAINT fk_teachers_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_teachers_user FOREIGN KEY (tenant_user_id) REFERENCES tenant_users(id) ON DELETE SET NULL,
    CONSTRAINT fk_teachers_department FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS teacher_assignments (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    teacher_id CHAR(36) NOT NULL,
    academic_year_id CHAR(36) NOT NULL,
    academic_term_id CHAR(36) NOT NULL,
    class_level_id CHAR(36) NOT NULL,
    stream_id CHAR(36) NULL,
    subject_id CHAR(36) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_teacher_assignment (tenant_id,teacher_id,academic_term_id,class_level_id,stream_id,subject_id),
    KEY ix_teacher_assignments_lookup (tenant_id,academic_year_id,academic_term_id),
    CONSTRAINT fk_ta_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_ta_teacher FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
    CONSTRAINT fk_ta_year FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
    CONSTRAINT fk_ta_term FOREIGN KEY (academic_term_id) REFERENCES academic_terms(id) ON DELETE CASCADE,
    CONSTRAINT fk_ta_class FOREIGN KEY (class_level_id) REFERENCES class_levels(id) ON DELETE CASCADE,
    CONSTRAINT fk_ta_stream FOREIGN KEY (stream_id) REFERENCES streams(id) ON DELETE SET NULL,
    CONSTRAINT fk_ta_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS timetable_rooms (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    code VARCHAR(60) NOT NULL,
    name VARCHAR(120) NOT NULL,
    capacity INT UNSIGNED NULL,
    room_type VARCHAR(80) NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_timetable_rooms_code (tenant_id,code),
    CONSTRAINT fk_timetable_rooms_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS timetable_periods (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    code VARCHAR(60) NOT NULL,
    name VARCHAR(120) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_break TINYINT(1) NOT NULL DEFAULT 0,
    sort_order SMALLINT UNSIGNED NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_timetable_periods_code (tenant_id,code),
    CONSTRAINT fk_timetable_periods_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT chk_timetable_periods_time CHECK (end_time > start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS timetable_entries (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    academic_year_id CHAR(36) NOT NULL,
    academic_term_id CHAR(36) NOT NULL,
    class_level_id CHAR(36) NOT NULL,
    stream_id CHAR(36) NULL,
    subject_id CHAR(36) NOT NULL,
    teacher_id CHAR(36) NOT NULL,
    room_id CHAR(36) NULL,
    period_id CHAR(36) NOT NULL,
    day_of_week TINYINT UNSIGNED NOT NULL,
    is_double TINYINT(1) NOT NULL DEFAULT 0,
    notes VARCHAR(500) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_timetable_class_slot (tenant_id,academic_term_id,class_level_id,stream_id,day_of_week,period_id),
    UNIQUE KEY uq_timetable_teacher_slot (tenant_id,academic_term_id,teacher_id,day_of_week,period_id),
    UNIQUE KEY uq_timetable_room_slot (tenant_id,academic_term_id,room_id,day_of_week,period_id),
    KEY ix_timetable_entries_term (tenant_id,academic_year_id,academic_term_id),
    CONSTRAINT fk_tt_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_tt_year FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
    CONSTRAINT fk_tt_term FOREIGN KEY (academic_term_id) REFERENCES academic_terms(id) ON DELETE CASCADE,
    CONSTRAINT fk_tt_class FOREIGN KEY (class_level_id) REFERENCES class_levels(id) ON DELETE CASCADE,
    CONSTRAINT fk_tt_stream FOREIGN KEY (stream_id) REFERENCES streams(id) ON DELETE SET NULL,
    CONSTRAINT fk_tt_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    CONSTRAINT fk_tt_teacher FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE RESTRICT,
    CONSTRAINT fk_tt_room FOREIGN KEY (room_id) REFERENCES timetable_rooms(id) ON DELETE SET NULL,
    CONSTRAINT fk_tt_period FOREIGN KEY (period_id) REFERENCES timetable_periods(id) ON DELETE RESTRICT,
    CONSTRAINT chk_tt_day CHECK (day_of_week BETWEEN 1 AND 7)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Phase 5 tenant permissions. Existing and future tenants receive the permissions.
INSERT IGNORE INTO tenant_permissions (id,tenant_id,code,name)
SELECT UUID(),t.id,p.code,p.name FROM tenants t CROSS JOIN (
    SELECT 'academics.read' code,'Read academic records' name
    UNION ALL SELECT 'academics.manage','Manage academic configuration'
    UNION ALL SELECT 'teachers.read','Read teacher records'
    UNION ALL SELECT 'teachers.manage','Manage teacher records'
    UNION ALL SELECT 'assignments.read','Read teaching assignments'
    UNION ALL SELECT 'assignments.manage','Manage teaching assignments'
    UNION ALL SELECT 'timetable.read','Read timetables'
    UNION ALL SELECT 'timetable.manage','Manage timetables'
    UNION ALL SELECT 'timetable.generate','Generate timetables'
) p;

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='school_admin' AND p.code IN ('academics.read','academics.manage','teachers.read','teachers.manage','assignments.read','assignments.manage','timetable.read','timetable.manage','timetable.generate');

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='registrar' AND p.code IN ('academics.read','teachers.read','teachers.manage','assignments.read','assignments.manage','timetable.read','timetable.manage');

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='teacher' AND p.code IN ('academics.read','teachers.read','assignments.read','timetable.read');
