-- ShuleLink Attendance Engine — Phase A foundation
-- This migration creates the tenant-scoped attendance domain only.
-- Attendance capture, rules and notifications are intentionally deferred.

CREATE TABLE IF NOT EXISTS attendance_statuses (
    id CHAR(36) NOT NULL,
    code VARCHAR(64) NOT NULL,
    name VARCHAR(120) NOT NULL,
    description VARCHAR(255) NULL,
    category ENUM('attendance','absence','leave','exception') NOT NULL DEFAULT 'attendance',
    is_system TINYINT(1) NOT NULL DEFAULT 0,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    sort_order INT NOT NULL DEFAULT 0,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uq_attendance_status_code (code),
    KEY idx_attendance_status_active (is_active, sort_order)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance_policies (
    id CHAR(36) NOT NULL,
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
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uq_attendance_policy_code (code),
    KEY idx_attendance_policy_scope (scope_type, enabled, effective_from, effective_to),
    CONSTRAINT chk_attendance_policy_dates CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from),
    CONSTRAINT chk_attendance_policy_grace CHECK (grace_period_minutes <= 1440)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance_sessions (
    id CHAR(36) NOT NULL,
    school_id CHAR(36) NOT NULL,
    academic_year_id CHAR(36) NULL,
    term_id CHAR(36) NULL,
    class_id CHAR(36) NULL,
    stream_id CHAR(36) NULL,
    timetable_lesson_id CHAR(36) NULL,
    session_type ENUM('daily','lesson','event') NOT NULL,
    session_date DATE NOT NULL,
    scheduled_start_at DATETIME(6) NULL,
    scheduled_end_at DATETIME(6) NULL,
    actual_started_at DATETIME(6) NULL,
    closed_at DATETIME(6) NULL,
    status ENUM('open','closed','cancelled') NOT NULL DEFAULT 'open',
    attendance_status_policy_id CHAR(36) NULL,
    opened_by_user_id CHAR(36) NULL,
    closed_by_user_id CHAR(36) NULL,
    notes VARCHAR(500) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    KEY idx_attendance_session_school_date (school_id, session_date, status),
    KEY idx_attendance_session_roster (school_id, class_id, stream_id, session_date),
    KEY idx_attendance_session_timetable (school_id, timetable_lesson_id, session_date),
    KEY idx_attendance_session_term (school_id, academic_year_id, term_id, session_date),
    CONSTRAINT chk_attendance_session_times CHECK (scheduled_end_at IS NULL OR scheduled_start_at IS NULL OR scheduled_end_at > scheduled_start_at),
    CONSTRAINT chk_attendance_session_actual_close CHECK (closed_at IS NULL OR actual_started_at IS NULL OR closed_at >= actual_started_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance_records (
    id CHAR(36) NOT NULL,
    session_id CHAR(36) NOT NULL,
    school_id CHAR(36) NOT NULL,
    student_id CHAR(36) NOT NULL,
    attendance_status_id CHAR(36) NOT NULL,
    marked_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    marked_by_user_id CHAR(36) NULL,
    source ENUM('manual','teacher_mobile','rfid','biometric','nfc','qr','api','import','system') NOT NULL DEFAULT 'manual',
    late_minutes SMALLINT UNSIGNED NULL,
    remarks VARCHAR(500) NULL,
    is_correction TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uq_attendance_record_session_student (session_id, student_id),
    KEY idx_attendance_record_school_date (school_id, marked_at, attendance_status_id),
    KEY idx_attendance_record_student (school_id, student_id, marked_at),
    KEY idx_attendance_record_status (school_id, attendance_status_id, marked_at),
    CONSTRAINT chk_attendance_record_late CHECK (late_minutes IS NULL OR late_minutes <= 1440)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance_events (
    id CHAR(36) NOT NULL,
    school_id CHAR(36) NOT NULL,
    session_id CHAR(36) NULL,
    student_id CHAR(36) NULL,
    attendance_record_id CHAR(36) NULL,
    event_type ENUM('captured','status_changed','corrected','voided') NOT NULL,
    source ENUM('manual','teacher_mobile','rfid','biometric','nfc','qr','api','import','system') NOT NULL,
    occurred_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    actor_user_id CHAR(36) NULL,
    device_id CHAR(36) NULL,
    idempotency_key VARCHAR(191) NULL,
    payload_json JSON NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uq_attendance_event_idempotency (school_id, idempotency_key),
    KEY idx_attendance_event_session (school_id, session_id, occurred_at),
    KEY idx_attendance_event_student (school_id, student_id, occurred_at),
    KEY idx_attendance_event_record (attendance_record_id, occurred_at),
    KEY idx_attendance_event_type (school_id, event_type, occurred_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance_corrections (
    id CHAR(36) NOT NULL,
    school_id CHAR(36) NOT NULL,
    attendance_record_id CHAR(36) NOT NULL,
    previous_status_id CHAR(36) NULL,
    new_status_id CHAR(36) NOT NULL,
    reason VARCHAR(500) NOT NULL,
    requested_by_user_id CHAR(36) NOT NULL,
    approved_by_user_id CHAR(36) NULL,
    status ENUM('pending','approved','rejected','applied','cancelled') NOT NULL DEFAULT 'pending',
    requested_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    resolved_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    KEY idx_attendance_correction_record (school_id, attendance_record_id, status),
    KEY idx_attendance_correction_status (school_id, status, requested_at),
    CONSTRAINT chk_attendance_correction_reason CHECK (CHAR_LENGTH(TRIM(reason)) >= 3),
    CONSTRAINT chk_attendance_correction_resolution CHECK (resolved_at IS NULL OR status IN ('approved','rejected','applied','cancelled'))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance_devices (
    id CHAR(36) NOT NULL,
    school_id CHAR(36) NOT NULL,
    name VARCHAR(150) NOT NULL,
    device_type ENUM('rfid','biometric','nfc','qr','kiosk','mobile') NOT NULL,
    external_identifier VARCHAR(191) NOT NULL,
    status ENUM('active','inactive','revoked') NOT NULL DEFAULT 'active',
    last_seen_at DATETIME(6) NULL,
    metadata_json JSON NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uq_attendance_device_external (school_id, external_identifier),
    KEY idx_attendance_device_status (school_id, status, device_type)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance_policy_versions (
    id CHAR(36) NOT NULL,
    policy_id CHAR(36) NOT NULL,
    version INT UNSIGNED NOT NULL,
    policy_json JSON NOT NULL,
    created_by_user_id CHAR(36) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uq_attendance_policy_version (policy_id, version),
    KEY idx_attendance_policy_version_history (policy_id, created_at)
) ENGINE=InnoDB;

-- Seed the engine's immutable system statuses. IDs are generated once and
-- codes are the stable integration contract; names remain editable later.
INSERT IGNORE INTO attendance_statuses (id, code, name, description, category, is_system, is_active, sort_order)
VALUES
    (UUID(), 'present', 'Present', 'Student attended the session.', 'attendance', 1, 1, 10),
    (UUID(), 'absent', 'Absent', 'Student did not attend the session.', 'absence', 1, 1, 20),
    (UUID(), 'late', 'Late', 'Student attended after the configured grace period.', 'exception', 1, 1, 30),
    (UUID(), 'half_day', 'Half Day', 'Student attended only part of the expected attendance period.', 'exception', 1, 1, 40),
    (UUID(), 'on_leave', 'On Leave', 'Student has an approved leave covering the session.', 'leave', 1, 1, 50),
    (UUID(), 'excused', 'Excused', 'Absence has been approved or otherwise excused.', 'leave', 1, 1, 60),
    (UUID(), 'early_departure', 'Early Departure', 'Student left before the expected end of the session.', 'exception', 1, 1, 70),
    (UUID(), 'not_marked', 'Not Marked', 'Attendance has not yet been recorded.', 'attendance', 1, 1, 80);

-- Phase A permissions. Assignment to tenant roles is deliberately not done
-- here because the existing RBAC model determines role membership separately.
INSERT IGNORE INTO permissions (id, code, name)
VALUES
    (UUID(), 'attendance.read', 'View attendance'),
    (UUID(), 'attendance.mark', 'Mark attendance'),
    (UUID(), 'attendance.edit', 'Edit attendance'),
    (UUID(), 'attendance.correct', 'Request attendance corrections'),
    (UUID(), 'attendance.approve', 'Approve attendance corrections'),
    (UUID(), 'attendance.manage', 'Manage attendance configuration'),
    (UUID(), 'attendance.reports', 'View attendance reports'),
    (UUID(), 'attendance.export', 'Export attendance data');
