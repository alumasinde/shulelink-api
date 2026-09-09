import pytest
from pydantic import ValidationError

from app.core.config import Settings


BASE = {
    "app_name": "ShuleLink",
    "app_env": "development",
    "debug": True,
    "app_version": "0.2.0",
    "api_v1_prefix": "/api/v1",
    "db_host": "127.0.0.1",
    "db_port": 3306,
    "db_name": "shulelink_test",
    "db_user": "shulelink_test",
    "db_password": "test-password",
    "db_ssl_verify": True,
    "db_pool_min_size": 1,
    "db_pool_max_size": 2,
    "db_pool_recycle_seconds": 1800,
    "db_connect_timeout_seconds": 5,
    "db_read_timeout_seconds": 10,
    "db_write_timeout_seconds": 10,
    "cors_origins": "http://localhost:5173",
    "cors_origin_regex": r"^https?://([a-z0-9-]+\.)?localhost:5173$",
    "trusted_hosts": "localhost,127.0.0.1",
    "max_request_body_bytes": 10 * 1024 * 1024,
    "log_level": "INFO",
    "rate_limit_storage_uri": "memory://",
    "rate_limit_default": "120/minute",
    "jwt_secret_key": "test-secret-key-with-at-least-32-characters",
    "jwt_algorithm": "HS256",
    "jwt_issuer": "shulelink-test",
    "jwt_audience": "shulelink-test",
    "access_token_minutes": 15,
    "refresh_token_days": 30,
    "password_min_length": 10,
    "auth_cookie_mode": False,
    "auth_cookie_secure": False,
    "auth_cookie_samesite": "lax",
    "csrf_token_bytes": 32,
    "auth_reset_return_token": True,
    "password_reset_minutes": 30,
    "mfa_challenge_minutes": 5,
    "mfa_issuer": "ShuleLink Test",
    "smtp_port": 587,
    "smtp_starttls": True,
    "password_reset_base_url": "http://localhost:5173/reset-password",
    "db_provisioner_port": 3306,
    "db_provisioner_tenant_host": "127.0.0.1",
    "platform_admin_host": "admin.localhost",
    "root_domain": "localhost",
}


def make_settings(**overrides):
    values = {**BASE, **overrides}
    return Settings(_env_file=None, **values)


def test_development_configuration_is_explicit():
    settings = make_settings()
    assert settings.app_env == "development"
    assert settings.trusted_host_list == ["127.0.0.1", "localhost"]
    assert settings.cors_origin_list == ["http://localhost:5173"]


def test_unknown_environment_is_rejected():
    with pytest.raises(ValidationError):
        make_settings(app_env="local")


def test_staging_rejects_development_security_values():
    with pytest.raises(ValidationError):
        make_settings(app_env="staging")


def test_production_requires_provisioner_and_tls():
    with pytest.raises(ValidationError):
        make_settings(
            app_env="production",
            debug=False,
            rate_limit_storage_uri="redis://redis:6379/0",
            auth_cookie_mode=True,
            auth_cookie_secure=True,
            credential_encryption_key="x" * 32,
            db_ssl_ca="/run/secrets/db-ca.pem",
            smtp_host="smtp.internal",
            smtp_username="smtp-user",
            smtp_password="smtp-password",
            smtp_from="no-reply@shulelink.co.ke",
            auth_reset_return_token=False,
        )


def test_production_accepts_complete_configuration():
    settings = make_settings(
        app_env="production",
        debug=False,
        rate_limit_storage_uri="redis://redis:6379/0",
        auth_cookie_mode=True,
        auth_cookie_secure=True,
        credential_encryption_key="x" * 32,
        db_ssl_ca="/run/secrets/db-ca.pem",
        smtp_host="smtp.internal",
        smtp_username="smtp-user",
        smtp_password="smtp-password",
        smtp_from="no-reply@shulelink.co.ke",
        auth_reset_return_token=False,
        db_provisioner_host="db-provisioner.internal",
        db_provisioner_user="provisioner",
        db_provisioner_password="provisioner-password",
        trusted_hosts="admin.shulelink.co.ke,*.shulelink.co.ke",
        cors_origins="https://admin.shulelink.co.ke",
        cors_origin_regex=r"^https://([a-z0-9-]+\.)?shulelink\.co\.ke$",
        platform_admin_host="admin.shulelink.co.ke",
        root_domain="shulelink.co.ke",
    )
    assert settings.app_env == "production"
    assert settings.trusted_host_list == ["*.shulelink.co.ke", "admin.shulelink.co.ke"]


def test_unknown_configuration_key_is_rejected():
    with pytest.raises(ValidationError):
        make_settings(UNDECLARED_CONFIGURATION_KEY="must-fail")
