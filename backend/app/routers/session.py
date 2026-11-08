from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_optional_user
from app.models import User
from app.schemas.identity import SessionBootstrapRequest, SessionResponse, SessionUser
from app.services import identity as identity_service
from app.services.rooms import validate_display_name

router = APIRouter(prefix="/api/session", tags=["session"])


def _to_response(user: User) -> SessionResponse:
    return SessionResponse(
        user=SessionUser(
            id=user.id,
            display_name=user.display_name,
            created_at=user.created_at,
            account_status=user.account_status or "guest",
            email=user.email,
            first_name=user.first_name,
        )
    )


@router.get("", response_model=SessionResponse)
def read_session(user: User | None = Depends(get_optional_user)) -> SessionResponse:
    if user is None:
        from app.errors import unauthorized

        raise unauthorized()
    return _to_response(user)


@router.post("", response_model=SessionResponse)
def bootstrap_session(
    payload: SessionBootstrapRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> SessionResponse:
    display_name = validate_display_name(payload.display_name)
    user = identity_service.ensure_session_user(db, request, response, display_name)
    return _to_response(user)


@router.delete("")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    identity_service.logout_session(db, request, response)
    return {"ok": True}
