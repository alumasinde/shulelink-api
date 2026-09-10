-- Timetable lessons can occupy multiple configured periods explicitly.
ALTER TABLE timetable_entries
    ADD COLUMN duration_periods SMALLINT UNSIGNED NOT NULL DEFAULT 1 AFTER period_id;

UPDATE timetable_entries SET duration_periods=2 WHERE is_double=1 AND duration_periods=1;
