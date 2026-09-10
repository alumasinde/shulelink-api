-- Kenyan attendance foundation.
-- Extends existing students/enrollments/attendance tables; does not create duplicate student or daily attendance models.

ALTER TABLE students
    ADD COLUMN IF NOT EXISTS nemis_upi VARCHAR(40) NULL,
    ADD COLUMN IF NOT EXISTS residency_type ENUM('day_scholar','boarder') NOT NULL DEFAULT 'day_scholar';

CREATE UNIQUE INDEX IF NOT EXISTS uq_students_tenant_nemis_upi
    ON students (tenant_id, nemis_upi);
CREATE INDEX IF NOT EXISTS ix_students_tenant_residency
    ON students (tenant_id, residency_type, status);

CREATE TABLE IF NOT EXISTS attendance_session_types (
    id CHAR(36) NOT NULL PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    code VARCHAR(64) NOT NULL,
    name VARCHAR(120) NOT NULL,
    description VARCHAR(255) NULL,
    applies_to ENUM('all','day_scholar','boarder') NOT NULL DEFAULT 'all',
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    sort_order INT NOT NULL DEFAULT 0,
    default_start_time TIME NULL,
    default_end_time TIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_attendance_session_type (tenant_id, code),
    KEY ix_attendance_session_type_active (tenant_id, enabled, sort_order),
    CONSTRAINT fk_attendance_session_type_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT chk_attendance_session_type_times CHECK (default_end_time IS NULL OR default_start_time IS NULL OR default_end_time > default_start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_exemptions (
    id CHAR(36) NOT NULL PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    student_id CHAR(36) NOT NULL,
    exemption_type ENUM('leave','sickbay','suspension','official_duty','approved_absence') NOT NULL,
    status ENUM('pending','approved','rejected','cancelled','expired') NOT NULL DEFAULT 'pending',
    starts_at DATETIME NOT NULL,
    ends_at DATETIME NOT NULL,
    reason VARCHAR(500) NULL,
    source_type VARCHAR(64) NULL,
    source_id CHAR(36) NULL,
    approved_by_user_id CHAR(36) NULL,
    approved_at DATETIME NULL,
    created_by_user_id CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_attendance_exemption_student_window (tenant_id, student_id, status, starts_at, ends_at),
    KEY ix_attendance_exemption_source (tenant_id, source_type, source_id),
    CONSTRAINT fk_attendance_exemption_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_attendance_exemption_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT chk_attendance_exemption_window CHECK (ends_at > starts_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_outbox (
    id CHAR(36) NOT NULL PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    aggregate_type VARCHAR(80) NOT NULL,
    aggregate_id CHAR(36) NOT NULL,
    student_id CHAR(36) NULL,
    recipient VARCHAR(190) NULL,
    channel ENUM('sms','push','email','whatsapp') NOT NULL,
    payload_json JSON NOT NULL,
    status ENUM('pending','processing','sent','failed','cancelled') NOT NULL DEFAULT 'pending',
    attempts INT UNSIGNED NOT NULL DEFAULT 0,
    available_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME NULL,
    last_error VARCHAR(1000) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_attendance_outbox_event_channel (tenant_id, event_type, aggregate_id, channel),
    KEY ix_attendance_outbox_queue (status, available_at),
    KEY ix_attendance_outbox_student (tenant_id, student_id, created_at),
    CONSTRAINT fk_attendance_outbox_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_attendance_outbox_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_sync_batches (
    id CHAR(36) NOT NULL PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    device_id CHAR(36) NULL,
    client_batch_id VARCHAR(191) NOT NULL,
    source VARCHAR(32) NOT NULL DEFAULT 'teacher_mobile',
    status ENUM('received','processing','completed','partial','failed') NOT NULL DEFAULT 'received',
    request_hash CHAR(64) NOT NULL,
    received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    summary_json JSON NULL,
    UNIQUE KEY uq_attendance_sync_batch (tenant_id, client_batch_id),
    KEY ix_attendance_sync_status (tenant_id, status, received_at),
    CONSTRAINT fk_attendance_sync_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_attendance_sync_device FOREIGN KEY (device_id) REFERENCES attendance_devices(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_sync_items (
    id CHAR(36) NOT NULL PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    batch_id CHAR(36) NOT NULL,
    client_event_id VARCHAR(191) NOT NULL,
    session_id CHAR(36) NULL,
    student_id CHAR(36) NULL,
    status ENUM('pending','accepted','rejected','duplicate') NOT NULL DEFAULT 'pending',
    error_code VARCHAR(80) NULL,
    error_message VARCHAR(500) NULL,
    attendance_record_id CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_attendance_sync_item (tenant_id, batch_id, client_event_id),
    KEY ix_attendance_sync_item_batch (tenant_id, batch_id, status),
    CONSTRAINT fk_attendance_sync_item_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_attendance_sync_item_batch FOREIGN KEY (batch_id) REFERENCES attendance_sync_batches(id) ON DELETE CASCADE,
    CONSTRAINT fk_attendance_sync_item_record FOREIGN KEY (attendance_record_id) REFERENCES attendance_records(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attendance_nemis_staging (
    id CHAR(36) NOT NULL PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    academic_year_id CHAR(36) NULL,
    academic_term_id CHAR(36) NULL,
    student_id CHAR(36) NOT NULL,
    nemis_upi VARCHAR(40) NULL,
    attendance_date DATE NOT NULL,
    present_count INT UNSIGNED NOT NULL DEFAULT 0,
    absent_count INT UNSIGNED NOT NULL DEFAULT 0,
    late_count INT UNSIGNED NOT NULL DEFAULT 0,
    excused_count INT UNSIGNED NOT NULL DEFAULT 0,
    source_version VARCHAR(40) NOT NULL DEFAULT 'internal-v1',
    export_status ENUM('pending','validated','exported','failed') NOT NULL DEFAULT 'pending',
    validation_message VARCHAR(1000) NULL,
    exported_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_attendance_nemis_daily (tenant_id, student_id, attendance_date, source_version),
    KEY ix_attendance_nemis_period (tenant_id, academic_year_id, academic_term_id, attendance_date),
    KEY ix_attendance_nemis_status (tenant_id, export_status),
    CONSTRAINT fk_attendance_nemis_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_attendance_nemis_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO attendance_session_types (id, tenant_id, code, name, description, applies_to, enabled, sort_order, default_start_time, default_end_time)
SELECT UUID(), t.id, x.code, x.name, x.description, x.applies_to, 1, x.sort_order, x.start_time, x.end_time
FROM tenants t
CROSS JOIN (
    SELECT 'morning_roll_call' code, 'Morning Roll Call' name, 'Primary daily attendance check.' description, 'all' applies_to, 10 sort_order, '07:00:00' start_time, '09:00:00' end_time
    UNION ALL SELECT 'afternoon_roll_call','Afternoon Roll Call','Secondary daily attendance check.','all',20,'13:00:00','15:30:00'
    UNION ALL SELECT 'dormitory_night_check','Dormitory Night Check','Boarding accountability check.','boarder',30,'19:00:00','23:00:00'
) x;

INSERT IGNORE INTO tenant_permissions (id, tenant_id, code, name)
SELECT UUID(), t.id, p.code, p.name
FROM tenants t
CROSS JOIN (
    SELECT 'attendance.sync' code, 'Synchronize offline attendance' name
    UNION ALL SELECT 'attendance.nemis','Prepare attendance NEMIS exports'
) p;

INSERT IGNORE INTO tenant_role_permissions (role_id, permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='school_admin' AND p.code IN ('attendance.sync','attendance.nemis');

INSERT IGNORE INTO tenant_role_permissions (role_id, permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code IN ('teacher','registrar') AND p.code='attendance.sync';
