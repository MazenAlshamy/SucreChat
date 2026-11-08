from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str = "securechat-api"
    version: str
    environment: str
    database: Literal["connected", "unavailable"]
    livekit_configured: bool = False
    media_available: bool = False
    media_provider: str = "none"
    message: str = Field(default="الخادم يعمل بشكل طبيعي")
