from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import get_session_factory
from app.models.identity import CaptchaChallenge, EmailVerification, User
from app.rate_limit import reset_rate_limits
from app.security import hash_token
from tests.conftest import create_room, csrf_headers


def _solve_captcha(client: TestClient) -> tuple[str, str]:
    payload = client.get("/api/accounts/captcha").json()
    db = get_session_factory()()
    challenge = db.get(CaptchaChallenge, payload["captcha_id"])
    hashed = challenge.answer_hash
    db.close()
    for value in range(2, 19):
        if hash_token(str(value)) == hashed:
            return payload["captcha_id"], str(value)
    raise AssertionError("تعذر حل سؤال التحقق")


def _register(client: TestClient, email: str = "user@example.com", **overrides) -> tuple:
    captcha_id, answer = _solve_captcha(client)
    body = {
        "first_name": "أحمد",
        "last_name": "سالم",
        "email": email,
        "password": "Passw0rd!",
        "terms_accepted": True,
        "captcha_id": captcha_id,
        "captcha_answer": answer,
    }
    body.update(overrides)
    return client.post("/api/accounts/register", json=body)


def test_register_requires_captcha(client: TestClient) -> None:
    response = client.post(
        "/api/accounts/register",
        json={
            "first_name": "أحمد",
            "last_name": "سالم",
            "email": "user@example.com",
            "password": "Passw0rd!",
            "terms_accepted": True,
            "captcha_id": "missing",
            "captcha_answer": "1",
        },
    )
    assert response.status_code == 400


def _verify(client: TestClient, email: str = "user@example.com", code: str = "123456"):
    return client.post("/api/accounts/verify-email", json={"email": email, "code": code})


def test_register_and_verify_creates_session(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.accounts.generate_verification_code", lambda: "123456")
    created = _register(client)
    assert created.status_code == 200
    payload = created.json()
    assert payload["email"] == "user@example.com"
    assert payload["verification_required"] is True
    assert payload["mail_sent"] is False
    assert "SMTP_HOST" in payload["message"]
    assert "password" not in payload
    assert "code" not in payload

    db = get_session_factory()()
    user = db.query(User).filter(User.email_normalized == "user@example.com").one()
    assert user.password_hash
    assert user.password_hash != "Passw0rd!"
    assert user.email_verified_at is None
    assert user.account_status == "pending"
    db.close()

    verified = client.post(
        "/api/accounts/verify-email",
        json={"email": "user@example.com", "code": "123456"},
    )
    assert verified.status_code == 200
    body = verified.json()["user"]
    assert body["display_name"] == "أحمد"
    assert body["email_verified"] is True
    assert body["account_status"] == "active"
    assert client.cookies.get("sc_session")
    session = client.get("/api/session")
    assert session.status_code == 200
    assert session.json()["user"]["display_name"] == "أحمد"


def test_login_after_verification(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.accounts.generate_verification_code", lambda: "123456")
    assert _register(client).status_code == 200
    assert _verify(client).status_code == 200
    client.delete("/api/session", headers=csrf_headers(client))
    denied = client.get("/api/session")
    assert denied.status_code == 401
    failed = client.post(
        "/api/accounts/login",
        json={"email": "user@example.com", "password": "wrong-pass"},
    )
    assert failed.status_code == 401
    logged = client.post(
        "/api/accounts/login",
        json={"email": "user@example.com", "password": "Passw0rd!"},
    )
    assert logged.status_code == 200
    assert logged.json()["user"]["email_verified"] is True
    session = client.get("/api/session")
    assert session.status_code == 200
    assert session.json()["user"]["display_name"] == "أحمد"


def test_login_requires_verified_email(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.accounts.generate_verification_code", lambda: "123456")
    assert _register(client).status_code == 200
    pending = client.post(
        "/api/accounts/login",
        json={"email": "user@example.com", "password": "Passw0rd!"},
    )
    assert pending.status_code == 400
    assert "تأكيد" in pending.json()["detail"]["message"]


def test_duplicate_verified_email_conflicts(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.accounts.generate_verification_code", lambda: "123456")
    assert _register(client).status_code == 200
    assert client.post(
        "/api/accounts/verify-email",
        json={"email": "user@example.com", "code": "123456"},
    ).status_code == 200
    again = _register(client)
    assert again.status_code == 409


def test_pending_email_can_register_again(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.accounts.generate_verification_code", lambda: "111111")
    first = _register(client)
    second = _register(client, first_name="ليان")
    assert first.status_code == 200
    assert second.status_code == 200
    db = get_session_factory()()
    users = db.query(User).filter(User.email_normalized == "user@example.com").all()
    assert len(users) == 1
    assert users[0].first_name == "ليان"
    db.close()


def test_invalid_or_expired_code_is_rejected(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.accounts.generate_verification_code", lambda: "222222")
    assert _register(client).status_code == 200
    wrong = client.post(
        "/api/accounts/verify-email",
        json={"email": "user@example.com", "code": "000000"},
    )
    assert wrong.status_code == 400
    db = get_session_factory()()
    record = db.query(EmailVerification).one()
    record.expires_at = datetime.utcnow() - timedelta(seconds=5)
    db.commit()
    db.close()
    expired = client.post(
        "/api/accounts/verify-email",
        json={"email": "user@example.com", "code": "222222"},
    )
    assert expired.status_code == 400


def test_weak_password_and_missing_terms_rejected(client: TestClient) -> None:
    weak = _register(client, password="password")
    assert weak.status_code == 400
    no_terms = _register(client, email="other@example.com", terms_accepted=False)
    assert no_terms.status_code == 400


def test_register_rate_limit(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_REGISTER_PER_MINUTE", "1")
    get_settings.cache_clear()
    reset_rate_limits()
    first = _register(client, email="one@example.com")
    second = _register(client, email="two@example.com")
    assert first.status_code == 200
    assert second.status_code == 429
    get_settings.cache_clear()
    reset_rate_limits()


def test_guest_rooms_still_work_after_accounts(client: TestClient) -> None:
    created = create_room(client)
    assert created.status_code == 200
    listed = client.get("/api/rooms")
    assert listed.status_code == 200
    logout = client.delete("/api/session", headers=csrf_headers(client))
    assert logout.status_code == 200


def test_resend_invalidates_previous_code(client: TestClient, monkeypatch) -> None:
    codes = iter(["111111", "222222"])
    monkeypatch.setattr("app.services.accounts.generate_verification_code", lambda: next(codes))
    assert _register(client).status_code == 200
    captcha_id, answer = _solve_captcha(client)
    resend = client.post(
        "/api/accounts/resend-verification",
        json={"email": "user@example.com", "captcha_id": captcha_id, "captcha_answer": answer},
    )
    assert resend.status_code == 200
    assert resend.json()["mail_sent"] is False
    assert "code" not in resend.json()
    old = client.post(
        "/api/accounts/verify-email",
        json={"email": "user@example.com", "code": "111111"},
    )
    assert old.status_code == 400
    fresh = client.post(
        "/api/accounts/verify-email",
        json={"email": "user@example.com", "code": "222222"},
    )
    assert fresh.status_code == 200


def test_smtp_send_failure_does_not_return_code(client: TestClient, monkeypatch) -> None:
    from app.services.mailer import MailResult

    monkeypatch.setattr("app.services.accounts.generate_verification_code", lambda: "333333")
    monkeypatch.setattr(
        "app.services.accounts.send_verification_email",
        lambda *args, **kwargs: MailResult(sent=False, configured=True, error="تعذر الاتصال بخادم البريد"),
    )
    created = _register(client)
    assert created.status_code == 200
    payload = created.json()
    assert payload["mail_sent"] is False
    assert "تعذر الاتصال بخادم البريد" in payload["message"]
    assert "333333" not in str(payload)
    verified = client.post(
        "/api/accounts/verify-email",
        json={"email": "user@example.com", "code": "333333"},
    )
    assert verified.status_code == 200
