"""Transactional email.

Sending is best-effort and never part of the request: routes hand these
functions to FastAPI's BackgroundTasks. With no SMTP_HOST configured the
message is only logged, so the app behaves the same in development, in
tests and in the offline desktop build.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import settings
from app.core.logging import get_logger

log = get_logger("francessca.email")

_FOOTER = (
    "\n\n--\nFrancesca helps people prepare before they speak with a lawyer. "
    "It does not provide legal advice."
)


def send_email(to: str | None, subject: str, body: str) -> bool:
    """Send one plain-text email. Returns whether it actually went out."""
    to = (to or "").strip()
    if not to:
        return False
    if not settings.smtp_host:
        log.info("email (not sent, SMTP_HOST unset) to=%s subject=%s", to, subject)
        return False

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body + _FOOTER)
    try:
        if settings.smtp_port == 465:
            server: smtplib.SMTP = smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, timeout=15
            )
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
        with server:
            if settings.smtp_port != 465:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        log.info("email sent to=%s subject=%s", to, subject)
        return True
    except Exception:  # noqa: BLE001 - a mail outage must never break a request
        log.exception("email failed to=%s subject=%s", to, subject)
        return False


def _url(path: str) -> str:
    return settings.frontend_url.rstrip("/") + path


# --- The messages -------------------------------------------------------
def lawyer_registered_admin(name: str, email: str, city: str | None) -> None:
    send_email(
        settings.contact_email,
        f"New lawyer sign-up: {name}",
        f"{name} <{email}>{' from ' + city if city else ''} registered as a lawyer "
        f"and is waiting for approval.\n\nReview: {_url('/admin/lawyers')}",
    )


def lawyer_decision(email: str, name: str, approved: bool) -> None:
    if approved:
        send_email(
            email,
            "Your Francesca profile is live",
            f"Hello {name},\n\nyour profile has been approved and now appears in the "
            f"directory. Your first {settings.lawyer_free_orders} orders are free.\n\n"
            f"Open your portal: {_url('/lawyer')}",
        )
    else:
        send_email(
            email,
            "About your Francesca application",
            f"Hello {name},\n\nwe could not approve your profile at this time. "
            "Reply to this email if you think this is a mistake.",
        )


def new_order_lawyer(email: str | None, name: str, title: str, score: int) -> None:
    send_email(
        email,
        "New case request on Francesca",
        f"Hello {name},\n\na client sent you their prepared case: \"{title}\" "
        f"(lead quality {score}/100).\n\nReview and accept or decline it: "
        f"{_url('/lawyer')}",
    )


def order_response_client(email: str, lawyer_name: str, accepted: bool) -> None:
    if accepted:
        body = (
            f"{lawyer_name} accepted your case and can now see your contact "
            "details. They will get in touch with you directly."
        )
    else:
        body = (
            f"{lawyer_name} is not able to take your case. You can send it to "
            "another lawyer from the directory."
        )
    send_email(
        email,
        f"{lawyer_name} {'accepted' if accepted else 'declined'} your case",
        f"{body}\n\nYour requests: {_url('/requests')}",
    )


def new_feedback_admin(lawyer_name: str, category: str, comment: str) -> None:
    send_email(
        settings.contact_email,
        f"Lawyer feedback ({category}) from {lawyer_name}",
        f"{comment}\n\nAll feedback: {_url('/admin/feedback')}",
    )


def lawyer_reported_admin(to: str, lawyer_name: str, reason: str, suspended: bool) -> None:
    send_email(
        to,
        f"Lawyer reported: {lawyer_name}" + (" (auto-suspended)" if suspended else ""),
        f"A user reported {lawyer_name} (reason: {reason}).\n"
        + ("The lawyer was suspended automatically and is hidden from the directory.\n"
           if suspended else "")
        + f"Review: {_url('/admin/lawyers')}",
    )


def deadline_reminder(to: str, description: str, when: str, days_left: int) -> None:
    lead = "tomorrow" if days_left <= 1 else f"in {days_left} days"
    send_email(
        to,
        f"Reminder: {description[:60]} ({when})",
        f"A date in your Francesca timeline is {lead}:\n\n  {when}: {description}\n\n"
        f"Open your timeline: {_url('/timeline')}",
    )
