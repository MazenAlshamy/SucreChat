from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.rate_limit import check_rate_limit
from app.schemas.accounts import (
    AccountSessionResponse,
    AccountUser,
    CaptchaChallengeResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    VerifyEmailRequest,
)
from app.services import accounts as account_service
from app.services import captcha as captcha_service
from app.services import identity as identity_service

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _client_key(request: Request, suffix: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{host}:{suffix}"


def _user_view(user) -> AccountUser:
    return AccountUser(
        id=user.id,
        display_name=user.display_name,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        email_verified=user.email_verified_at is not None,
        account_status=user.account_status or "guest",
    )


@router.get("/captcha", response_model=CaptchaChallengeResponse)
def get_captcha(request: Request, db: Session = Depends(get_db)) -> CaptchaChallengeResponse:
    settings = get_settings()
    check_rate_limit(_client_key(request, "captcha"), max(settings.rate_limit_register_per_minute, 20))
    payload = captcha_service.issue_captcha(db)
    return CaptchaChallengeResponse(**payload)


@router.post("/register", response_model=RegisterResponse)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    settings = get_settings()
    check_rate_limit(_client_key(request, "register"), settings.rate_limit_register_per_minute)
    captcha_service.consume_captcha(db, payload.captcha_id, payload.captcha_answer)
    user, mailed = account_service.register_account(
        db,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        password=payload.password,
        terms_accepted=payload.terms_accepted,
    )
    return RegisterResponse(
        email=user.email or "",
        mail_sent=mailed.sent,
        message=account_service.mail_status_message(mailed),
    )


@router.post("/login", response_model=AccountSessionResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AccountSessionResponse:
    settings = get_settings()
    check_rate_limit(_client_key(request, "login"), settings.rate_limit_login_per_minute)
    user = account_service.authenticate_account(db, payload.email, payload.password)
    identity_service.create_session(db, user, response)
    return AccountSessionResponse(user=_user_view(user))


@router.post("/verify-email", response_model=AccountSessionResponse)
def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AccountSessionResponse:
    settings = get_settings()
    check_rate_limit(_client_key(request, "verify"), settings.rate_limit_verify_per_minute)
    user = account_service.verify_email_code(db, payload.email, payload.code)
    identity_service.create_session(db, user, response)
    return AccountSessionResponse(user=_user_view(user))


@router.post("/resend-verification", response_model=RegisterResponse)
def resend_verification(
    payload: ResendVerificationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    settings = get_settings()
    check_rate_limit(_client_key(request, "resend"), settings.rate_limit_resend_per_minute)
    captcha_service.consume_captcha(db, payload.captcha_id, payload.captcha_answer)
    user, mailed = account_service.resend_verification(db, payload.email)
    return RegisterResponse(
        email=user.email or "",
        mail_sent=mailed.sent,
        message=account_service.mail_status_message(mailed),
    )
