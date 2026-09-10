from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "staging", "production"]


class Settings(BaseSettings):
    app_name: str
    app_env: Environment
    debug: bool
    app_version: str
    api_v1_prefix: str

    db_host: str
    db_port: int = Field(ge=1, le=65535)
    db_name: str
    db_user: str
    db_password: str
    db_ssl_ca: str | None = None
    db_ssl_verify: bool
    db_pool_min_size: int = Field(ge=1)
    db_pool_max_size: int = Field(ge=1)
    db_tenant_pool_min_size: int = Field(ge=1)
    db_tenant_pool_max_size: int = Field(ge=1)
    db_max_dedicated_tenant_pools: int = Field(ge=1)
    db_pool_recycle_seconds: int = Field(ge=60)
    db_connect_timeout_seconds: int = Field(ge=1, le=60)
    db_read_timeout_seconds: int = Field(ge=1, le=300)
    db_write_timeout_seconds: int = Field(ge=1, le=300)

    cors_origins: str
    cors_origin_regex: str | None = None
    trusted_hosts: str
    max_request_body_bytes: int = Field(ge=1024)
    log_level: str
    rate_limit_storage_uri: str
    rate_limit_default: str

    jwt_secret_key: str
    jwt_algorithm: str
    jwt_issuer: str
    jwt_audience: str
    access_token_minutes: int = Field(ge=5, le=60)
    refresh_token_days: int = Field(ge=1, le=90)
    password_min_length: int = Field(ge=8, le=128)

    auth_cookie_mode: bool
    auth_cookie_secure: bool
    auth_cookie_samesite: str
    csrf_token_bytes: int = Field(ge=16, le=64)
    auth_reset_return_token: bool
    password_reset_minutes: int = Field(ge=5, le=120)
    mfa_challenge_minutes: int = Field(ge=1, le=15)
    mfa_issuer: str
    credential_encryption_key: str | None = None

    smtp_host: str | None = None
    smtp_port: int = Field(ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_starttls: bool
    password_reset_base_url: str

    db_provisioner_host: str | None = None
    db_provisioner_port: int = Field(ge=1, le=65535)
    db_provisioner_user: str | None = None
    db_provisioner_password: str | None = None
    db_provisioner_tenant_host: str

    platform_admin_host: str
    root_domain: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        case_sensitive=False,
    )

    @model_validator(mode="after")
    def validate_runtime(self):
        if self.db_pool_max_size < self.db_pool_min_size:
            raise ValueError("DB_POOL_MAX_SIZE must be greater than or equal to DB_POOL_MIN_SIZE")
        if self.db_tenant_pool_max_size < self.db_tenant_pool_min_size:
            raise ValueError(
                "DB_TENANT_POOL_MAX_SIZE must be greater than or equal to DB_TENANT_POOL_MIN_SIZE"
            )
        if self.auth_cookie_samesite.lower() not in {"lax", "strict", "none"}:
            raise ValueError("AUTH_COOKIE_SAMESITE must be lax, strict or none")
        if self.auth_cookie_samesite.lower() == "none" and not self.auth_cookie_secure:
            raise ValueError("AUTH_COOKIE_SECURE must be true when SameSite=None")
        if not self.cors_origin_list and not self.cors_origin_regex:
            raise ValueError("CORS_ORIGINS or CORS_ORIGIN_REGEX must be configured")
        if not self.trusted_host_list:
            raise ValueError("TRUSTED_HOSTS must contain at least one host")
        if self.app_env in {"staging", "production"}:
            if self.debug:
                raise ValueError("DEBUG must be false in staging and production")
            if len(self.jwt_secret_key) < 32:
                raise ValueError("JWT_SECRET_KEY must be at least 32 characters in staging and production")
            if self.db_user.lower() in {"root", "admin"}:
                raise ValueError("A dedicated least-privilege database user is required in staging and production")
            if self.rate_limit_storage_uri.startswith("memory://"):
                raise ValueError("A shared rate-limit store such as Redis is required in staging and production")
            if not self.auth_cookie_mode or not self.auth_cookie_secure:
                raise ValueError("Staging and production require Secure HttpOnly cookie authentication")
            if not self.credential_encryption_key:
                raise ValueError("CREDENTIAL_ENCRYPTION_KEY is required in staging and production")
            if not self.db_ssl_ca:
                raise ValueError("DB_SSL_CA is required in staging and production")
            if not all((self.smtp_host, self.smtp_username, self.smtp_password, self.smtp_from)):
                raise ValueError("SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM are required in staging and production")
            if self.auth_reset_return_token:
                raise ValueError("AUTH_RESET_RETURN_TOKEN must be false in staging and production")
        if self.app_env == "production" and not (
            self.db_provisioner_host and self.db_provisioner_user and self.db_provisioner_password
        ):
            raise ValueError("Dedicated tenant provisioning credentials are required in production")
        return self

    @staticmethod
    def _split(value: str) -> list[str]:
        return [x.strip().lower() for x in value.split(",") if x.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        items = self._split(self.trusted_hosts)
        wildcards = [x for x in items if "*" in x]
        others = [x for x in items if "*" not in x]
        return wildcards + others

    @property
    def max_theoretical_db_connections(self) -> int:
        return self.db_pool_max_size + (
            self.db_max_dedicated_tenant_pools * self.db_tenant_pool_max_size
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
