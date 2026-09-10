-- Expand the existing session type enum while preserving legacy values.
ALTER TABLE attendance_sessions
    MODIFY COLUMN session_type ENUM(
        'daily','lesson','event',
        'morning_roll_call','afternoon_roll_call','dormitory_night_check'
    ) NOT NULL;

CREATE INDEX IF NOT EXISTS ix_attendance_session_type_date
    ON attendance_sessions (tenant_id, session_type, session_date, status);
