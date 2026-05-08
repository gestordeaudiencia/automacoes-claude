"""Envia email via provider configurado (Resend ou nenhum)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages"))

import httpx
from loguru import logger

from core.config import get_settings


async def send_email(to: str, subject: str, html: str) -> dict | None:
    s = get_settings()
    if s.email_provider == "none" or not to:
        logger.info(f"[email skipped] to={to} subject={subject!r}")
        return None
    if s.email_provider == "resend":
        return await _send_resend(to, subject, html, s)
    raise ValueError(f"Email provider não suportado: {s.email_provider}")


async def _send_resend(to: str, subject: str, html: str, s) -> dict:
    headers = {"Authorization": f"Bearer {s.resend_api_key}", "Content-Type": "application/json"}
    body = {"from": s.email_from, "to": [to], "subject": subject, "html": html}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post("https://api.resend.com/emails", headers=headers, json=body)
        r.raise_for_status()
        return r.json()
