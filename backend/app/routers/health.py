from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.config import get_settings
from app.database import get_engine
from app.schemas.health import HealthResponse
from app.services import livekit as livekit_service

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    settings = get_settings()
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "degraded",
                "service": "securechat-api",
                "version": settings.app_version,
                "environment": settings.app_env,
                "database": "unavailable",
                "livekit_configured": settings.livekit_configured,
                "media_available": False,
                "media_provider": "none",
                "message": "تعذر الاتصال بقاعدة البيانات",
                "error": str(exc.__class__.__name__),
            },
        ) from exc

    media_enabled, media_provider, _reason = livekit_service.media_status()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.app_env,
        database="connected",
        livekit_configured=settings.livekit_configured,
        media_available=media_enabled,
        media_provider=media_provider,
        message="الخادم وقاعدة البيانات يعملان بشكل طبيعي",
    )
