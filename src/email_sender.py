from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .config import env, env_int, load_dotenv


def build_message(subject: str, body: str, to_addr: str, from_addr: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["To"] = to_addr
    msg["From"] = from_addr
    msg.set_content(body)
    return msg


def send_email(subject: str, body: str, dry_run: bool = False) -> EmailMessage:
    load_dotenv()
    to_addr = env("MAIL_TO")
    from_addr = env("MAIL_FROM")
    password = env("GMAIL_APP_PASSWORD")
    host = env("SMTP_HOST", "smtp.gmail.com")
    port = env_int("SMTP_PORT", 587)
    if not to_addr or not from_addr:
        raise RuntimeError("MAIL_TO and MAIL_FROM are required for email sending.")
    msg = build_message(subject, body, to_addr, from_addr)
    if dry_run:
        return msg
    if not password:
        raise RuntimeError("GMAIL_APP_PASSWORD is required unless dry_run=True.")
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(from_addr, password)
        smtp.send_message(msg)
    return msg


def can_send_email() -> bool:
    load_dotenv()
    return bool(env("MAIL_TO") and env("MAIL_FROM") and env("GMAIL_APP_PASSWORD"))

