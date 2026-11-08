from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import unauthorized
from app.models import User
from app.services import identity as identity_service


def get_current_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    user = identity_service.resolve_user(db, request, response, required=True)
    if user is None:
        raise unauthorized()
    return user


def get_optional_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User | None:
    return identity_service.resolve_user(db, request, response, required=False)
