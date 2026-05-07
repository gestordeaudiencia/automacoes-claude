"""Renderizadores de email por tipo de recovery. Multi-plataforma."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages"))

from core.config import get_settings  # noqa: E402
from core.platforms import NormalizedEvent  # noqa: E402


def _base_html(title: str, body_html: str) -> str:
    s = get_settings()
    return f"""<!DOCTYPE html>
<html><body style="font-family: -apple-system, system-ui, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; color: #1a1a1a;">
<h2 style="color:#0a0a0a;">{title}</h2>
{body_html}
<p style="color:#666;font-size:13px;margin-top:32px;">— {s.company_name}</p>
</body></html>"""


def render(tipo_recovery: str, ev: NormalizedEvent, produto_label: str, link_oferta: str) -> tuple[str, str] | None:
    s = get_settings()
    nome = ev.customer.first_name or ""
    valor = ev.product.value_brl

    if tipo_recovery == "pix_gerado":
        body = f"""
        <p>Oi {nome},</p>
        <p>Seu PIX de R$ {valor} para o <strong>{produto_label}</strong> foi gerado.
        Ele expira em 24 horas ({ev.payment.pix_expiration}).</p>
        <p>Código PIX (copia e cola):</p>
        <pre style="background:#f3f3f3;padding:12px;border-radius:6px;word-break:break-all;">{ev.payment.pix_code}</pre>
        <p><a href="{link_oferta}" style="display:inline-block;background:#10b981;color:white;padding:12px 20px;border-radius:6px;text-decoration:none;">Pagar agora</a></p>
        """
        return (f"Seu PIX do {produto_label} está pronto", _base_html("Pix gerado", body))

    if tipo_recovery == "boleto_gerado":
        body = f"""
        <p>Oi {nome},</p>
        <p>Seu boleto de R$ {valor} para o <strong>{produto_label}</strong> foi emitido.
        Vencimento: {ev.payment.boleto_expiry}.</p>
        <p><a href="{ev.payment.boleto_url}" style="display:inline-block;background:#10b981;color:white;padding:12px 20px;border-radius:6px;text-decoration:none;">Abrir boleto</a></p>
        <p>Linha digitável:</p>
        <pre style="background:#f3f3f3;padding:12px;border-radius:6px;word-break:break-all;">{ev.payment.boleto_barcode}</pre>
        """
        return (f"Seu boleto do {produto_label}", _base_html("Boleto emitido", body))

    if tipo_recovery == "compra_recusada":
        body = f"""
        <p>Oi {nome},</p>
        <p>Tivemos um problema ao processar seu pagamento do <strong>{produto_label}</strong>.</p>
        <p>Pode ser bandeira do cartão, limite ou um detalhe pequeno. Tenta de novo:</p>
        <p><a href="{link_oferta}" style="display:inline-block;background:#10b981;color:white;padding:12px 20px;border-radius:6px;text-decoration:none;">Tentar novamente</a></p>
        <p>Se precisar de ajuda: {s.support_whatsapp_url}</p>
        """
        return ("Tivemos um problema com seu pagamento", _base_html("Pagamento recusado", body))

    if tipo_recovery == "carrinho_abandonado":
        body = f"""
        <p>Oi {nome},</p>
        <p>Vi que você começou o cadastro pro <strong>{produto_label}</strong> mas não finalizou.</p>
        <p>Sou a {s.agent_name}, do time do {s.agent_owner}. Posso te ajudar.</p>
        <p><a href="{link_oferta}" style="display:inline-block;background:#10b981;color:white;padding:12px 20px;border-radius:6px;text-decoration:none;">Voltar pro checkout</a></p>
        """
        return ("Posso te ajudar com algo?", _base_html("Voltando aqui rapidinho", body))

    if tipo_recovery == "onboarding":
        access = ev.payment.access_url or s.club_url
        body = f"""
        <p>Oi {nome}, parabéns pela decisão!</p>
        <p>Acesso ao <strong>{produto_label}</strong>:</p>
        <p><a href="{access}" style="display:inline-block;background:#10b981;color:white;padding:12px 20px;border-radius:6px;text-decoration:none;">Acessar agora</a></p>
        <p>Qualquer coisa, é só responder este email.</p>
        """
        return (f"Bem-vindo(a) ao {produto_label}", _base_html("Bem-vindo!", body))

    return None
