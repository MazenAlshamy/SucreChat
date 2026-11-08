import re
import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import bad_request, conflict, too_many, unauthorized
from app.models.identity import EmailVerification, User
from app.security import hash_token, new_id, tokens_match, utcnow
from app.services.mailer import MailResult, send_verification_email, smtp_configured
from app.services.passwords import hash_password, verify_password

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
NAME_RE = re.compile(r"^[\w\s\u0600-\u06FF\-'.]+$", re.UNICODE)
PASSWORD_MIN = 8
PASSWORD_MAX = 72


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_person_name(value: str, label: str) -> str:
    cleaned = "".join(ch for ch in (value or "") if ch.isprintable()).strip()
    if len(cleaned) < 2 or len(cleaned) > 40:
        raise bad_request(f"{label} يجب أن يكون بين حرفين و40 حرفاً")
    if not NAME_RE.match(cleaned):
        raise bad_request(f"{label} يحتوي رموزاً غير مسموحة")
    return cleaned


def validate_email(email: str) -> tuple[str, str]:
    raw = (email or "").strip()
    if len(raw) > 254 or not EMAIL_RE.match(raw):
        raise bad_request("البريد الإلكتروني غير صالح")
    return raw, normalize_email(raw)


def validate_password(password: str) -> str:
    value = password or ""
    if any(ch.isspace() for ch in value) or "\x00" in value:
        raise bad_request("كلمة المرور لا يجوز أن تحتوي مسافات")
    if len(value) < PASSWORD_MIN:
        raise bad_request("كلمة المرور قصيرة جداً")
    if len(value.encode("utf-8")) > PASSWORD_MAX:
        raise bad_request("كلمة المرور طويلة جداً")
    classes = 0
    if re.search(r"[A-Za-z\u0600-\u06FF]", value):
        classes += 1
    if re.search(r"\d", value):
        classes += 1
    if re.search(r"[^A-Za-z0-9\u0600-\u06FF]", value):
        classes += 1
    if classes < 2:
        raise bad_request("استخدم حروفاً مع أرقام أو رمزاً في كلمة المرور")
    return value


def find_by_normalized_email(db: Session, email_normalized: str) -> User | None:
    return db.query(User).filter(User.email_normalized == email_normalized).one_or_none()


def _active_verification(db: Session, user_id: str) -> EmailVerification | None:
    now = utcnow()
    return (
        db.query(EmailVerification)
        .filter(
            EmailVerification.user_id == user_id,
            EmailVerification.used_at.is_(None),
            EmailVerification.expires_at > now,
            EmailVerification.purpose == "signup",
        )
        .order_by(EmailVerification.created_at.desc())
        .first()
    )


def generate_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _issue_code(db: Session, user: User) -> str:
    settings = get_settings()
    now = utcnow()
    db.query(EmailVerification).filter(
        EmailVerification.user_id == user.id,
        EmailVerification.used_at.is_(None),
        EmailVerification.purpose == "signup",
    ).update({"expires_at": now}, synchronize_session=False)
    code = generate_verification_code()
    record = EmailVerification(
        id=new_id(),
        user_id=user.id,
        email_normalized=user.email_normalized or "",
        code_hash=hash_token(code),
        purpose="signup",
        expires_at=now + timedelta(seconds=settings.email_verification_ttl_seconds),
        attempts=0,
        max_attempts=settings.email_verification_max_attempts,
    )
    db.add(record)
    db.flush()
    return code


def register_account(
    db: Session,
    *,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    terms_accepted: bool,
) -> tuple[User, MailResult]:
    if not terms_accepted:
        raise bad_request("يلزم الموافقة على الشروط قبل إنشاء الحساب")
    first = validate_person_name(first_name, "الاسم الأول")
    last = validate_person_name(last_name, "اسم العائلة")
    raw_email, normalized = validate_email(email)
    password_value = validate_password(password)

    existing = find_by_normalized_email(db, normalized)
    if existing is not None:
        if existing.email_verified_at is not None:
            raise conflict("هذا البريد مسجّل مسبقاً")
        existing.first_name = first
        existing.last_name = last
        existing.display_name = first
        existing.email = raw_email
        existing.password_hash = hash_password(password_value)
        existing.terms_accepted_at = utcnow()
        existing.account_status = "pending"
        user = existing
    else:
        user = User(
            id=new_id(),
            display_name=first,
            first_name=first,
            last_name=last,
            email=raw_email,
            email_normalized=normalized,
            password_hash=hash_password(password_value),
            terms_accepted_at=utcnow(),
            account_status="pending",
        )
        db.add(user)
        db.flush()

    code = _issue_code(db, user)
    mailed = send_verification_email(raw_email, code, first)
    return user, mailed


def resend_verification(db: Session, email: str) -> tuple[User, MailResult]:
    _raw, normalized = validate_email(email)
    user = find_by_normalized_email(db, normalized)
    if user is None or user.email_verified_at is not None or not user.password_hash:
        raise bad_request("تعذر إعادة إرسال رمز التأكيد")
    code = _issue_code(db, user)
    mailed = send_verification_email(user.email or "", code, user.first_name or user.display_name)
    return user, mailed


def verify_email_code(db: Session, email: str, code: str) -> User:
    _raw, normalized = validate_email(email)
    cleaned_code = "".join((code or "").split())
    if not re.fullmatch(r"\d{6}", cleaned_code):
        raise bad_request("رمز التأكيد غير صالح")
    user = find_by_normalized_email(db, normalized)
    if user is None or user.email_verified_at is not None or not user.password_hash:
        raise bad_request("رمز التأكيد غير صالح أو منتهٍ")
    record = _active_verification(db, user.id)
    if record is None:
        raise bad_request("رمز التأكيد غير صالح أو منتهٍ")
    if record.attempts >= record.max_attempts:
        raise too_many("تجاوزت عدد محاولات التأكيد")
    record.attempts += 1
    if not tokens_match(cleaned_code, record.code_hash):
        db.flush()
        raise bad_request("رمز التأكيد غير صالح أو منتهٍ")
    record.used_at = utcnow()
    user.email_verified_at = utcnow()
    user.account_status = "active"
    db.flush()
    return user


def authenticate_account(db: Session, email: str, password: str) -> User:
    _raw, normalized = validate_email(email)
    user = find_by_normalized_email(db, normalized)
    if user is None or not user.password_hash:
        raise unauthorized("البريد أو كلمة المرور غير صحيحة")
    if user.email_verified_at is None:
        raise bad_request("يلزم تأكيد البريد قبل تسجيل الدخول")
    if not verify_password(password or "", user.password_hash):
        raise unauthorized("البريد أو كلمة المرور غير صحيحة")
    if user.account_status != "active":
        user.account_status = "active"
        db.flush()
    return user


def mail_status_message(mailed: MailResult | bool) -> str:
    if isinstance(mailed, bool):
        mailed = MailResult(sent=mailed, configured=smtp_configured() or mailed)
    if mailed.sent:
        return "أُرسل رمز التأكيد إلى بريدك. تحقق من الوارد ومجلد غير المرغوب فيه. صلاحية الرمز دقيقة واحدة."
    if not mailed.configured:
        return (
            "الحساب أُنشئ بانتظار التأكيد، لكن إرسال البريد غير مضبوط. "
            "اضبط SMTP_HOST وSMTP_PORT وSMTP_FROM_EMAIL وSMTP_USERNAME/SMTP_PASSWORD عند الحاجة."
        )
    detail = mailed.error or "تحقق من إعدادات SMTP على الخادم."
    return f"الحساب أُنشئ بانتظار التأكيد، لكن تعذر إرسال الرمز. {detail}"
