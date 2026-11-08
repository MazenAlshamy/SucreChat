from email.message import EmailMessage

from app.config import Settings
from app.services.mailer import MailResult, send_verification_email, smtp_configured


def test_smtp_configured_requires_host_and_from() -> None:
    empty = Settings(app_env="test")
    host_only = Settings(app_env="test", smtp_host="smtp.gmail.com")
    from_alias = Settings(app_env="test", smtp_host="smtp.gmail.com", smtp_from_email="noreply@example.com")
    assert empty.smtp_configured is False
    assert host_only.smtp_configured is False
    assert from_alias.smtp_configured is True
    assert from_alias.resolved_smtp_from == "noreply@example.com"


def test_smtp_encryption_mode_from_port_and_flag() -> None:
    starttls = Settings(app_env="test", smtp_port=587, smtp_use_tls=True)
    ssl_port = Settings(app_env="test", smtp_port=465, smtp_use_tls=False)
    explicit = Settings(app_env="test", smtp_port=2525, smtp_encryption="ssl")
    none = Settings(app_env="test", smtp_port=25, smtp_use_tls=False, smtp_encryption="none")
    assert starttls.smtp_encryption_mode == "starttls"
    assert ssl_port.smtp_encryption_mode == "ssl"
    assert explicit.smtp_encryption_mode == "ssl"
    assert none.smtp_encryption_mode == "none"


def test_send_skips_when_smtp_not_configured(monkeypatch) -> None:
    monkeypatch.setattr("app.services.mailer.smtp_configured", lambda: False)
    result = send_verification_email("user@example.com", "123456", "أحمد")
    assert result == MailResult(sent=False, configured=False)


def test_send_uses_smtp_and_does_not_log_code(monkeypatch) -> None:
    captured: dict = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=15):
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout

        def ehlo(self):
            captured["ehlo"] = captured.get("ehlo", 0) + 1

        def starttls(self, context=None):
            captured["starttls"] = True

        def login(self, username, password):
            captured["username"] = username
            captured["password_set"] = bool(password)

        def send_message(self, message: EmailMessage):
            captured["to"] = message["To"]
            captured["subject"] = message["Subject"]
            captured["body"] = message.get_content()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("app.services.mailer.smtp_configured", lambda: True)
    monkeypatch.setattr(
        "app.services.mailer.get_settings",
        lambda: Settings(
            app_env="test",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_username="noreply@example.com",
            smtp_password="app-password",
            smtp_from_email="noreply@example.com",
            smtp_from_name="SecureChat",
            smtp_use_tls=True,
        ),
    )
    monkeypatch.setattr("app.services.mailer.smtplib.SMTP", FakeSMTP)
    result = send_verification_email("user@example.com", "654321", "أحمد")
    assert result.sent is True
    assert result.configured is True
    assert captured["host"] == "smtp.gmail.com"
    assert captured["port"] == 587
    assert captured["starttls"] is True
    assert captured["username"] == "noreply@example.com"
    assert captured["to"] == "user@example.com"
    assert "654321" in captured["body"]
    assert "رمز" in captured["subject"]


def test_send_reports_connection_error(monkeypatch) -> None:
    class FailingSMTP:
        def __init__(self, *args, **kwargs):
            raise TimeoutError("timed out")

    monkeypatch.setattr("app.services.mailer.smtp_configured", lambda: True)
    monkeypatch.setattr(
        "app.services.mailer.get_settings",
        lambda: Settings(
            app_env="test",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_from="noreply@example.com",
        ),
    )
    monkeypatch.setattr("app.services.mailer.smtplib.SMTP", FailingSMTP)
    result = send_verification_email("user@example.com", "111111", "أحمد")
    assert result.sent is False
    assert result.configured is True
    assert result.error == "تعذر الاتصال بخادم البريد"
