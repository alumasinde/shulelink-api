from fastapi.testclient import TestClient

from app.main import app


def test_root():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health():
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_unknown_route_uses_consistent_error_shape():
    response = TestClient(app).get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json()["success"] is False
    assert "error" in response.json()
