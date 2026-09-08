from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ShuleLink"
    app_env: str = "development"
    debug: bool = False
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "shulelink"
    db_user: str = "root"
    db_password: str = ""
    db_pool_min_size: int = Field(default=2, ge=1)
    db_pool_max_size: int = Field(default=10, ge=1)

    cors_origins: str = "http://localhost:5173"
    trusted_hosts: str = "localhost,127.0.0.1"
    max_request_body_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @staticmethod
    def _split(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return self._split(self.cors_origins)

    @property
    def trusted_host_list(self) -> list[str]:
        return self._split(self.trusted_hosts)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
