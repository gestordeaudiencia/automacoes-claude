"""Builders de contexto pra LLM por tipo de evento. Multi-plataforma.

Recebe NormalizedEvent (do core.platforms) — não conhece plataforma específica.
"""
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages"))

from core.config import get_settings  # noqa: E402
from core.platforms import NormalizedEvent  # noqa: E402


def _produto_resolve(ev: NormalizedEvent) -> tuple[str, str, str]:
    """Decide produto_id (curso|mentoria), label e link com base no nome do produto.
    Convenção simples: se nome contém 'mentoria' ou 'caminho' → mentoria.
    Cliente customiza editando esta função.
    """
    s = get_settings()
    name = (ev.product.name or "").lower()
    if "mentoria" in name or "caminho" in name:
        return "mentoria", s.product_b_name, s.product_b_link
    return "curso", s.product_a_name, s.product_a_link


def system_prompt() -> str:
    s = get_settings()
    return (
        f"Você é a {s.agent_name}, consultora comercial da {s.company_name}, do time do {s.agent_owner}. "
        "Escreve mensagens de WhatsApp curtas, diretas e personalizadas. "
        "Nunca use markdown. Nunca use asteriscos. Texto puro. Máximo 4 linhas. Varie o estilo."
    )


def user_prompt(first_name: str, contexto_ai: str) -> str:
    s = get_settings()
    return (
        f"Gere UMA mensagem de WhatsApp para o lead {first_name}.\n\n"
        f"Contexto:\n{contexto_ai}\n\n"
        "Regras:\n"
        f"1. Você é a {s.agent_name}, do time do {s.agent_owner} na {s.company_name}\n"
        "2. Máximo 4 linhas\n"
        "3. Tom profissional, próximo e confiante\n"
        "4. Emojis: no máximo 1-2\n"
        "5. Texto puro, sem markdown, sem asteriscos, sem negrito\n"
        "6. Varie o estilo a cada chamada — não comece sempre igual\n"
        "7. OBEDEÇA as instruções do contexto sobre incluir ou NÃO incluir links/códigos\n\n"
        "Responda SOMENTE com a mensagem."
    )


def build_contexto(ev: NormalizedEvent) -> dict[str, Any] | None:
    s = get_settings()
    first = ev.customer.first_name or "lead"
    valor = ev.product.value_brl
    produto_id, produto_label, link_default = _produto_resolve(ev)
    produto_artigo = f"a {produto_label}" if produto_id == "mentoria" else f"o {produto_label}"

    if ev.event_kind == "carrinho":
        return {
            "tipo_recovery": "carrinho_abandonado",
            "produto_id": produto_id,
            "produto_label": produto_label,
            "link_oferta": link_default,
            "wait_minutes": 30,
            "msgs_extras": [],
            "contexto_ai": (
                f"O lead {first} estava no checkout do {produto_label} mas não finalizou. "
                f"Gere uma mensagem consultiva de primeiro contato. Se apresente como {s.agent_name} "
                f"do time do {s.agent_owner} na {s.company_name}. Diga que viu o interesse dele no produto "
                "(mencione pelo nome). Pergunte se ficou alguma dúvida ou se quer entender melhor como "
                "funciona. Tom leve, sem pressão. NÃO inclua link. NÃO mencione preço. NÃO tente recuperar "
                "a venda diretamente. O objetivo é ABRIR UMA CONVERSA."
            ),
        }

    if ev.event_kind == "pix":
        return {
            "tipo_recovery": "pix_gerado",
            "produto_id": produto_id,
            "produto_label": produto_label,
            "link_oferta": link_default,
            "wait_minutes": 2,
            "msgs_extras": [ev.payment.pix_code] if ev.payment.pix_code else [],
            "contexto_ai": (
                f"O lead {first} gerou um PIX de R$ {valor} para o produto {produto_label}. "
                f"O PIX expira em 24 horas ({ev.payment.pix_expiration}). Gere uma mensagem confirmando "
                "que o pix foi gerado, que expira em 24h, e avise que vai mandar o código pix na próxima "
                "mensagem pra facilitar. Tom animado mas não forçado. NÃO inclua o código pix na mensagem."
            ),
        }

    if ev.event_kind == "boleto":
        extras = [m for m in (ev.payment.boleto_url, ev.payment.boleto_barcode) if m]
        return {
            "tipo_recovery": "boleto_gerado",
            "produto_id": produto_id,
            "produto_label": produto_label,
            "link_oferta": link_default,
            "wait_minutes": 3,
            "msgs_extras": extras,
            "contexto_ai": (
                f"O lead {first} gerou um boleto de R$ {valor} para o produto {produto_label}. "
                f"Vence em {ev.payment.boleto_expiry}. Gere uma mensagem confirmando a emissão, "
                "mencionando a data de vencimento, e avise que vai mandar o link e o código na próxima "
                "mensagem. NÃO inclua links ou códigos na mensagem."
            ),
        }

    if ev.event_kind == "recusada":
        rejection = ev.payment.rejection_reason
        rej_str = f" (motivo: {rejection})" if rejection else ""
        return {
            "tipo_recovery": "compra_recusada",
            "produto_id": produto_id,
            "produto_label": produto_label,
            "link_oferta": link_default,
            "wait_minutes": 1,
            "msgs_extras": [],
            "contexto_ai": (
                f"O lead {first} tentou comprar {produto_artigo} mas o pagamento foi recusado{rej_str}. "
                "Gere uma mensagem empática dizendo que houve um probleminha no pagamento, sem expor "
                "detalhes técnicos. Sugira tentar com outro cartão, pix ou boleto. Pergunte se precisa "
                "de ajuda. NÃO inclua link de pagamento na mensagem."
            ),
        }

    if ev.event_kind == "compra_aprovada":
        access = ev.payment.access_url or s.club_url
        extra_msg = ""
        if produto_id == "mentoria":
            extra_msg = " Mencione que em breve receberá as informações da turma."
        return {
            "tipo_recovery": "onboarding",
            "produto_id": produto_id,
            "produto_label": produto_label,
            "link_oferta": link_default,
            "wait_minutes": 1,
            "msgs_extras": [access] if access else [],
            "contexto_ai": (
                f"O lead {first} COMPROU {produto_artigo}! Gere uma mensagem de boas-vindas calorosa. "
                f"Parabenize pela decisão. Diga que o {s.agent_owner} vai ficar feliz. Avise que vai "
                f"mandar o link de acesso na próxima mensagem.{extra_msg} NÃO inclua links na mensagem."
            ),
        }

    return None


EMAIL_WAIT_MINUTES = {
    "pix_gerado": 10,
    "boleto_gerado": 15,
    "compra_recusada": 10,
    "carrinho_abandonado": 120,
    "onboarding": 5,
}
