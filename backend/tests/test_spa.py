from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import reset_engine
from app.main import create_app
from app.rate_limit import reset_rate_limits
from app.ws.hub import reset_hub


def _app_with_dist(dist: Path) -> TestClient:
    get_settings.cache_clear()
    reset_engine()
    reset_rate_limits()
    reset_hub()
    (dist / "assets").mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text("<html><body>securechat-spa</body></html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("window.SECURECHAT=1;", encoding="utf-8")
    return TestClient(create_app())


def test_spa_index_and_assets_are_served(tmp_path, monkeypatch) -> None:
    dist = tmp_path / "dist"
    monkeypatch.setenv("FRONTEND_DIST_DIR", str(dist))
    with _app_with_dist(dist) as client:
        home = client.get("/")
        assert home.status_code == 200
        assert "securechat-spa" in home.text
        asset = client.get("/assets/app.js")
        assert asset.status_code == 200
        assert "SECURECHAT" in asset.text
        deep = client.get("/rooms/abc/meeting")
        assert deep.status_code == 200
        assert "securechat-spa" in deep.text
        missing_api = client.get("/api/does-not-exist")
        assert missing_api.status_code == 404
        health = client.get("/api/health")
        assert health.status_code == 200
    reset_engine()
    get_settings.cache_clear()


def test_api_still_works_without_frontend_dist(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert client.get("/").status_code == 404
    assert client.get("/rooms/1").status_code == 404
