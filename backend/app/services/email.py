from dataclasses import dataclass
from enum import StrEnum

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.security_audit import log_security_event


class EmailType(StrEnum):
    PASSWORD_RESET = "Password Reset"
    MFA_VERIFICATION = "MFA Verification"
    SECURITY_ALERT = "Security Alert"
    WORKFLOW_NOTIFICATION = "Workflow Notification"
    SUPPLIER_INVITE = "Future Supplier Invite"


@dataclass(slots=True)
class EmailMessage:
    to_email: str
    subject: str
    body: str
    email_type: EmailType
    metadata: dict | None = None


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

    # Console mode is intentionally provider-agnostic for local demo and test environments.
    # Production providers can plug into this boundary without changing auth or workflow code.
    if provider == "console":
        details["delivery"] = "console"
    elif provider == "sendgrid":
        details["delivery"] = "sendgrid_pending_adapter"
    elif provider == "ses":
        details["delivery"] = "ses_pending_adapter"
    elif provider == "mailgun":
        details["delivery"] = "mailgun_pending_adapter"
    else:
        status = "skipped"
        details["delivery"] = "unknown_provider"

    log_security_event(
        db,
        event_type=f"EMAIL_{status.upper()}",
        user_id=user_id,
        request=request,
        success=status == "queued",
        details=details,
    )
    return {"status": status, "provider": provider}
