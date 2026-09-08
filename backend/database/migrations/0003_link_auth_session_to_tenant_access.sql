ALTER TABLE auth_sessions
    ADD COLUMN tenant_access_session_id CHAR(36) NULL AFTER tenant_id,
    ADD KEY ix_auth_sessions_access_session (tenant_access_session_id);

ALTER TABLE auth_sessions
    ADD CONSTRAINT fk_auth_sessions_access_session
    FOREIGN KEY (tenant_access_session_id) REFERENCES tenant_access_sessions(id) ON DELETE SET NULL;
