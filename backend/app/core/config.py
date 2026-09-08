from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ShuleLink"
    app_env: str = "development"
    debug: bool = False
    app_version: str = "0.2.0"
    api_v1_prefix: str = "/api/v1"

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "shulelink"
    db_user: str = "root"
    db_password: str = ""
    db_pool_min_size: int = Field(default=2, ge=1)
    db_pool_max_size: int = Field(default=10, ge=1)

    cors_origins: str = "http://localhost:5173"
    trusted_hosts: str = "localhost,127.0.0.1,admin.localhost,*.localhost,*.shulelink.co.ke"
    max_request_body_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)
    log_level: str = "INFO"

    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = Field(default=15, ge=5, le=60)
    refresh_token_days: int = Field(default=30, ge=1, le=90)
    password_min_length: int = Field(default=10, ge=8, le=128)
    platform_admin_host: str = "admin.shulelink.co.ke"
    root_domain: str = "shulelink.co.ke"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @staticmethod
    def _split(value: str) -> list[str]:
        return [item.strip().lower() for item in value.split(",") if item.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return self._split(self.cors_origins)

    @property
    def trusted_host_list(self) -> list[str]:
        """Return the complete host allowlist required by ShuleLink routing.

        Local development always supports the platform host and tenant
        subdomains. Production supports the configured platform host and
        first-level tenant subdomains under the ShuleLink root domain.
        Explicit TRUSTED_HOSTS values remain supported for deployments that
        need additional custom hosts.
        """
        hosts = set(self._split(self.trusted_hosts))
        hosts.update({"localhost", "127.0.0.1", "admin.localhost", "*.localhost"})
        hosts.add(self.platform_admin_host.lower())
        hosts.add(f"*.{self.root_domain.lower()}")
        return sorted(hosts)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
