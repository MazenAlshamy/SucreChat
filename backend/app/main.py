from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.database import init_db
from app.routers import (
    accounts_router,
    activity_router,
    health_router,
    rooms_router,
    session_router,
    ws_router,
)
from app.static_spa import mount_frontend


def _validate_cors_origins() -> list[str]:
    settings = get_settings()
    origins = settings.cors_origin_list
    if "*" in origins:
        if settings.is_production:
            raise RuntimeError(
                "CORS wildcard is not allowed when APP_ENV=production"
            )
        return ["*"]
    if not origins:
        if settings.is_production:
            return []
        return ["http://localhost:5173"]
    return origins


@asynccontextmanager
async def lifespan(_application: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="SecureChat API",
        description="واجهة برمجية لغرف SecureChat الخاصة والدعوات وطلبات الانضمام",
        version=settings.app_version,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=_validate_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Accept", "X-CSRF-Token"],
    )

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(self), microphone=(self), display-capture=(self), geolocation=()"
        )
        response.headers["Cache-Control"] = "no-store"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @application.exception_handler(Exception)
    async def unhandled_error(_request: Request, exc: Exception):
        if isinstance(exc, (HTTPException, StarletteHTTPException, RequestValidationError)):
            raise exc
        if settings.is_production:
            return JSONResponse(
                status_code=500,
                content={"detail": {"message": "حدث خطأ غير متوقع"}},
            )
        raise exc

    application.include_router(health_router)
    application.include_router(session_router)
    application.include_router(accounts_router)
    application.include_router(rooms_router)
    application.include_router(activity_router)
    application.include_router(ws_router)
    mount_frontend(application)
    return application


app = create_app()
