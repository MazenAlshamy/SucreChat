import logging
import smtplib
import socket
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.config import get_settings

logger = logging.getLogger("securechat.mailer")


@dataclass(frozen=True)
class MailResult:
    sent: bool
    configured: bool
    error: str | None = None


def smtp_configured() -> bool:
    settings = get_settings()
    return bool(settings.smtp_host.strip() and settings.resolved_smtp_from)


def send_verification_email(to_email: str, code: str, first_name: str) -> MailResult:
    settings = get_settings()
    if not smtp_configured():
        return MailResult(sent=False, configured=False)
    sender = settings.resolved_smtp_from
    message = EmailMessage()
    display_name = settings.smtp_from_name.strip() or settings.app_name
    message["From"] = formataddr((display_name, sender))
    message["To"] = to_email
    message["Subject"] = "رمز تأكيد حساب SecureChat"
    message["Message-ID"] = make_msgid(domain=sender.split("@")[-1] if "@" in sender else "securechat.local")
    greeting = first_name.strip() or "مرحباً"
    message.set_content(
        f"{greeting}،\n\n"
        f"رمز تأكيد بريدك في SecureChat هو: {code}\n"
        "صلاحية الرمز دقيقة واحدة.\n"
        "إذا لم تطلب إنشاء حساب فتجاهل هذه الرسالة.\n"
    )
    try:
        _deliver(settings, message)
    except smtplib.SMTPAuthenticationError:
        logger.warning("smtp authentication failed")
        return MailResult(sent=False, configured=True, error="فشل التحقق من حساب SMTP")
    except smtplib.SMTPRecipientsRefused:
        logger.warning("smtp rejected recipient")
        return MailResult(sent=False, configured=True, error="رفض خادم البريد عنوان المستلم")
    except smtplib.SMTPSenderRefused:
        logger.warning("smtp rejected sender")
        return MailResult(sent=False, configured=True, error="رفض خادم البريد عنوان المرسل")
    except (TimeoutError, socket.timeout, socket.gaierror, ConnectionRefusedError, smtplib.SMTPServerDisconnected):
        logger.warning("smtp connection failed")
        return MailResult(sent=False, configured=True, error="تعذر الاتصال بخادم البريد")
    except (OSError, smtplib.SMTPException):
        logger.warning("smtp send failed")
        return MailResult(sent=False, configured=True, error="تعذر إرسال رسالة التحقق")
    return MailResult(sent=True, configured=True)


def _deliver(settings, message: EmailMessage) -> None:
    host = settings.smtp_host.strip()
    port = settings.smtp_port
    mode = settings.smtp_encryption_mode
    username = settings.smtp_username.strip()
    password = settings.smtp_password
    context = ssl.create_default_context()
    if mode == "ssl":
        with smtplib.SMTP_SSL(host, port, timeout=15, context=context) as client:
            _authenticate_and_send(client, username, password, message)
        return
    with smtplib.SMTP(host, port, timeout=15) as client:
        client.ehlo()
        if mode == "starttls":
            client.starttls(context=context)
            client.ehlo()
        _authenticate_and_send(client, username, password, message)


def _authenticate_and_send(client, username: str, password: str, message: EmailMessage) -> None:
    if username:
        client.login(username, password)
    client.send_message(message)
