-- Remove the remaining school configuration ENUM so configuration types stay extensible.
ALTER TABLE school_settings MODIFY COLUMN value_type VARCHAR(30) NOT NULL DEFAULT 'string';
