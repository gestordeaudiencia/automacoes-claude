"""Adapter Shopify.

Shopify webhooks docs: https://shopify.dev/docs/apps/build/webhooks/configuration/https
- Header `X-Shopify-Hmac-Sha256` (base64 do HMAC-SHA256 sobre raw body)
- Header `X-Shopify-Topic` (ex: "orders/paid", "checkouts/create")

Mapping de tópicos pra event_kind interno:
- orders/paid               → compra_aprovada
- orders/cancelled          → cancelada
- checkouts/create          → carrinho (se abandoned_at preenchido)
- checkouts/update          → carrinho (idem)
- orders/create (pendente)  → pix/boleto se gateway = mercadopago
"""
import base64
import hashlib
import hmac
from typing import Any, Mapping

from .base import (
    Customer,
    EventKind,
    NormalizedEvent,
    Payment,
    Product,
    first_name_of,
    normalize_phone_br,
)


class ShopifyAdapter:
    name = "shopify"

    def validate_signature(
        self, raw_body: bytes, headers: Mapping[str, str], query_params: Mapping[str, str], secret: str
    ) -> bool:
        if not secret:
            return True
        sig = headers.get("x-shopify-hmac-sha256") or headers.get("x-shopify-hmac-sha-256", "")
        if not sig:
            return False
        digest = hmac.new(secret.encode(), raw_body, hashlib.sha256).digest()
        expected = base64.b64encode(digest).decode()
        return hmac.compare_digest(expected, sig)

    def event_kind(self, payload: dict[str, Any]) -> EventKind:
        topic = (payload.get("_topic") or "").lower()  # injetado pelo handler
        gateway = (payload.get("gateway") or "").lower()
        financial = (payload.get("financial_status") or "").lower()

        if topic == "orders/paid" or financial == "paid":
            return "compra_aprovada"
        if topic == "orders/cancelled" or financial == "voided":
            return "cancelada"
        if topic in ("orders/create",) and financial == "pending":
            if "mercado" in gateway or "pix" in gateway:
                return "pix"
            if "boleto" in gateway:
                return "boleto"
        if topic in ("checkouts/create", "checkouts/update"):
            if payload.get("abandoned_checkout_url") or payload.get("completed_at") is None:
                return "carrinho"
        return "outro"

    def normalize(self, payload: dict[str, Any]) -> NormalizedEvent:
        customer = payload.get("customer") or {}
        billing = payload.get("billing_address") or payload.get("shipping_address") or {}
        line_items = payload.get("line_items") or []

        full_name = (
            f"{customer.get('first_name','')} {customer.get('last_name','')}".strip()
            or billing.get("name", "")
        )
        email = customer.get("email") or payload.get("email") or billing.get("email", "")
        phone_raw = customer.get("phone") or payload.get("phone") or billing.get("phone", "")
        phone = normalize_phone_br(phone_raw)

        try:
            total_cents = int(round(float(payload.get("total_price") or 0) * 100))
        except (TypeError, ValueError):
            total_cents = 0

        product_name = ", ".join((li.get("title") or "") for li in line_items if li.get("title"))[:200]
        product_id = ",".join(str(li.get("product_id") or "") for li in line_items)

        # PIX/Boleto via metadata do Mercado Pago (estilo plugin)
        attributes = payload.get("note_attributes") or []
        meta = {a.get("name", "").lower(): a.get("value", "") for a in attributes if isinstance(a, dict)}

        return NormalizedEvent(
            platform=self.name,
            event_kind=self.event_kind(payload),
            raw_event_type=payload.get("_topic", ""),
            customer=Customer(
                name=full_name,
                first_name=first_name_of(full_name),
                email=email,
                phone=phone,
                user_number=f"{phone}@s.whatsapp.net" if phone else "",
            ),
            product=Product(
                name=product_name,
                id=product_id,
                value_cents=total_cents,
            ),
            payment=Payment(
                pix_code=meta.get("pix_code", ""),
                pix_expiration=meta.get("pix_expiration", ""),
                boleto_url=meta.get("boleto_url", ""),
                boleto_barcode=meta.get("boleto_barcode", ""),
                boleto_expiry=meta.get("boleto_expiry", ""),
                access_url=payload.get("order_status_url", ""),
                rejection_reason=payload.get("cancel_reason", "") or "",
                method=(payload.get("gateway") or "").lower(),
            ),
            raw_payload=payload,
        )
