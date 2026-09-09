from functools import lru_cache
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "ShuleLink"; app_env: str = "development"; debug: bool = False; app_version: str = "0.2.0"; api_v1_prefix: str = "/api/v1"
    db_host: str = "127.0.0.1"; db_port: int = 3306; db_name: str = "shulelink"; db_user: str = "root"; db_password: str = ""; db_ssl_ca: str | None = None; db_ssl_verify: bool = True
    db_pool_min_size: int = Field(default=2, ge=1); db_pool_max_size: int = Field(default=10, ge=1); db_pool_recycle_seconds: int = Field(default=1800, ge=60); db_connect_timeout_seconds: int = Field(default=10, ge=1, le=60); db_read_timeout_seconds: int = Field(default=30, ge=1, le=300); db_write_timeout_seconds: int = Field(default=30, ge=1, le=300)
    cors_origins: str = "http://localhost:5173"; trusted_hosts: str = "localhost,127.0.0.1,admin.localhost,*.localhost,*.shulelink.co.ke"; max_request_body_bytes: int = Field(default=10 * 1024 * 1024, ge=1024); log_level: str = "INFO"
    rate_limit_storage_uri: str = "memory://"; rate_limit_default: str = "120/minute"
    jwt_secret_key: str = "change-this-in-production"; jwt_algorithm: str = "HS256"; jwt_issuer: str = "shulelink-api"; jwt_audience: str = "shulelink"; access_token_minutes: int = Field(default=15, ge=5, le=60); refresh_token_days: int = Field(default=30, ge=1, le=90); password_min_length: int = Field(default=8, ge=8, le=128)
    auth_cookie_mode: bool = False; auth_cookie_secure: bool = False; auth_cookie_samesite: str = "lax"; csrf_token_bytes: int = Field(default=32, ge=16, le=64); auth_reset_return_token: bool = False; password_reset_minutes: int = Field(default=30, ge=5, le=120); mfa_challenge_minutes: int = Field(default=5, ge=1, le=15); mfa_issuer: str = "ShuleLink"; credential_encryption_key: str | None = None
    smtp_host: str | None = None; smtp_port: int = 587; smtp_username: str | None = None; smtp_password: str | None = None; smtp_from: str | None = None; smtp_starttls: bool = True; password_reset_base_url: str = "http://localhost:5173/reset-password"
    db_provisioner_host: str | None = None; db_provisioner_port: int = 3306; db_provisioner_user: str | None = None; db_provisioner_password: str | None = None; db_provisioner_tenant_host: str = "%"
    platform_admin_host: str = "admin.shulelink.co.ke"; root_domain: str = "shulelink.co.ke"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    @model_validator(mode="after")
    def validate_runtime(self):
        if self.db_pool_max_size < self.db_pool_min_size: raise ValueError("DB_POOL_MAX_SIZE must be greater than or equal to DB_POOL_MIN_SIZE")
        if self.auth_cookie_samesite.lower() not in {"lax","strict","none"}: raise ValueError("AUTH_COOKIE_SAMESITE must be lax, strict or none")
        if self.auth_cookie_samesite.lower() == "none" and not self.auth_cookie_secure: raise ValueError("AUTH_COOKIE_SECURE must be true when SameSite=None")
        if self.app_env.lower() == "production":
            if self.debug: raise ValueError("DEBUG must be false in production")
            if self.jwt_secret_key == "change-this-in-production" or len(self.jwt_secret_key) < 32: raise ValueError("JWT_SECRET_KEY must be a unique secret of at least 32 characters in production")
            if self.db_user.lower() in {"root","admin"}: raise ValueError("A dedicated least-privilege database user is required in production")
            if self.rate_limit_storage_uri.startswith("memory://"): raise ValueError("A shared rate-limit store such as Redis is required in production")
            if not self.cors_origin_list: raise ValueError("CORS_ORIGINS must contain at least one trusted origin in production")
            if not self.auth_cookie_mode or not self.auth_cookie_secure: raise ValueError("Production browser authentication requires Secure HttpOnly cookie mode")
            if not self.credential_encryption_key: raise ValueError("CREDENTIAL_ENCRYPTION_KEY is required in production")
            if not self.db_ssl_ca: raise ValueError("DB_SSL_CA is required in production")
            if not all((self.smtp_host,self.smtp_username,self.smtp_password,self.smtp_from)): raise ValueError("SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM are required in production")
            if self.auth_reset_return_token: raise ValueError("AUTH_RESET_RETURN_TOKEN must be false in production")
            if not self.db_provisioner_host or not self.db_provisioner_user or not self.db_provisioner_password: raise ValueError("Dedicated tenant provisioning credentials are required in production")
        return self
    @staticmethod
    def _split(value: str) -> list[str]: return [item.strip().lower() for item in value.split(",") if item.strip()]
    @property
    def cors_origin_list(self) -> list[str]: return self._split(self.cors_origins)
    @property
    def trusted_host_list(self) -> list[str]:
        hosts=set(self._split(self.trusted_hosts)); hosts.update({"localhost","127.0.0.1","admin.localhost","*.localhost"}); hosts.add(self.platform_admin_host.lower()); hosts.add(f"*.{self.root_domain.lower()}"); return sorted(hosts)

@lru_cache
def get_settings() -> Settings: return Settings()
settings = get_settings()
