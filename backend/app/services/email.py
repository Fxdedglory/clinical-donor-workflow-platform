import smtplib
from dataclasses import dataclass
from email.message import EmailMessage as MIMEEmailMessage
from enum import StrEnum

import requests
from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.security_audit import log_security_event


class EmailType(StrEnum):
    ACCOUNT_SETUP = "Account Setup"
    PASSWORD_RESET = "Password Reset"
    MFA_VERIFICATION = "MFA Verification"
    SECURITY_ALERT = "Security Alert"
    WORKFLOW_NOTIFICATION = "Workflow Notification"
    SUPPLIER_INVITE = "Partner Invite"


@dataclass(slots=True)
class EmailMessage:
    to_email: str
    subject: str
    body: str
    email_type: EmailType
    metadata: dict | None = None


def _from_address() -> str:
    return f"{settings.email_from_name} <{settings.email_from}>"


def _send_smtp(message: EmailMessage) -> None:
    if not settings.smtp_host:
        raise ValueError("SMTP_HOST is required for EMAIL_PROVIDER=smtp")
    mime = MIMEEmailMessage()
    mime["From"] = _from_address()
    mime["To"] = message.to_email
    mime["Subject"] = message.subject
    mime.set_content(message.body)

    smtp_class = smtplib.SMTP_SSL if settings.smtp_use_ssl else smtplib.SMTP
    with smtp_class(settings.smtp_host, settings.smtp_port, timeout=20) as client:
        if settings.smtp_use_tls and not settings.smtp_use_ssl:
            client.starttls()
        if settings.smtp_username and settings.smtp_password:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(mime)


def _send_sendgrid(message: EmailMessage) -> None:
    if not settings.sendgrid_api_key:
        raise ValueError("SENDGRID_API_KEY is required for EMAIL_PROVIDER=sendgrid")
    response = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={
            "Authorization": f"Bearer {settings.sendgrid_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "personalizations": [{"to": [{"email": message.to_email}]}],
            "from": {"email": settings.email_from, "name": settings.email_from_name},
            "subject": message.subject,
            "content": [{"type": "text/plain", "value": message.body}],
        },
        timeout=20,
    )
    response.raise_for_status()


def _send_mailgun(message: EmailMessage) -> None:
    if not settings.mailgun_api_key or not settings.mailgun_domain:
        raise ValueError("MAILGUN_API_KEY and MAILGUN_DOMAIN are required for EMAIL_PROVIDER=mailgun")
    response = requests.post(
        f"https://api.mailgun.net/v3/{settings.mailgun_domain}/messages",
        auth=("api", settings.mailgun_api_key),
        data={
            "from": _from_address(),
            "to": message.to_email,
            "subject": message.subject,
            "text": message.body,
        },
        timeout=20,
    )
    response.raise_for_status()


def send_email(
    db: Session,
    message: EmailMessage,
    *,
    user_id: int | None = None,
    request: Request | None = None,
) -> dict[str, str]:
    provider = settings.email_provider.lower()
    status = "queued"
    details = {
        "provider": provider,
        "email_type": message.email_type.value,
        "to": message.to_email,
        "subject": message.subject,
        "metadata": message.metadata or {},
    }

    try:
        if provider == "console":
            details["delivery"] = "console"
        elif provider == "smtp":
            _send_smtp(message)
            details["delivery"] = "smtp"
        elif provider == "sendgrid":
            _send_sendgrid(message)
            details["delivery"] = "sendgrid"
        elif provider == "mailgun":
            _send_mailgun(message)
            details["delivery"] = "mailgun"
        elif provider == "ses":
            status = "skipped"
            details["delivery"] = "ses_adapter_not_enabled"
        else:
            status = "skipped"
            details["delivery"] = "unknown_provider"
    except Exception as exc:
        status = "failed"
        details["delivery"] = provider
        details["error"] = str(exc)

    log_security_event(
        db,
        event_type=f"EMAIL_{status.upper()}",
        user_id=user_id,
        request=request,
        success=status == "queued",
        details=details,
    )
    return {"status": status, "provider": provider}
