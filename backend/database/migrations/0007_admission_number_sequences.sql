-- Phase 4: concurrency-safe admission number sequences.
-- Keeps per-tenant counters separate and supports yearly or global sequences.

CREATE TABLE IF NOT EXISTS admission_number_sequences (
    tenant_id CHAR(36) NOT NULL,
    sequence_key VARCHAR(32) NOT NULL,
    current_number BIGINT UNSIGNED NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (tenant_id, sequence_key),
    CONSTRAINT fk_admission_sequences_tenant
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
