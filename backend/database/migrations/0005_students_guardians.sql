-- Phase 4: students, guardians, enrollment history and documents.

CREATE TABLE IF NOT EXISTS students (
    id CHAR(36) NOT NULL PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    admission_number VARCHAR(80) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100) NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NULL,
    gender ENUM('male','female','other','unspecified') NOT NULL DEFAULT 'unspecified',
    nationality VARCHAR(80) NULL,
    birth_certificate_number VARCHAR(100) NULL,
    admission_date DATE NULL,
    previous_school VARCHAR(190) NULL,
    photo_url VARCHAR(500) NULL,
    status ENUM('active','inactive','graduated','transferred','withdrawn') NOT NULL DEFAULT 'active',
    medical_notes TEXT NULL,
    emergency_notes TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_students_tenant_admission (tenant_id, admission_number),
    KEY ix_students_tenant_status (tenant_id, status),
    KEY ix_students_tenant_name (tenant_id, last_name, first_name),
    CONSTRAINT fk_students_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS guardians (
    id CHAR(36) NOT NULL PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(40) NULL,
    alternative_phone VARCHAR(40) NULL,
    email VARCHAR(190) NULL,
    address VARCHAR(255) NULL,
    occupation VARCHAR(150) NULL,
    employer VARCHAR(190) NULL,
    preferred_contact_method ENUM('phone','sms','email','whatsapp','any') NOT NULL DEFAULT 'phone',
    status ENUM('active','inactive') NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_guardians_tenant_name (tenant_id, last_name, first_name),
    KEY ix_guardians_tenant_phone (tenant_id, phone),
    CONSTRAINT fk_guardians_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS student_guardians (
    id CHAR(36) NOT NULL PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    student_id CHAR(36) NOT NULL,
    guardian_id CHAR(36) NOT NULL,
    relationship VARCHAR(80) NOT NULL,
    is_primary TINYINT(1) NOT NULL DEFAULT 0,
    is_emergency_contact TINYINT(1) NOT NULL DEFAULT 0,
    can_pick_up TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_student_guardian (student_id, guardian_id),
    KEY ix_student_guardians_tenant (tenant_id),
    KEY ix_student_guardians_guardian (guardian_id),
    CONSTRAINT fk_student_guardians_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_student_guardians_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT fk_student_guardians_guardian FOREIGN KEY (guardian_id) REFERENCES guardians(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS student_enrollments (
    id CHAR(36) NOT NULL PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    student_id CHAR(36) NOT NULL,
    academic_year_id CHAR(36) NOT NULL,
    class_level_id CHAR(36) NOT NULL,
    stream_id CHAR(36) NULL,
    enrollment_date DATE NOT NULL,
    exit_date DATE NULL,
    status ENUM('active','completed','withdrawn') NOT NULL DEFAULT 'active',
    notes VARCHAR(500) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_student_year (student_id, academic_year_id),
    KEY ix_enrollments_tenant_year (tenant_id, academic_year_id),
    KEY ix_enrollments_tenant_class (tenant_id, class_level_id),
    KEY ix_enrollments_student (student_id, enrollment_date),
    CONSTRAINT fk_enrollments_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_enrollments_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT fk_enrollments_year FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE RESTRICT,
    CONSTRAINT fk_enrollments_class FOREIGN KEY (class_level_id) REFERENCES class_levels(id) ON DELETE RESTRICT,
    CONSTRAINT fk_enrollments_stream FOREIGN KEY (stream_id) REFERENCES streams(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS student_document_types (
    id CHAR(36) NOT NULL PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    code VARCHAR(80) NOT NULL,
    name VARCHAR(150) NOT NULL,
    is_required TINYINT(1) NOT NULL DEFAULT 0,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_student_doc_type_code (tenant_id, code),
    UNIQUE KEY uq_student_doc_type_name (tenant_id, name),
    KEY ix_student_doc_types_tenant (tenant_id),
    CONSTRAINT fk_student_doc_types_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS student_documents (
    id CHAR(36) NOT NULL PRIMARY KEY,
    tenant_id CHAR(36) NOT NULL,
    student_id CHAR(36) NOT NULL,
    document_type_id CHAR(36) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_url VARCHAR(1000) NOT NULL,
    mime_type VARCHAR(120) NULL,
    file_size BIGINT UNSIGNED NULL,
    document_number VARCHAR(150) NULL,
    issued_at DATE NULL,
    expires_at DATE NULL,
    notes VARCHAR(500) NULL,
    uploaded_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY ix_student_documents_tenant_student (tenant_id, student_id),
    KEY ix_student_documents_type (document_type_id),
    CONSTRAINT fk_student_documents_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_student_documents_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT fk_student_documents_type FOREIGN KEY (document_type_id) REFERENCES student_document_types(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO tenant_permissions (id, tenant_id, code, name)
SELECT UUID(), t.id, p.code, p.name
FROM tenants t CROSS JOIN (
    SELECT 'students.read' AS code, 'View students and guardians' AS name
    UNION ALL SELECT 'students.manage', 'Manage students and guardians'
    UNION ALL SELECT 'students.enroll', 'Enroll and place students'
    UNION ALL SELECT 'students.documents', 'Manage student documents'
) AS p;

INSERT IGNORE INTO tenant_role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='school_admin' AND p.code IN ('students.read','students.manage','students.enroll','students.documents');

INSERT IGNORE INTO tenant_role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='teacher' AND p.code IN ('students.read');

INSERT IGNORE INTO student_document_types (id, tenant_id, code, name, is_required)
SELECT UUID(), t.id, d.code, d.name, d.is_required
FROM tenants t CROSS JOIN (
    SELECT 'birth_certificate' AS code, 'Birth Certificate' AS name, 0 AS is_required
    UNION ALL SELECT 'previous_school_report', 'Previous School Report', 0
    UNION ALL SELECT 'transfer_certificate', 'Transfer Certificate', 0
) AS d;
