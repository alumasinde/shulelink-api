CREATE TABLE IF NOT EXISTS system_metadata (
    id TINYINT UNSIGNED NOT NULL,
    system_name VARCHAR(100) NOT NULL,
    system_version VARCHAR(30) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT chk_system_metadata_singleton CHECK (id = 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO system_metadata (id, system_name, system_version)
VALUES (1, 'ShuleLink', '0.1.0')
ON DUPLICATE KEY UPDATE system_version = VALUES(system_version);
