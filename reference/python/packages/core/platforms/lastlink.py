"""Adapter Lastlink.

Lastlink envia POST com schema (referência: docs Lastlink, formato 2024+):
{
  "Id": "...",
  "Event": "Purchase_Order_Confirmed" | "Purchase_Request_Confirmed" |
           "Purchase_Request_Expired" | "Subscription_Canceled" | ...,
  "CreatedAt": "...",
  "Data": {
    "Buyer": {"Name", "Email", "PhoneNumber", "Document"},
    "Products": [{"Id", "Name", ...}],
    "Payment": {
      "Method": "CreditCard" | "Pix" | "Bankslip",
      "PixCode" / "PixCopyPaste"?,
      "PixExpirationDate"?,
      "BankSlipUrl"?,
      "BankSlipBarcode"?,
      "BankSlipDueDate"?,
      "Amount" (em reais),
      ...
    },
    "Subscriptions": [{...}]?,
    "Offer": {"Url"?},
  }
}

Validação: header `X-Lastlink-Signature` (HMAC-SHA256 hex sobre raw body).
Se Lastlink tiver schema diferente na sua conta, ajuste os campos abaixo —
o teste smoke valida com payload sintético; rode primeiro contra um webhook real
e ajuste se necessário.
"""
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


class LastlinkAdapter:
    name = "lastlink"

    def validate_signature(
        self, raw_body: bytes, headers: Mapping[str, str], query_params: Mapping[str, str], secret: str
    ) -> bool:
        if not secret:
            return True
        sig = headers.get("x-lastlink-signature") or headers.get("x-hub-signature-256", "")
        # Alguns setups mandam "sha256=<hex>" — extrai
        if sig.startswith("sha256="):
            sig = sig.split("=", 1)[1]
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)

    def event_kind(self, payload: dict[str, Any]) -> EventKind:
        evt = (payload.get("Event") or "").lower()
        method = (((payload.get("Data") or {}).get("Payment") or {}).get("Method") or "").lower()

        if evt in ("purchase_order_confirmed", "purchase_approved"):
            return "compra_aprovada"
        if evt in ("purchase_request_confirmed", "purchase_pending_payment", "purchase_request_created"):
            if "pix" in method:
                return "pix"
            if "bankslip" in method or "boleto" in method:
                return "boleto"
            return "outro"
        if evt in ("purchase_request_expired", "purchase_canceled", "subscription_canceled"):
            return "cancelada"
        if evt in ("purchase_refused", "purchase_failed"):
            return "recusada"
        if evt in ("abandoned_cart", "purchase_abandoned"):
            return "carrinho"
        if evt in ("subscription_renewed",):
            return "renovacao"
        return "outro"

    def normalize(self, payload: dict[str, Any]) -> NormalizedEvent:
        data = payload.get("Data") or {}
        buyer = data.get("Buyer") or {}
        products = data.get("Products") or []
        first_product = products[0] if products else {}
        payment = data.get("Payment") or {}
        offer = data.get("Offer") or {}

        full_name = buyer.get("Name") or ""
        phone = normalize_phone_br(buyer.get("PhoneNumber") or buyer.get("Phone") or "")
        try:
            value_cents = int(round(float(payment.get("Amount") or payment.get("TotalAmount") or 0) * 100))
        except (TypeError, ValueError):
            value_cents = 0

        return NormalizedEvent(
            platform=self.name,
            event_kind=self.event_kind(payload),
            raw_event_type=payload.get("Event", ""),
            customer=Customer(
                name=full_name,
                first_name=first_name_of(full_name),
                email=buyer.get("Email", ""),
                phone=phone,
                user_number=f"{phone}@s.whatsapp.net" if phone else "",
            ),
            product=Product(
                name=first_product.get("Name", ""),
                id=str(first_product.get("Id") or ""),
                value_cents=value_cents,
            ),
            payment=Payment(
                pix_code=payment.get("PixCode") or payment.get("PixCopyPaste") or "",
                pix_expiration=payment.get("PixExpirationDate") or "",
                boleto_url=payment.get("BankSlipUrl") or payment.get("BoletoUrl") or "",
                boleto_barcode=payment.get("BankSlipBarcode") or payment.get("BoletoBarcode") or "",
                boleto_expiry=payment.get("BankSlipDueDate") or payment.get("BoletoExpiry") or "",
                access_url=offer.get("Url") or data.get("AccessUrl") or "",
                rejection_reason=payment.get("RefusalReason") or "",
                method=(payment.get("Method") or "").lower(),
            ),
            raw_payload=payload,
        )
