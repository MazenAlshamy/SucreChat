from datetime import datetime

from pydantic import BaseModel, Field


class SessionBootstrapRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=40)


class SessionUser(BaseModel):
    id: str
    display_name: str
    created_at: datetime
    account_status: str = "guest"
    email: str | None = None
    first_name: str | None = None


class SessionResponse(BaseModel):
    user: SessionUser
