import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_pool_bounds_are_validated():
    with pytest.raises(ValidationError):
        Settings(db_pool_min_size=10, db_pool_max_size=2)


def test_production_rejects_default_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret_key="change-this-in-production",
            db_user="shulelink_app",
            rate_limit_storage_uri="redis://127.0.0.1:6379/0",
            cors_origins="https://admin.shulelink.co.ke",
        )


def test_production_requires_shared_rate_limit_store():
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret_key="a" * 64,
            db_user="shulelink_app",
            rate_limit_storage_uri="memory://",
            cors_origins="https://admin.shulelink.co.ke",
        )


def test_production_rejects_debug_and_root_database_user():
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            debug=True,
            jwt_secret_key="a" * 64,
            db_user="root",
            rate_limit_storage_uri="redis://127.0.0.1:6379/0",
            cors_origins="https://admin.shulelink.co.ke",
        )
