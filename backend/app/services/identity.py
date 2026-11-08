from fastapi import Request, Response
from sqlalchemy.orm import Session

from app.errors import forbidden, unauthorized
from app.models import SessionRecord, User
from app.security import (
    CSRF_HEADER,
    as_utc,
    clear_auth_cookies,
    generate_token,
    hash_token,
    new_id,
    read_session_token,
    session_expiry,
    set_auth_cookies,
    tokens_match,
    utcnow,
)


def create_user(db: Session, display_name: str) -> User:
    user = User(id=new_id(), display_name=display_name.strip())
    db.add(user)
    db.flush()
    return user


def create_session(db: Session, user: User, response: Response) -> tuple[str, str]:
    session_token = generate_token()
    csrf_token = generate_token(24)
    record = SessionRecord(
        id=new_id(),
        user_id=user.id,
        token_hash=hash_token(session_token),
        csrf_token_hash=hash_token(csrf_token),
        expires_at=session_expiry(),
        last_seen_at=utcnow(),
    )
    db.add(record)
    db.flush()
    set_auth_cookies(response, session_token, csrf_token)
    return session_token, csrf_token


def _load_session(db: Session, token: str | None) -> SessionRecord | None:
    if not token:
        return None
    record = db.query(SessionRecord).filter(SessionRecord.token_hash == hash_token(token)).one_or_none()
    if record is None:
        return None
    if as_utc(record.expires_at) <= utcnow():
        db.delete(record)
        db.flush()
        return None
    record.last_seen_at = utcnow()
    return record


def _verify_csrf(request: Request, session: SessionRecord) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    header_token = request.headers.get(CSRF_HEADER)
    if not header_token or not tokens_match(header_token, session.csrf_token_hash):
        raise forbidden("رمز الحماية غير صالح")


def resolve_user_from_token(db: Session, token: str | None) -> User | None:
    session = _load_session(db, token)
    if session is None:
        return None
    return db.get(User, session.user_id)


def resolve_user(
    db: Session,
    request: Request,
    response: Response,
    required: bool = True,
) -> User | None:
    token = read_session_token(request)
    session = _load_session(db, token)
    if session is None:
        if required:
            raise unauthorized()
        return None
    _verify_csrf(request, session)
    user = db.get(User, session.user_id)
    if user is None:
        if required:
            raise unauthorized()
        return None
    return user


def logout_session(db: Session, request: Request, response: Response) -> None:
    token = read_session_token(request)
    session = _load_session(db, token)
    if session is not None:
        _verify_csrf(request, session)
        db.delete(session)
        db.flush()
    clear_auth_cookies(response)


def ensure_session_user(
    db: Session,
    request: Request,
    response: Response,
    display_name: str | None = None,
) -> User:
    user = resolve_user(db, request, response, required=False)
    if user is not None:
        if display_name:
            cleaned = display_name.strip()
            if cleaned and user.display_name != cleaned:
                user.display_name = cleaned
        return user
    if not display_name or not display_name.strip():
        raise unauthorized("يلزم إدخال اسم العرض لبدء الجلسة")
    user = create_user(db, display_name)
    create_session(db, user, response)
    return user
