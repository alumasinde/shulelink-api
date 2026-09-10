-- Attendance consistency guards.
-- The application performs the normal workflow; these database guards protect
-- the final write from races and direct cross-tenant writes.

DROP TRIGGER IF EXISTS bi_attendance_records_consistency;
DROP TRIGGER IF EXISTS bu_attendance_records_consistency;

CREATE TRIGGER bi_attendance_records_consistency
BEFORE INSERT ON attendance_records
FOR EACH ROW
BEGIN
    DECLARE v_session_tenant CHAR(36);
    DECLARE v_student_tenant CHAR(36);
    DECLARE v_status_tenant CHAR(36);
    DECLARE v_session_start DATETIME;
    DECLARE v_session_end DATETIME;
    DECLARE v_exemption_type VARCHAR(32);
    DECLARE v_status_code VARCHAR(64);
    DECLARE v_expected_status VARCHAR(64);

    SELECT tenant_id,
           COALESCE(scheduled_start_at, TIMESTAMP(session_date, '00:00:00')),
           COALESCE(scheduled_end_at, TIMESTAMP(session_date, '23:59:59'))
      INTO v_session_tenant, v_session_start, v_session_end
      FROM attendance_sessions
     WHERE id = NEW.session_id
     LIMIT 1;

    SELECT tenant_id
      INTO v_student_tenant
      FROM students
     WHERE id = NEW.student_id
     LIMIT 1;

    SELECT tenant_id, code
      INTO v_status_tenant, v_status_code
      FROM attendance_statuses
     WHERE id = NEW.attendance_status_id
     LIMIT 1;

    IF v_session_tenant IS NULL OR v_student_tenant IS NULL OR v_status_tenant IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Attendance record references a missing tenant-owned resource';
    END IF;

    IF v_session_tenant <> NEW.tenant_id
       OR v_student_tenant <> NEW.tenant_id
       OR v_status_tenant <> NEW.tenant_id THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Attendance record tenant mismatch';
    END IF;

    SELECT exemption_type
      INTO v_exemption_type
      FROM attendance_exemptions
     WHERE tenant_id = NEW.tenant_id
       AND student_id = NEW.student_id
       AND status = 'approved'
       AND starts_at <= v_session_start
       AND ends_at >= v_session_end
     ORDER BY CASE exemption_type
                  WHEN 'sickbay' THEN 1
                  WHEN 'leave' THEN 2
                  WHEN 'suspension' THEN 3
                  WHEN 'official_duty' THEN 4
                  ELSE 5
              END,
              starts_at DESC
     LIMIT 1;

    IF v_exemption_type IS NOT NULL THEN
        SET v_expected_status = CASE v_exemption_type
            WHEN 'leave' THEN 'on_leave'
            WHEN 'suspension' THEN 'on_leave'
            WHEN 'sickbay' THEN 'excused'
            WHEN 'official_duty' THEN 'excused'
            WHEN 'approved_absence' THEN 'excused'
            ELSE 'excused'
        END;

        IF v_status_code <> v_expected_status THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Attendance record conflicts with an approved exemption covering the full session';
        END IF;
    END IF;
END;

CREATE TRIGGER bu_attendance_records_consistency
BEFORE UPDATE ON attendance_records
FOR EACH ROW
BEGIN
    DECLARE v_session_tenant CHAR(36);
    DECLARE v_student_tenant CHAR(36);
    DECLARE v_status_tenant CHAR(36);
    DECLARE v_session_start DATETIME;
    DECLARE v_session_end DATETIME;
    DECLARE v_exemption_type VARCHAR(32);
    DECLARE v_status_code VARCHAR(64);
    DECLARE v_expected_status VARCHAR(64);

    SELECT tenant_id,
           COALESCE(scheduled_start_at, TIMESTAMP(session_date, '00:00:00')),
           COALESCE(scheduled_end_at, TIMESTAMP(session_date, '23:59:59'))
      INTO v_session_tenant, v_session_start, v_session_end
      FROM attendance_sessions
     WHERE id = NEW.session_id
     LIMIT 1;

    SELECT tenant_id
      INTO v_student_tenant
      FROM students
     WHERE id = NEW.student_id
     LIMIT 1;

    SELECT tenant_id, code
      INTO v_status_tenant, v_status_code
      FROM attendance_statuses
     WHERE id = NEW.attendance_status_id
     LIMIT 1;

    IF v_session_tenant IS NULL OR v_student_tenant IS NULL OR v_status_tenant IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Attendance record references a missing tenant-owned resource';
    END IF;

    IF v_session_tenant <> NEW.tenant_id
       OR v_student_tenant <> NEW.tenant_id
       OR v_status_tenant <> NEW.tenant_id THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Attendance record tenant mismatch';
    END IF;

    SELECT exemption_type
      INTO v_exemption_type
      FROM attendance_exemptions
     WHERE tenant_id = NEW.tenant_id
       AND student_id = NEW.student_id
       AND status = 'approved'
       AND starts_at <= v_session_start
       AND ends_at >= v_session_end
     ORDER BY CASE exemption_type
                  WHEN 'sickbay' THEN 1
                  WHEN 'leave' THEN 2
                  WHEN 'suspension' THEN 3
                  WHEN 'official_duty' THEN 4
                  ELSE 5
              END,
              starts_at DESC
     LIMIT 1;

    IF v_exemption_type IS NOT NULL THEN
        SET v_expected_status = CASE v_exemption_type
            WHEN 'leave' THEN 'on_leave'
            WHEN 'suspension' THEN 'on_leave'
            WHEN 'sickbay' THEN 'excused'
            WHEN 'official_duty' THEN 'excused'
            WHEN 'approved_absence' THEN 'excused'
            ELSE 'excused'
        END;

        IF v_status_code <> v_expected_status THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Attendance update conflicts with an approved exemption covering the full session';
        END IF;
    END IF;
END;
