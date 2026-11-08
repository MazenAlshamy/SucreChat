from fastapi.testclient import TestClient


def test_health_endpoint_returns_ok_when_database_is_available(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "securechat-api"
    assert payload["database"] == "connected"
    assert payload["livekit_configured"] is False
    assert payload["media_available"] is True
    assert payload["media_provider"] == "webrtc"
    assert payload["environment"] == "test"
    assert payload["version"] == "0.1.0"
    assert "يعمل" in payload["message"]


def test_health_endpoint_content_type_is_json(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.headers["content-type"].startswith("application/json")


def test_unknown_route_returns_404(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
