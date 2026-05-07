"""
Cron Recovery — Pix/Boleto Vencido (multi-plataforma)
=====================================================
Roda de hora em hora. Busca leads com pix/boleto vencido em qualquer plataforma
registrada (Kiwify, Hotmart, Shopify, ...) e dispara WhatsApp via LLM.

A query lê `eventos_pagamento` agnóstica de plataforma — basta o webhook ter
sido processado e gravado por algum adapter.

    python app.py            # executa o ciclo uma vez
    python app.py --schedule # roda em loop (APScheduler 1h)
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages"))

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # noqa: E402
from loguru import logger  # noqa: E402

from core import db, llm, whatsapp  # noqa: E402
from core.config import get_settings  # noqa: E402

QUERY_VENCIDOS = """
WITH vencidos AS (
  SELECT
    e.platform, e.user_number, e.email, e.customer_name, e.product_name,
    e.charge_amount, e.event_kind, e.pix_expiration, e.boleto_expiry, e.created_at,
    c.produto_interesse, c.link_oferta
  FROM eventos_pagamento e
  LEFT JOIN contatos_agente c ON c.user_number = e.user_number
  WHERE
    (
      -- PIX vencido: criado há mais de 25h (margem de 1h)
      (e.event_kind = 'pix' AND e.created_at < NOW() - INTERVAL '25 hours')
      OR
      -- Boleto vencido: data de expiração passou (formato DD/MM/YYYY)
      (e.event_kind = 'boleto' AND
        CASE WHEN e.boleto_expiry ~ '^\\d{2}/\\d{2}/\\d{4}$'
          THEN TO_DATE(e.boleto_expiry, 'DD/MM/YYYY') < CURRENT_DATE
          ELSE FALSE
        END
      )
    )
    -- Lead não comprou depois
    AND NOT EXISTS (
      SELECT 1 FROM eventos_pagamento e2
      WHERE e2.user_number = e.user_number
      AND e2.event_kind = 'compra_aprovada'
      AND e2.created_at > e.created_at
    )
    -- Lead não está em atendimento humano
    AND NOT EXISTS (
      SELECT 1 FROM contatos_agente c2
      WHERE c2.user_number = e.user_number AND c2.agente = 'off'
    )
    -- Sem conversa recente (não interromper SPIN em andamento)
    AND NOT EXISTS (
      SELECT 1 FROM chat_histories h
      WHERE h.session_id = e.user_number
      AND h.created_at > NOW() - INTERVAL '2 hours'
    )
    -- Não foi processado ainda
    AND NOT EXISTS (
      SELECT 1 FROM follow_up f
      WHERE f.user_number = e.user_number
      AND f.tipo IN ('pix_vencido', 'boleto_vencido')
      AND f.created_at > e.created_at
    )
)
SELECT * FROM vencidos
ORDER BY created_at ASC
LIMIT 20;
"""


def _system_prompt() -> str:
    s = get_settings()
    return (
        f"Você é a {s.agent_name}, consultora comercial da {s.company_name}. "
        "Escreve mensagens de WhatsApp curtas, diretas e personalizadas. "
        "Nunca usa markdown. Nunca usa asteriscos. Texto puro. Máximo 4 linhas."
    )


def _user_prompt(lead: dict) -> str:
    s = get_settings()
    is_pix = lead["event_kind"] == "pix"
    valor = f"{(lead.get('charge_amount') or 0) / 100:.2f}".replace(".", ",")
    nome = (lead.get("customer_name") or "").split(" ")[0] or "lead"
    produto_id = (lead.get("produto_interesse") or "").lower()
    if produto_id == "mentoria":
        produto_label = s.product_b_name
        link = lead.get("link_oferta") or s.product_b_link
    else:
        produto_label = s.product_a_name
        link = lead.get("link_oferta") or s.product_a_link

    if is_pix:
        contexto = (
            f"O pix de R$ {valor} que o lead {nome} gerou para {produto_label} expirou. "
            "Gere uma mensagem natural dizendo que notou que o pix venceu, sem pressão. "
            f"Pergunte se ainda tem interesse e ofereça o link pra gerar um novo pagamento: {link}"
        )
    else:
        venc = lead.get("boleto_expiry") or ""
        contexto = (
            f"O boleto de R$ {valor} que o lead {nome} gerou para {produto_label} venceu (vencimento: {venc}). "
            "Gere uma mensagem natural dizendo que o boleto venceu, sem pressão. "
            f"Pergunte se ainda tem interesse e ofereça o link pra gerar um novo pagamento: {link}"
        )

    return (
        f"Gere UMA mensagem de WhatsApp para o lead {nome}.\n\n"
        f"Contexto:\n{contexto}\n\n"
        "Regras:\n"
        f"1. Você é a {s.agent_name}, do time do {s.agent_owner} na {s.company_name}\n"
        "2. Máximo 4 linhas\n"
        "3. Tom leve, sem pressão, mas mostrando que se importa\n"
        "4. Emojis: no máximo 1-2\n"
        "5. Texto puro, sem markdown, sem asteriscos\n"
        "6. Inclua o link de pagamento na mensagem\n"
        "7. Varie o estilo\n\n"
        "Responda SOMENTE com a mensagem."
    )


async def processar_lead(lead: dict) -> None:
    is_pix = lead["event_kind"] == "pix"
    tipo = "pix_vencido" if is_pix else "boleto_vencido"
    produto = (lead.get("produto_interesse") or "curso").lower()
    phone = (lead.get("user_number") or "").replace("@s.whatsapp.net", "")

    msg = await llm.gerar_mensagem(_system_prompt(), _user_prompt(lead))
    if not msg:
        logger.warning(f"Mensagem vazia para {phone}, pulando")
        return

    try:
        await whatsapp.send_message(phone, msg)
    except Exception as e:
        logger.error(f"Falha enviando WhatsApp pra {phone}: {e}")
        await db.insert_followup(lead["user_number"], tipo, produto, msg, status="failed")
        return

    await db.insert_followup(lead["user_number"], tipo, produto, msg, status="completed")
    logger.info(f"[{tipo}] {phone} ({lead.get('platform','?')}) ← '{msg[:60]}...'")


async def ciclo() -> int:
    rows = await db.fetch(QUERY_VENCIDOS)
    if not rows:
        logger.info("Nenhum vencido pendente.")
        return 0
    logger.info(f"{len(rows)} lead(s) com pagamento vencido. Processando...")
    for row in rows:
        await processar_lead(dict(row))
        await asyncio.sleep(5)
    return len(rows)


async def main_once() -> None:
    try:
        await ciclo()
    finally:
        await db.close_pool()


async def main_scheduled() -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(ciclo, "interval", hours=1, id="cron_vencidos")
    scheduler.start()
    logger.info("Scheduler iniciado. Cron a cada 1h.")
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        scheduler.shutdown()
        await db.close_pool()


if __name__ == "__main__":
    if "--schedule" in sys.argv:
        asyncio.run(main_scheduled())
    else:
        asyncio.run(main_once())
