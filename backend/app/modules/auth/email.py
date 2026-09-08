import asyncio
import smtplib
from email.message import EmailMessage

from app.core.config import settings


async def send_password_reset_email(email: str, token: str) -> None:
    if not all((settings.smtp_host, settings.smtp_username, settings.smtp_password, settings.smtp_from)):
        raise RuntimeError("SMTP is not configured")
    reset_url = f"{settings.password_reset_base_url}?token={token}"
    message = EmailMessage()
    message["Subject"] = "Reset your ShuleLink password"
    message["From"] = settings.smtp_from
    message["To"] = email
    message.set_content(
        "A password reset was requested for your ShuleLink account.\n\n"
        f"Use this link to set a new password: {reset_url}\n\n"
        f"This link expires in {settings.password_reset_minutes} minutes and can only be used once. "
        "If you did not request this, you can safely ignore this message."
    )

    def _send() -> None:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_starttls:
                server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)

    await asyncio.to_thread(_send)
