from app.routers.accounts import router as accounts_router
from app.routers.activity import router as activity_router
from app.routers.health import router as health_router
from app.routers.rooms import router as rooms_router
from app.routers.session import router as session_router
from app.ws.router import router as ws_router

__all__ = [
    "accounts_router",
    "activity_router",
    "health_router",
    "rooms_router",
    "session_router",
    "ws_router",
]
