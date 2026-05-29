from fastapi.testclient import TestClient

from app.main import app


def test_api_health_returns_runtime_metadata() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["startup_mode"] == "fastapi_react"
    assert payload["version"]
