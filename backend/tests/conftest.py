import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

os.environ["APP_ENV"] = "test"
os.environ["APP_VERSION"] = "0.1.0"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["FRONTEND_DIST_DIR"] = "/nonexistent-securechat-frontend-dist"

from app.config import get_settings
from app.database import init_db, reset_engine
from app.rate_limit import reset_rate_limits
from app.ws.hub import reset_hub


@pytest.fixture
def client():
    get_settings.cache_clear()
    reset_engine()
    reset_rate_limits()
    reset_hub()
    init_db()

    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client

    reset_engine()
    reset_rate_limits()
    reset_hub()
    get_settings.cache_clear()


def csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("sc_csrf")
    if not token:
        return {}
    return {"X-CSRF-Token": token}


def create_room(client: TestClient, name: str = "غرفة الاختبار", display_name: str = "مالك", max_participants: int = 4):
    response = client.post(
        "/api/rooms",
        json={
            "name": name,
            "description": "غرفة لاختبارات الفصل الثاني",
            "max_participants": max_participants,
            "display_name": display_name,
        },
        headers=csrf_headers(client),
    )
    return response


def other_client() -> TestClient:
    from app.main import create_app

    return TestClient(create_app())
