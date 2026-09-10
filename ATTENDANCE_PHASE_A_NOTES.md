# Attendance Phase A

Phase A establishes the durable attendance domain model. It intentionally does not expose attendance capture endpoints yet.

## Design guarantees
- Tenant-scoped operational records carry school_id.
- Attendance records are unique per session and student.
- Event ingestion supports idempotency keys.
- Attendance history is represented as events; corrections are explicit workflows.
- Policies are versioned so historical interpretation does not depend on mutable settings.
- Device identities are scoped per school.
- System status codes are stable integration identifiers.

## Deferred
- Roll-call/session APIs
- Timetable roster resolution
- Leave integration
- Late/grace evaluation
- Notifications
- Reports/exports
- RFID/biometric/QR ingestion
- Offline synchronization

These belong to later phases and must consume the Phase A contracts rather than bypassing them.
