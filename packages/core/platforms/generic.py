"""Adapter genérico config-driven.

Pra plataformas simples (Eduzz, Kirvano, Lastlink, Pepper, etc) onde você não quer
escrever Python. Define um JSON config com mappings (JSONPath-like) e signature scheme.

Exemplo de config (passar via construtor):

    {
      "name": "eduzz",
      "signature": {
        "scheme": "hmac_sha256_header",
        "header": "x-eduzz-signature",
        "encoding": "hex"
      },
      "event_field": "trans_status",
      "event_map": {
        "1": "carrinho",
        "3": "compra_aprovada",
        "8": "recusada",
        "12": "boleto"
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
        "payment.boleto_expiry": "trans_billet_due_date"
      }
    }

`product.value_cents_x100` significa "campo já está em reais, multiplique por 100".
Se o campo já vem em cents, use `product.value_cents`.
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


def _dotget(obj: Any, path: str) -> Any:
    """Pega obj[a][b][c] dado 'a.b.c'. Retorna '' se path não existe."""
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return ""
        else:
            return ""
        if cur is None:
            return ""
    return cur


class GenericAdapter:
    def __init__(self, config: dict[str, Any]):
        self.name = config["name"]
        self.config = config

    def validate_signature(
        self, raw_body: bytes, headers: Mapping[str, str], query_params: Mapping[str, str], secret: str
    ) -> bool:
        if not secret:
            return True
        sig_cfg = self.config.get("signature") or {}
        scheme = sig_cfg.get("scheme", "")
        if scheme == "none":
            return True

        if scheme == "static_token_header":
            header_name = sig_cfg.get("header", "").lower()
            return hmac.compare_digest(headers.get(header_name, ""), secret)

        if scheme.startswith("hmac_"):
            algo = scheme.split("_")[1]  # sha1, sha256
            digest_mod = hashlib.sha1 if algo == "sha1" else hashlib.sha256
            source = sig_cfg.get("source", "header")  # header | query
            location = sig_cfg.get("header") or sig_cfg.get("query_param", "signature")
            encoding = sig_cfg.get("encoding", "hex")  # hex | base64

            received = ""
            if source == "header":
                received = headers.get(location.lower(), "")
            else:
                received = query_params.get(location, "")

            digest = hmac.new(secret.encode(), raw_body, digest_mod).digest()
            expected = digest.hex() if encoding == "hex" else base64.b64encode(digest).decode()
            return hmac.compare_digest(expected, received)

        return False

    def event_kind(self, payload: dict[str, Any]) -> EventKind:
        event_field = self.config.get("event_field", "event")
        raw_value = str(_dotget(payload, event_field) or "").strip()
        mapping = self.config.get("event_map", {})
        kind = mapping.get(raw_value, "outro")
        return kind  # type: ignore[return-value]

    def normalize(self, payload: dict[str, Any]) -> NormalizedEvent:
        f = self.config.get("fields", {})

        def g(key: str, default: str = "") -> str:
            path = f.get(key)
            if not path:
                return default
            return str(_dotget(payload, path) or default)

        full_name = g("customer.name")
        phone = normalize_phone_br(g("customer.phone"))

        # value_cents pode vir em cents ou em reais (com sufixo _x100)
        value_cents = 0
        if "product.value_cents" in f:
            try:
                value_cents = int(float(g("product.value_cents") or 0))
            except (TypeError, ValueError):
                pass
        elif "product.value_cents_x100" in f:
            try:
                value_cents = int(round(float(g("product.value_cents_x100") or 0) * 100))
            except (TypeError, ValueError):
                pass

        event_field = self.config.get("event_field", "event")
        return NormalizedEvent(
            platform=self.name,
            event_kind=self.event_kind(payload),
            raw_event_type=str(_dotget(payload, event_field) or ""),
            customer=Customer(
                name=full_name,
                first_name=first_name_of(full_name),
                email=g("customer.email"),
                phone=phone,
                user_number=f"{phone}@s.whatsapp.net" if phone else "",
            ),
            product=Product(
                name=g("product.name"),
                id=g("product.id"),
                value_cents=value_cents,
            ),
            payment=Payment(
                pix_code=g("payment.pix_code"),
                pix_expiration=g("payment.pix_expiration"),
                boleto_url=g("payment.boleto_url"),
                boleto_barcode=g("payment.boleto_barcode"),
                boleto_expiry=g("payment.boleto_expiry"),
                access_url=g("payment.access_url"),
                rejection_reason=g("payment.rejection_reason"),
                method=g("payment.method"),
            ),
            raw_payload=payload,
        )
