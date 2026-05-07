"""Adapter Kiwify."""
import hashlib
import hmac
import json
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


class KiwifyAdapter:
    name = "kiwify"

    def validate_signature(
        self, raw_body: bytes, headers: Mapping[str, str], query_params: Mapping[str, str], secret: str
    ) -> bool:
        if not secret:
            return True
        signature = query_params.get("signature", "")
        # Try raw bytes
        expected_raw = hmac.new(secret.encode(), raw_body, hashlib.sha1).hexdigest()
        if hmac.compare_digest(expected_raw, signature):
            return True
        # Fallback: re-stringify (compat com n8n)
        try:
            body = json.loads(raw_body)
            re_stringified = json.dumps(body, separators=(",", ":")).encode()
            expected_re = hmac.new(secret.encode(), re_stringified, hashlib.sha1).hexdigest()
            return hmac.compare_digest(expected_re, signature)
        except Exception:
            return False

    def event_kind(self, payload: dict[str, Any]) -> EventKind:
        et = (payload.get("webhook_event_type") or "").lower()
        if et == "pix_created":
            return "pix"
        if et in ("billet_created", "boleto_created"):
            return "boleto"
        if et == "order_approved":
            return "compra_aprovada"
        if et == "order_refused":
            return "recusada"
        if et in ("cart_abandoned", "abandoned_cart"):
            return "carrinho"
        if et == "subscription_canceled":
            return "cancelada"
        if et == "subscription_renewed":
            return "renovacao"
        return "outro"

    def normalize(self, payload: dict[str, Any]) -> NormalizedEvent:
        customer = payload.get("Customer", {}) or {}
        product = payload.get("Product", {}) or {}
        commissions = payload.get("Commissions", {}) or {}

        full_name = customer.get("full_name") or customer.get("first_name") or ""
        phone = normalize_phone_br(customer.get("mobile") or customer.get("phone") or "")
        try:
            value_cents = int(float(commissions.get("charge_amount") or 0) * 100)
        except (TypeError, ValueError):
            value_cents = 0

        return NormalizedEvent(
            platform=self.name,
            event_kind=self.event_kind(payload),
            raw_event_type=payload.get("webhook_event_type", ""),
            customer=Customer(
                name=full_name,
                first_name=first_name_of(full_name),
                email=customer.get("email", ""),
                phone=phone,
                user_number=f"{phone}@s.whatsapp.net" if phone else "",
            ),
            product=Product(
                name=product.get("product_name", ""),
                id=product.get("product_id", ""),
                value_cents=value_cents,
            ),
            payment=Payment(
                pix_code=payload.get("pix_code", "") if isinstance(payload.get("pix_code"), str) else "",
                pix_expiration=payload.get("pix_expiration", "") or "",
                boleto_url=payload.get("boleto_URL") or payload.get("boleto_url", "") or "",
                boleto_barcode=payload.get("boleto_barcode", "") or "",
                boleto_expiry=payload.get("boleto_expiry_date", "") or "",
                access_url=payload.get("access_url", "") or "",
                rejection_reason=payload.get("card_rejection_reason", "") or "",
                method=payload.get("payment_method", "") or "",
            ),
            raw_payload=payload,
        )
