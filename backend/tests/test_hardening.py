import pytest
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import _safe_validation_details


def test_pool_bounds_are_validated():
    with pytest.raises(ValidationError):
        Settings(db_pool_min_size=10, db_pool_max_size=2)


def test_tenant_pool_bounds_are_validated():
    with pytest.raises(ValidationError):
        Settings(db_tenant_pool_min_size=4, db_tenant_pool_max_size=2)


def test_connection_budget_is_bounded():
    settings = Settings(
        db_pool_min_size=1,
        db_pool_max_size=2,
        db_tenant_pool_min_size=1,
        db_tenant_pool_max_size=2,
        db_max_dedicated_tenant_pools=3,
    )
    assert settings.max_theoretical_db_connections == 8


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


def test_validation_details_never_echo_input_values():
    error = RequestValidationError(
        [
            {
                "type": "string_too_short",
                "loc": ("body", "password"),
                "msg": "Password is too short",
                "input": "SuperSecret123!",
                "ctx": {"min_length": 10},
            }
        ]
    )
    details = _safe_validation_details(error)
    assert details == [{"loc": ["body", "password"], "type": "string_too_short"}]
    assert "SuperSecret123!" not in str(details)
