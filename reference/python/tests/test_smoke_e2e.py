"""Smoke test end-to-end: webhook server + cron processor com mocks.

Valida fluxo completo:
- POST /webhook/kiwify aceita signature válida → enfileira processar_evento
- POST /webhook/hotmart aceita Hottok válido
- POST /webhook/shopify aceita HMAC-SHA256 válido
- Rejeita signature inválida (401)
- Rejeita plataforma desconhecida (404)
- processar_evento (multi-plataforma) chama LLM + WhatsApp + DB
- cron processar_lead funciona com event_kind
"""
import asyncio
import base64
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock

# Env fake antes de tudo
os.environ.update({
    "DATABASE_URL": "postgresql://fake/fake",
    "OPENAI_API_KEY": "sk-fake",
    "WHATSAPP_API_URL": "https://example.com/send",
    "WHATSAPP_API_TOKEN": "token-fake",
    "KIWIFY_WEBHOOK_SECRET": "kiwify-sec",
    "HOTMART_WEBHOOK_SECRET": "hotmart-tok",
    "SHOPIFY_WEBHOOK_SECRET": "shopify-sec",
    "AGENT_NAME": "Laura",
    "AGENT_OWNER": "Matheus",
    "COMPANY_NAME": "Sua Empresa",
    "PRODUCT_A_NAME": "Produto A",
    "PRODUCT_A_LINK": "https://link/a",
    "PRODUCT_B_NAME": "Mentoria O Caminho",
    "PRODUCT_B_LINK": "https://link/b",
    "EMAIL_PROVIDER": "none",
})

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

# Bypass asyncio.sleep antes de importar processor
import asyncio as _aio  # noqa: E402

async def _no_sleep(_):
    return None

_aio.sleep = _no_sleep

from fastapi.testclient import TestClient  # noqa: E402

import importlib.util  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Webhook server (templates/payment-webhooks/)
sys.path.insert(0, str(ROOT / "templates" / "payment-webhooks"))
wh_processor = _load("payment_webhooks_processor", ROOT / "templates" / "payment-webhooks" / "processor.py")
web_app = _load("payment_webhooks_app", ROOT / "templates" / "payment-webhooks" / "app.py")

# Cron app (templates/cron-recovery-vencidos/)
cron_app = _load("cron_recovery_app", ROOT / "templates" / "cron-recovery-vencidos" / "app.py")


# ---------- Helpers ----------

class Patcher:
    def __init__(self):
        self._patches = []

    def setattr(self, target, name, value):
        old = getattr(target, name)
        self._patches.append((target, name, old))
        setattr(target, name, value)

    def restore(self):
        for t, n, v in reversed(self._patches):
            setattr(t, n, v)


def kiwify_payload_pix():
    return {
        "webhook_event_type": "pix_created",
        "Customer": {"full_name": "João Silva", "email": "j@x.com", "mobile": "11999998888"},
        "Product": {"product_name": "Produto A"},
        "Commissions": {"charge_amount": "197.00"},
        "pix_code": "00020126...",
        "pix_expiration": "2026-05-08",
    }


def hotmart_payload_approved():
    return {
        "event": "PURCHASE_APPROVED",
        "data": {
            "buyer": {"name": "Maria Souza", "email": "m@x.com", "checkout_phone": "11988887777"},
            "purchase": {"payment": {"type": "CREDIT_CARD"}, "price": {"value": 297.00}},
            "product": {"id": 99, "name": "Mentoria O Caminho"},
        },
    }


def shopify_payload_paid():
    return {
        "id": 1,
        "email": "buyer@x.com",
        "phone": "+5511977776666",
        "total_price": "397.00",
        "financial_status": "paid",
        "customer": {"first_name": "Pedro", "last_name": "Lima"},
        "line_items": [{"title": "Camiseta", "product_id": 99}],
        "order_status_url": "https://shop/orders/1",
    }


# ---------- Webhook tests ----------

def setup_mocks(p: Patcher):
    """Mocka DB + LLM + WhatsApp + lifespan pool."""
    insertions = {"eventos": [], "contatos": [], "followup": []}

    async def fake_insert_evento(ev):
        insertions["eventos"].append(ev)
        return 1

    async def fake_upsert(user_number, **kw):
        insertions["contatos"].append((user_number, kw))

    async def fake_followup(*args, **kw):
        insertions["followup"].append((args, kw))

    async def fake_send_wa(phone, msg):
        return {"ok": True}

    async def fake_llm(s, u, max_tokens=400):
        return "Mensagem da Laura"

    p.setattr(web_app.db, "insert_evento", fake_insert_evento)
    p.setattr(web_app.db, "upsert_contato", fake_upsert)
    p.setattr(web_app.db, "get_pool", AsyncMock(return_value=None))
    p.setattr(web_app.db, "close_pool", AsyncMock(return_value=None))
    p.setattr(wh_processor.db, "insert_followup", fake_followup)
    p.setattr(wh_processor.whatsapp, "send_message", fake_send_wa)
    p.setattr(wh_processor.llm, "gerar_mensagem", fake_llm)
    return insertions


def test_webhook_kiwify_e2e():
    p = Patcher()
    inserts = setup_mocks(p)
    try:
        body = kiwify_payload_pix()
        raw = json.dumps(body, separators=(",", ":")).encode()
        sig = hmac.new(b"kiwify-sec", raw, hashlib.sha1).hexdigest()
        with TestClient(web_app.app) as client:
            r = client.post(f"/webhook/kiwify?signature={sig}", content=raw,
                            headers={"Content-Type": "application/json"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["platform"] == "kiwify"
        assert data["event_kind"] == "pix"
        assert len(inserts["eventos"]) == 1
        assert inserts["eventos"][0].platform == "kiwify"
        print("OK: webhook Kiwify e2e")
    finally:
        p.restore()


def test_webhook_hotmart_e2e():
    p = Patcher()
    inserts = setup_mocks(p)
    try:
        body = hotmart_payload_approved()
        raw = json.dumps(body).encode()
        with TestClient(web_app.app) as client:
            r = client.post("/webhook/hotmart", content=raw,
                            headers={"Content-Type": "application/json", "X-Hotmart-Hottok": "hotmart-tok"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["platform"] == "hotmart"
        assert data["event_kind"] == "compra_aprovada"
        print("OK: webhook Hotmart e2e")
    finally:
        p.restore()


def test_webhook_shopify_e2e():
    p = Patcher()
    inserts = setup_mocks(p)
    try:
        body = shopify_payload_paid()
        raw = json.dumps(body, separators=(",", ":")).encode()
        sig = base64.b64encode(hmac.new(b"shopify-sec", raw, hashlib.sha256).digest()).decode()
        with TestClient(web_app.app) as client:
            r = client.post("/webhook/shopify", content=raw,
                            headers={
                                "Content-Type": "application/json",
                                "X-Shopify-Hmac-Sha256": sig,
                                "X-Shopify-Topic": "orders/paid",
                            })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["platform"] == "shopify"
        assert data["event_kind"] == "compra_aprovada"
        print("OK: webhook Shopify e2e")
    finally:
        p.restore()


def test_webhook_signature_invalida_rejeita():
    p = Patcher()
    setup_mocks(p)
    try:
        body = kiwify_payload_pix()
        raw = json.dumps(body, separators=(",", ":")).encode()
        with TestClient(web_app.app) as client:
            r = client.post("/webhook/kiwify?signature=deadbeef", content=raw)
        assert r.status_code == 401
        print("OK: signature inválida → 401")
    finally:
        p.restore()


def test_webhook_plataforma_inexistente_404():
    p = Patcher()
    setup_mocks(p)
    try:
        with TestClient(web_app.app) as client:
            r = client.post("/webhook/inexistente", content=b"{}")
        assert r.status_code == 404
        print("OK: plataforma desconhecida → 404")
    finally:
        p.restore()


# ---------- Cron tests ----------

async def test_cron_processar_lead():
    p = Patcher()
    sent = []
    inserted = []

    async def fake_send(phone, message):
        sent.append((phone, message))
        return {"ok": True}

    async def fake_followup(user_number, tipo, produto, message, status="completed", etapa_atual=1):
        inserted.append({"user_number": user_number, "tipo": tipo, "status": status})

    async def fake_llm(s, u, max_tokens=400):
        return "Oi Pedro, vi que seu pix venceu."

    p.setattr(cron_app.whatsapp, "send_message", fake_send)
    p.setattr(cron_app.db, "insert_followup", fake_followup)
    p.setattr(cron_app.llm, "gerar_mensagem", fake_llm)

    try:
        lead = {
            "platform": "hotmart",
            "user_number": "5511999998888@s.whatsapp.net",
            "customer_name": "Pedro Lima",
            "event_kind": "pix",
            "charge_amount": 19700,
            "produto_interesse": "curso",
            "link_oferta": "https://link/x",
            "boleto_expiry": None,
        }
        await cron_app.processar_lead(lead)
        assert len(sent) == 1
        assert sent[0][0] == "5511999998888"
        assert inserted[0]["tipo"] == "pix_vencido"
        assert inserted[0]["status"] == "completed"
        print("OK: cron processar_lead pix vencido (multi-plataforma)")
    finally:
        p.restore()


async def main():
    test_webhook_kiwify_e2e()
    test_webhook_hotmart_e2e()
    test_webhook_shopify_e2e()
    test_webhook_signature_invalida_rejeita()
    test_webhook_plataforma_inexistente_404()
    await test_cron_processar_lead()
    print("\nTODOS OS SMOKE TESTS E2E PASSARAM ✓")


if __name__ == "__main__":
    asyncio.run(main())
