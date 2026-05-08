"""Adapter Hotmart.

Hotmart envia eventos com schema:
{
  "id": "...",
  "event": "PURCHASE_APPROVED" | "PURCHASE_BILLET_PRINTED" | "PURCHASE_REFUSED" | ...,
  "version": "2.0.0",
  "data": {
    "buyer": { "name", "email", "checkout_phone", ... },
    "purchase": {
      "transaction": "...",
      "payment": { "type": "PIX"|"BILLET"|"CREDIT_CARD", "refusal_reason"?, ... },
      "price": { "value": 197.0, "currency_value": "BRL" },
      "checkout_country": { ... },
      "offer": { "code", ... },
      ...
    },
    "product": { "id", "name", "ucode" }
  }
}

Validação: header `X-Hotmart-Hottok` (token estático configurado na Hotmart).
Algumas integrações usam HMAC; aqui implementamos o caso padrão (token estático).
"""
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


class HotmartAdapter:
    name = "hotmart"

    def validate_signature(
        self, raw_body: bytes, headers: Mapping[str, str], query_params: Mapping[str, str], secret: str
    ) -> bool:
        if not secret:
            return True
        token = headers.get("x-hotmart-hottok") or headers.get("hottok") or query_params.get("hottok", "")
        return hmac.compare_digest(token, secret)

    def event_kind(self, payload: dict[str, Any]) -> EventKind:
        evt = (payload.get("event") or "").upper()
        purchase = (payload.get("data") or {}).get("purchase") or {}
        payment_type = ((purchase.get("payment") or {}).get("type") or "").upper()

        if evt == "PURCHASE_APPROVED":
            return "compra_aprovada"
        if evt == "PURCHASE_REFUSED":
            return "recusada"
        if evt == "PURCHASE_BILLET_PRINTED":
            return "boleto" if payment_type == "BILLET" else "pix"
        if evt == "PURCHASE_PROTEST":
            return "recusada"
        if evt == "PURCHASE_CANCELED":
            return "cancelada"
        if evt == "PURCHASE_OUT_OF_SHOPPING_CART":
            return "carrinho"
        if evt == "PURCHASE_COMPLETE":
            return "compra_aprovada"
        if evt == "SUBSCRIPTION_CANCELLATION":
            return "cancelada"
        return "outro"

    def normalize(self, payload: dict[str, Any]) -> NormalizedEvent:
        data = payload.get("data") or {}
        buyer = data.get("buyer") or {}
        purchase = data.get("purchase") or {}
        product = data.get("product") or {}
        payment = purchase.get("payment") or {}
        price = purchase.get("price") or {}
        offer = purchase.get("offer") or {}

        full_name = buyer.get("name") or ""
        phone = normalize_phone_br(buyer.get("checkout_phone") or buyer.get("phone") or "")
        try:
            value_cents = int(round(float(price.get("value") or 0) * 100))
        except (TypeError, ValueError):
            value_cents = 0

        # Hotmart pix data fica em purchase.payment.pix_code / pix_expiration_date
        pix_code = payment.get("pix_code") or payment.get("pix") or ""
        pix_exp = payment.get("pix_expiration_date") or payment.get("pix_expiration") or ""
        billet_url = payment.get("billet_url") or payment.get("billet_link") or ""
        billet_barcode = payment.get("billet_barcode") or ""
        billet_due = purchase.get("date_next_charge") or payment.get("billet_expiration") or ""
        rejection = payment.get("refusal_reason") or ""
        access_url = (data.get("subscription") or {}).get("subscriber_url") or offer.get("payment_link") or ""

        return NormalizedEvent(
            platform=self.name,
            event_kind=self.event_kind(payload),
            raw_event_type=payload.get("event", ""),
            customer=Customer(
                name=full_name,
                first_name=first_name_of(full_name),
                email=buyer.get("email", ""),
                phone=phone,
                user_number=f"{phone}@s.whatsapp.net" if phone else "",
            ),
            product=Product(
                name=product.get("name", ""),
                id=str(product.get("id") or product.get("ucode") or ""),
                value_cents=value_cents,
            ),
            payment=Payment(
                pix_code=pix_code,
                pix_expiration=pix_exp,
                boleto_url=billet_url,
                boleto_barcode=billet_barcode,
                boleto_expiry=billet_due,
                access_url=access_url,
                rejection_reason=rejection,
                method=(payment.get("type") or "").lower(),
            ),
            raw_payload=payload,
        )
