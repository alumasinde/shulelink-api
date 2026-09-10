-- ShuleLink Attendance Engine — Phase A foundation
-- Tenant-scoped domain. Capture/rules/notifications follow in later phases.
-- IMPORTANT: attendance authorization is tenant RBAC + resource scope; these tables
-- intentionally do not trust a tenant/class/student identifier supplied by a client.

CREATE TABLE IF NOT EXISTS attendance_statuses (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    code VARCHAR(64) NOT NULL,
    name VARCHAR(120) NOT NULL,
    description VARCHAR(255) NULL,
    category ENUM('attendance','absence','leave','exception') NOT NULL DEFAULT 'attendance',
    is_system TINYINT(1) NOT NULL DEFAULT 0,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    sort_order INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_attendance_status_tenant_code (tenant_id, code),
    KEY ix_attendance_status_tenant_active (tenant_id, is_active, sort_order),
    CONSTRAINT fk_attendance_status_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_policies (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    name VARCHAR(150) NOT NULL,
    code VARCHAR(64) NOT NULL,
    description VARCHAR(255) NULL,
    scope_type ENUM('school','academic_year','term','class','stream') NOT NULL DEFAULT 'school',
    grace_period_minutes SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    effective_from DATE NULL,
    effective_to DATE NULL,
    version INT UNSIGNED NOT NULL DEFAULT 1,
    created_by_user_id CHAR(36) NULL,
    updated_by_user_id CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_attendance_policy_tenant_code (tenant_id, code),
    KEY ix_attendance_policy_scope (tenant_id, scope_type, enabled, effective_from, effective_to),
    CONSTRAINT fk_attendance_policy_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT chk_attendance_policy_dates CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from),
    CONSTRAINT chk_attendance_policy_grace CHECK (grace_period_minutes <= 1440)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_sessions (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    academic_year_id CHAR(36) NULL,
    academic_term_id CHAR(36) NULL,
    class_level_id CHAR(36) NULL,
    stream_id CHAR(36) NULL,
    timetable_entry_id CHAR(36) NULL,
    session_type ENUM('daily','lesson','event') NOT NULL,
    session_date DATE NOT NULL,
    scheduled_start_at DATETIME NULL,
    scheduled_end_at DATETIME NULL,
    actual_started_at DATETIME NULL,
    closed_at DATETIME NULL,
    status ENUM('open','closed','cancelled') NOT NULL DEFAULT 'open',
    attendance_policy_id CHAR(36) NULL,
    opened_by_user_id CHAR(36) NULL,
    closed_by_user_id CHAR(36) NULL,
    notes VARCHAR(500) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_attendance_session_tenant_date (tenant_id, session_date, status),
    KEY ix_attendance_session_roster (tenant_id, class_level_id, stream_id, session_date),
    KEY ix_attendance_session_timetable (tenant_id, timetable_entry_id, session_date),
    KEY ix_attendance_session_term (tenant_id, academic_year_id, academic_term_id, session_date),
    CONSTRAINT fk_attendance_session_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_attendance_session_policy FOREIGN KEY (attendance_policy_id) REFERENCES attendance_policies(id) ON DELETE SET NULL,
    CONSTRAINT chk_attendance_session_times CHECK (scheduled_end_at IS NULL OR scheduled_start_at IS NULL OR scheduled_end_at > scheduled_start_at),
    CONSTRAINT chk_attendance_session_actual_close CHECK (closed_at IS NULL OR actual_started_at IS NULL OR closed_at >= actual_started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_records (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    session_id CHAR(36) NOT NULL,
    student_id CHAR(36) NOT NULL,
    attendance_status_id CHAR(36) NOT NULL,
    marked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    marked_by_user_id CHAR(36) NULL,
    source ENUM('manual','teacher_mobile','rfid','biometric','nfc','qr','api','import','system') NOT NULL DEFAULT 'manual',
    late_minutes SMALLINT UNSIGNED NULL,
    remarks VARCHAR(500) NULL,
    is_correction TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_attendance_record_session_student (session_id, student_id),
    KEY ix_attendance_record_tenant_date (tenant_id, marked_at, attendance_status_id),
    KEY ix_attendance_record_student (tenant_id, student_id, marked_at),
    KEY ix_attendance_record_status (tenant_id, attendance_status_id, marked_at),
    CONSTRAINT fk_attendance_record_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_attendance_record_session FOREIGN KEY (session_id) REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_attendance_record_status FOREIGN KEY (attendance_status_id) REFERENCES attendance_statuses(id) ON DELETE RESTRICT,
    CONSTRAINT chk_attendance_record_late CHECK (late_minutes IS NULL OR late_minutes <= 1440)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_events (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    session_id CHAR(36) NULL,
    student_id CHAR(36) NULL,
    attendance_record_id CHAR(36) NULL,
    event_type ENUM('captured','status_changed','corrected','voided') NOT NULL,
    source ENUM('manual','teacher_mobile','rfid','biometric','nfc','qr','api','import','system') NOT NULL,
    occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actor_user_id CHAR(36) NULL,
    device_id CHAR(36) NULL,
    idempotency_key VARCHAR(191) NULL,
    payload_json JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_attendance_event_idempotency (tenant_id, idempotency_key),
    KEY ix_attendance_event_session (tenant_id, session_id, occurred_at),
    KEY ix_attendance_event_student (tenant_id, student_id, occurred_at),
    KEY ix_attendance_event_record (attendance_record_id, occurred_at),
    KEY ix_attendance_event_type (tenant_id, event_type, occurred_at),
    CONSTRAINT fk_attendance_event_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_attendance_event_session FOREIGN KEY (session_id) REFERENCES attendance_sessions(id) ON DELETE SET NULL,
    CONSTRAINT fk_attendance_event_record FOREIGN KEY (attendance_record_id) REFERENCES attendance_records(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_corrections (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    attendance_record_id CHAR(36) NOT NULL,
    previous_status_id CHAR(36) NULL,
    new_status_id CHAR(36) NOT NULL,
    reason VARCHAR(500) NOT NULL,
    requested_by_user_id CHAR(36) NOT NULL,
    approved_by_user_id CHAR(36) NULL,
    status ENUM('pending','approved','rejected','applied','cancelled') NOT NULL DEFAULT 'pending',
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_attendance_correction_record (tenant_id, attendance_record_id, status),
    KEY ix_attendance_correction_status (tenant_id, status, requested_at),
    CONSTRAINT fk_attendance_correction_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_attendance_correction_record FOREIGN KEY (attendance_record_id) REFERENCES attendance_records(id) ON DELETE RESTRICT,
    CONSTRAINT fk_attendance_correction_previous_status FOREIGN KEY (previous_status_id) REFERENCES attendance_statuses(id) ON DELETE RESTRICT,
    CONSTRAINT fk_attendance_correction_new_status FOREIGN KEY (new_status_id) REFERENCES attendance_statuses(id) ON DELETE RESTRICT,
    CONSTRAINT chk_attendance_correction_reason CHECK (CHAR_LENGTH(TRIM(reason)) >= 3),
    CONSTRAINT chk_attendance_correction_resolution CHECK (resolved_at IS NULL OR status IN ('approved','rejected','applied','cancelled'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_devices (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    name VARCHAR(150) NOT NULL,
    device_type ENUM('rfid','biometric','nfc','qr','kiosk','mobile') NOT NULL,
    external_identifier VARCHAR(191) NOT NULL,
    status ENUM('active','inactive','revoked') NOT NULL DEFAULT 'active',
    last_seen_at DATETIME NULL,
    metadata_json JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_attendance_device_external (tenant_id, external_identifier),
    KEY ix_attendance_device_status (tenant_id, status, device_type),
    CONSTRAINT fk_attendance_device_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_policy_versions (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    policy_id CHAR(36) NOT NULL,
    version INT UNSIGNED NOT NULL,
    policy_json JSON NOT NULL,
    created_by_user_id CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_attendance_policy_version (policy_id, version),
    KEY ix_attendance_policy_version_history (tenant_id, policy_id, created_at),
    CONSTRAINT fk_attendance_policy_version_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_attendance_policy_version_policy FOREIGN KEY (policy_id) REFERENCES attendance_policies(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Stable system status contracts are seeded independently for every tenant.
INSERT IGNORE INTO attendance_statuses (id, tenant_id, code, name, description, category, is_system, is_active, sort_order)
SELECT UUID(), t.id, s.code, s.name, s.description, s.category, 1, 1, s.sort_order
FROM tenants t
CROSS JOIN (
    SELECT 'present' AS code, 'Present' AS name, 'Student attended the session.' AS description, 'attendance' AS category, 10 AS sort_order
    UNION ALL SELECT 'absent', 'Absent', 'Student did not attend the session.', 'absence', 20
    UNION ALL SELECT 'late', 'Late', 'Student attended after the configured grace period.', 'exception', 30
    UNION ALL SELECT 'half_day', 'Half Day', 'Student attended only part of the expected attendance period.', 'exception', 40
    UNION ALL SELECT 'on_leave', 'On Leave', 'Student has approved leave covering the session.', 'leave', 50
    UNION ALL SELECT 'excused', 'Excused', 'Absence has been approved or otherwise excused.', 'leave', 60
    UNION ALL SELECT 'early_departure', 'Early Departure', 'Student left before the expected end of the session.', 'exception', 70
    UNION ALL SELECT 'not_marked', 'Not Marked', 'Attendance has not yet been recorded.', 'attendance', 80
) s;

-- Every existing tenant receives the Phase A permission catalog. Role assignment
-- is scoped to existing tenant roles and follows the established RBAC convention.
INSERT IGNORE INTO tenant_permissions (id, tenant_id, code, name)
SELECT UUID(), t.id, p.code, p.name
FROM tenants t
CROSS JOIN (
    SELECT 'attendance.read' AS code, 'View attendance' AS name
    UNION ALL SELECT 'attendance.mark', 'Mark attendance'
    UNION ALL SELECT 'attendance.edit', 'Edit attendance'
    UNION ALL SELECT 'attendance.correct', 'Request attendance corrections'
    UNION ALL SELECT 'attendance.approve', 'Approve attendance corrections'
    UNION ALL SELECT 'attendance.manage', 'Manage attendance configuration'
    UNION ALL SELECT 'attendance.reports', 'View attendance reports'
    UNION ALL SELECT 'attendance.export', 'Export attendance data'
) p;

INSERT IGNORE INTO tenant_role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM tenant_roles r
JOIN tenant_permissions p ON p.tenant_id = r.tenant_id
WHERE r.code = 'school_admin'
  AND p.code IN ('attendance.read','attendance.mark','attendance.edit','attendance.correct','attendance.approve','attendance.manage','attendance.reports','attendance.export');

INSERT IGNORE INTO tenant_role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM tenant_roles r
JOIN tenant_permissions p ON p.tenant_id = r.tenant_id
WHERE r.code = 'registrar'
  AND p.code IN ('attendance.read','attendance.mark','attendance.correct','attendance.reports','attendance.export');

INSERT IGNORE INTO tenant_role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM tenant_roles r
JOIN tenant_permissions p ON p.tenant_id = r.tenant_id
WHERE r.code = 'teacher'
  AND p.code IN ('attendance.read','attendance.mark','attendance.correct');
