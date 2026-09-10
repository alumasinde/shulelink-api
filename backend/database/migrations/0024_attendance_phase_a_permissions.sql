-- Attendance permission catalog is kept separate from the attendance tables so
-- deployment can safely rerun the domain migration independently.
-- NOTE: role assignment remains the responsibility of the existing RBAC setup.
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
