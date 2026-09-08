import pytest
from app.core.security import create_access_token, decode_access_token, validate_password


def test_password_policy():
    validate_password("SecurePass123")
    with pytest.raises(ValueError):
        validate_password("weak")


def test_access_token_contains_identity_context():
    token, _ = create_access_token(user_id="00000000-0000-0000-0000-000000000001", user_type="tenant", tenant_id="00000000-0000-0000-0000-000000000002", session_id="00000000-0000-0000-0000-000000000003")
    payload = decode_access_token(token)
    assert payload["typ"] == "tenant"
    assert payload["tid"] == "00000000-0000-0000-0000-000000000002"
    assert payload["sid"] == "00000000-0000-0000-0000-000000000003"
