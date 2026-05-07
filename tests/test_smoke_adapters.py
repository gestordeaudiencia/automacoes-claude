"""Smoke tests dos adapters por plataforma.

Cada plataforma: payload exemplo + signature válida → normalize() retorna
NormalizedEvent correto.
"""
import base64
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

# Settings fake (não precisa DB pra esses testes)
os.environ.setdefault("DATABASE_URL", "postgresql://fake/fake")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

from core.platforms import get_adapter, list_platforms  # noqa: E402
from core.platforms.generic import GenericAdapter  # noqa: E402
from core.platforms.registry import register_adapter  # noqa: E402


# ---------- Kiwify ----------

def test_kiwify_signature_e_normalize():
    adapter = get_adapter("kiwify")
    payload = {
        "webhook_event_type": "pix_created",
        "Customer": {"full_name": "João Silva", "email": "j@x.com", "mobile": "11987654321"},
        "Product": {"product_name": "Investidor Coeso", "product_id": "p1"},
        "Commissions": {"charge_amount": "197.00"},
        "pix_code": "00020126...",
        "pix_expiration": "2026-05-08",
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(b"sec", raw, hashlib.sha1).hexdigest()

    assert adapter.validate_signature(raw, {}, {"signature": sig}, "sec") is True
    assert adapter.validate_signature(raw, {}, {"signature": "wrong"}, "sec") is False

    ev = adapter.normalize(payload)
    assert ev.platform == "kiwify"
    assert ev.event_kind == "pix"
    assert ev.customer.first_name == "João"
    assert ev.customer.phone == "5511987654321"
    assert ev.product.value_cents == 19700
    assert ev.payment.pix_code == "00020126..."
    print("OK: Kiwify pix_created → pix")


def test_kiwify_event_kinds():
    a = get_adapter("kiwify")
    cases = [
        ("billet_created", "boleto"),
        ("order_approved", "compra_aprovada"),
        ("order_refused", "recusada"),
        ("abandoned_cart", "carrinho"),
        ("subscription_canceled", "cancelada"),
        ("evento_estranho", "outro"),
    ]
    for raw, expected in cases:
        assert a.event_kind({"webhook_event_type": raw}) == expected, raw
    print("OK: Kiwify event_kind mappings")


# ---------- Hotmart ----------

def test_hotmart_signature_e_normalize():
    adapter = get_adapter("hotmart")
    payload = {
        "event": "PURCHASE_APPROVED",
        "version": "2.0.0",
        "data": {
            "buyer": {"name": "Maria Souza", "email": "m@x.com", "checkout_phone": "11999998888"},
            "purchase": {
                "transaction": "tx1",
                "payment": {"type": "CREDIT_CARD"},
                "price": {"value": 297.00, "currency_value": "BRL"},
            },
            "product": {"id": 123, "name": "Curso XPTO"},
        },
    }

    # Hottok em header
    assert adapter.validate_signature(b"", {"x-hotmart-hottok": "tok"}, {}, "tok") is True
    assert adapter.validate_signature(b"", {"x-hotmart-hottok": "errado"}, {}, "tok") is False
    # Sem secret = aceita
    assert adapter.validate_signature(b"", {}, {}, "") is True

    ev = adapter.normalize(payload)
    assert ev.platform == "hotmart"
    assert ev.event_kind == "compra_aprovada"
    assert ev.customer.first_name == "Maria"
    assert ev.customer.phone == "5511999998888"
    assert ev.product.value_cents == 29700
    assert ev.product.name == "Curso XPTO"
    print("OK: Hotmart PURCHASE_APPROVED → compra_aprovada")


def test_hotmart_billet_pix_distincao():
    a = get_adapter("hotmart")
    base = {"event": "PURCHASE_BILLET_PRINTED", "data": {"purchase": {"payment": {"type": "PIX"}}}}
    assert a.event_kind(base) == "pix"
    base["data"]["purchase"]["payment"]["type"] = "BILLET"
    assert a.event_kind(base) == "boleto"
    print("OK: Hotmart distingue PIX vs BILLET via payment.type")


# ---------- Shopify ----------

def test_shopify_signature_e_normalize():
    adapter = get_adapter("shopify")
    payload = {
        "_topic": "orders/paid",
        "id": 12345,
        "email": "buyer@x.com",
        "phone": "+5511999998888",
        "total_price": "397.00",
        "financial_status": "paid",
        "customer": {"first_name": "Carlos", "last_name": "Lima"},
        "line_items": [{"title": "Camiseta XYZ", "product_id": 99}],
        "order_status_url": "https://shop/orders/12345",
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    sig = base64.b64encode(hmac.new(b"shop-secret", raw, hashlib.sha256).digest()).decode()

    assert adapter.validate_signature(raw, {"x-shopify-hmac-sha256": sig}, {}, "shop-secret") is True
    assert adapter.validate_signature(raw, {"x-shopify-hmac-sha256": "deadbeef"}, {}, "shop-secret") is False

    ev = adapter.normalize(payload)
    assert ev.platform == "shopify"
    assert ev.event_kind == "compra_aprovada"
    assert ev.customer.first_name == "Carlos"
    assert ev.customer.phone == "5511999998888"
    assert ev.product.name == "Camiseta XYZ"
    assert ev.product.value_cents == 39700
    print("OK: Shopify orders/paid → compra_aprovada")


def test_shopify_carrinho():
    a = get_adapter("shopify")
    payload = {"_topic": "checkouts/create", "abandoned_checkout_url": "https://shop/abc"}
    assert a.event_kind(payload) == "carrinho"
    print("OK: Shopify checkouts/create + abandoned → carrinho")


# ---------- Generic Adapter (Eduzz exemplo) ----------

def test_generic_adapter_eduzz_like():
    config = {
        "name": "eduzz",
        "signature": {
            "scheme": "hmac_sha256_header",
            "header": "x-eduzz-signature",
            "encoding": "hex",
        },
        "event_field": "trans_status",
        "event_map": {
            "1": "carrinho",
            "3": "compra_aprovada",
            "8": "recusada",
            "12": "boleto",
        },
        "fields": {
            "customer.name": "cus_name",
            "customer.email": "cus_email",
            "customer.phone": "cus_tel",
            "product.name": "product_name",
            "product.id": "product_cod",
            "product.value_cents_x100": "trans_value",
            "payment.method": "trans_payment_method",
            "payment.boleto_url": "trans_billet_link",
            "payment.boleto_expiry": "trans_billet_due_date",
        },
    }
    register_adapter(GenericAdapter(config))

    payload = {
        "trans_status": "12",
        "cus_name": "Pedro Souza",
        "cus_email": "p@x.com",
        "cus_tel": "11988887777",
        "product_name": "Ebook Y",
        "product_cod": "ebk1",
        "trans_value": "97.00",
        "trans_payment_method": "boleto",
        "trans_billet_link": "https://eduzz/boleto",
        "trans_billet_due_date": "12/05/2026",
    }
    raw = json.dumps(payload).encode()
    sig = hmac.new(b"eduzz-sec", raw, hashlib.sha256).hexdigest()

    a = get_adapter("eduzz")
    assert a.validate_signature(raw, {"x-eduzz-signature": sig}, {}, "eduzz-sec") is True
    assert a.validate_signature(raw, {"x-eduzz-signature": "wrong"}, {}, "eduzz-sec") is False

    ev = a.normalize(payload)
    assert ev.platform == "eduzz"
    assert ev.event_kind == "boleto"
    assert ev.customer.first_name == "Pedro"
    assert ev.customer.phone == "5511988887777"
    assert ev.product.value_cents == 9700
    assert ev.payment.boleto_url == "https://eduzz/boleto"
    print("OK: GenericAdapter Eduzz config-driven")


def test_lastlink_signature_e_normalize():
    adapter = get_adapter("lastlink")
    payload = {
        "Id": "evt_1",
        "Event": "Purchase_Request_Confirmed",
        "Data": {
            "Buyer": {"Name": "Carla Mendes", "Email": "c@x.com", "PhoneNumber": "11966665555"},
            "Products": [{"Id": "p_xyz", "Name": "Curso Pro"}],
            "Payment": {
                "Method": "Pix",
                "Amount": 497.00,
                "PixCode": "00020126Lastlink",
                "PixExpirationDate": "2026-05-08T23:59:00Z",
            },
        },
    }
    raw = json.dumps(payload).encode()
    sig = hmac.new(b"ll-sec", raw, hashlib.sha256).hexdigest()

    assert adapter.validate_signature(raw, {"x-lastlink-signature": sig}, {}, "ll-sec") is True
    assert adapter.validate_signature(raw, {"x-lastlink-signature": f"sha256={sig}"}, {}, "ll-sec") is True
    assert adapter.validate_signature(raw, {"x-lastlink-signature": "errado"}, {}, "ll-sec") is False

    ev = adapter.normalize(payload)
    assert ev.platform == "lastlink"
    assert ev.event_kind == "pix"
    assert ev.customer.first_name == "Carla"
    assert ev.customer.phone == "5511966665555"
    assert ev.product.name == "Curso Pro"
    assert ev.product.value_cents == 49700
    assert ev.payment.pix_code == "00020126Lastlink"
    print("OK: Lastlink Purchase_Request_Confirmed (PIX) → pix")


def test_lastlink_compra_aprovada():
    a = get_adapter("lastlink")
    p = {"Event": "Purchase_Order_Confirmed", "Data": {"Payment": {"Method": "CreditCard"}}}
    assert a.event_kind(p) == "compra_aprovada"
    p["Event"] = "Purchase_Request_Confirmed"
    p["Data"]["Payment"]["Method"] = "Bankslip"
    assert a.event_kind(p) == "boleto"
    print("OK: Lastlink event_kind mappings")


def test_registry():
    plats = list_platforms()
    for required in ("kiwify", "hotmart", "shopify", "lastlink"):
        assert required in plats, required
    print(f"OK: registry expõe {plats}")


def main():
    test_kiwify_signature_e_normalize()
    test_kiwify_event_kinds()
    test_hotmart_signature_e_normalize()
    test_hotmart_billet_pix_distincao()
    test_shopify_signature_e_normalize()
    test_shopify_carrinho()
    test_generic_adapter_eduzz_like()
    test_lastlink_signature_e_normalize()
    test_lastlink_compra_aprovada()
    test_registry()
    print("\nTODOS OS SMOKE TESTS DE ADAPTERS PASSARAM ✓")


if __name__ == "__main__":
    main()
