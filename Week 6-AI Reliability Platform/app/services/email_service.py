"""
Email sending for agent tools (e.g. the Meeting Agent's "email me my
tasks" capability).

Uses Gmail's SMTP server with an App Password — this is the practical way
to send real email from a Gmail account without building a full OAuth
consent-screen flow (which needs a registered Google Cloud project). The
person configures GMAIL_ADDRESS + GMAIL_APP_PASSWORD in .env; without
those set, send_email() fails gracefully instead of crashing the agent.

How to get a Gmail App Password (not the normal account password):
  1. Turn on 2-Step Verification on the Google account.
  2. Go to https://myaccount.google.com/apppasswords
  3. Generate an app password for "Mail" and use that 16-character value
     as GMAIL_APP_PASSWORD.
"""
import smtplib
import logging
from email.mime.text import MIMEText

logger = logging.getLogger("ai_platform.email")

_gmail_address = None
_gmail_app_password = None


def configure(gmail_address: str, gmail_app_password: str):
    global _gmail_address, _gmail_app_password
    _gmail_address = gmail_address
    _gmail_app_password = gmail_app_password


def is_configured() -> bool:
    return bool(_gmail_address and _gmail_app_password)


def send_email(to_address: str, subject: str, body: str) -> dict:
    """Returns {"success": bool, "detail": str}."""
    if not is_configured():
        return {
            "success": False,
            "detail": (
                "Email isn't configured yet. Add GMAIL_ADDRESS and GMAIL_APP_PASSWORD "
                "to your .env file (see docs/AGENTS.md) to enable this."
            ),
        }
    if not to_address:
        return {"success": False, "detail": "No recipient email address on file."}

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = _gmail_address
    msg["To"] = to_address

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(_gmail_address, _gmail_app_password)
            server.sendmail(_gmail_address, [to_address], msg.as_string())
        return {"success": True, "detail": f"Email sent to {to_address}."}
    except Exception as exc:
        logger.error("send_email failed: %s", exc)
        return {"success": False, "detail": f"Failed to send email: {exc}"}
