"""Processador end-to-end de NormalizedEvent (multi-plataforma)."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages"))

from loguru import logger  # noqa: E402

from core import db, llm, whatsapp  # noqa: E402
from core.platforms import NormalizedEvent  # noqa: E402

from contexts import EMAIL_WAIT_MINUTES, build_contexto, system_prompt, user_prompt  # noqa: E402
from email_sender import send_email  # noqa: E402
from email_templates import render as render_email  # noqa: E402


async def processar_evento(ev: NormalizedEvent) -> None:
    ctx = build_contexto(ev)
    if ctx is None:
        logger.info(f"[{ev.platform}/{ev.event_kind}] sem ctx de recovery, ignorando.")
        return

    phone = ev.customer.phone
    first_name = ev.customer.first_name or "lead"

    await asyncio.sleep(ctx["wait_minutes"] * 60)

    msg = await llm.gerar_mensagem(system_prompt(), user_prompt(first_name, ctx["contexto_ai"]))
    if not msg:
        logger.warning(f"Mensagem vazia pra {phone}, abortando")
        return

    user_number = ev.customer.user_number
    try:
        await whatsapp.send_message(phone, msg)
        logger.info(f"[{ev.platform}/{ctx['tipo_recovery']}] {phone} ← '{msg[:60]}...'")
    except Exception as e:
        logger.error(f"Falha enviando WhatsApp pra {phone}: {e}")
        await db.insert_followup(user_number, ctx["tipo_recovery"], ctx["produto_id"], msg, status="failed")
        return

    await db.insert_followup(user_number, ctx["tipo_recovery"], ctx["produto_id"], msg, status="completed")

    for extra in ctx["msgs_extras"]:
        await asyncio.sleep(3)
        try:
            await whatsapp.send_message(phone, extra)
        except Exception as e:
            logger.error(f"Falha extra msg {phone}: {e}")

    email_wait = EMAIL_WAIT_MINUTES.get(ctx["tipo_recovery"], 15)
    await asyncio.sleep(email_wait * 60)

    rendered = render_email(ctx["tipo_recovery"], ev, ctx["produto_label"], ctx["link_oferta"])
    if rendered and ev.customer.email:
        subject, html = rendered
        try:
            await send_email(ev.customer.email, subject, html)
            logger.info(f"Email: {ev.customer.email} — {subject}")
        except Exception as e:
            logger.error(f"Falha email pra {ev.customer.email}: {e}")
