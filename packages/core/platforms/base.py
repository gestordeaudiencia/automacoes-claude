"""Interface comum pra plataformas de pagamento/checkout.

Cada plataforma (Kiwify, Hotmart, Shopify, etc) implementa um PlatformAdapter
que sabe validar assinatura, normalizar payload e mapear evento → kind interno.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Protocol, runtime_checkable

EventKind = Literal[
    "pix",
    "boleto",
    "compra_aprovada",
    "recusada",
    "carrinho",
    "cancelada",
    "renovacao",
    "outro",
]


@dataclass
class Customer:
    name: str = ""
    first_name: str = ""
    email: str = ""
    phone: str = ""              # apenas dígitos, com DDI 55 prefixado
    user_number: str = ""        # f"{phone}@s.whatsapp.net"


@dataclass
class Product:
    name: str = ""
    id: str = ""
    value_cents: int = 0

    @property
    def value_brl(self) -> str:
        return f"{self.value_cents / 100:.2f}".replace(".", ",")


@dataclass
class Payment:
    pix_code: str = ""
    pix_expiration: str = ""
    boleto_url: str = ""
    boleto_barcode: str = ""
    boleto_expiry: str = ""
    access_url: str = ""
    rejection_reason: str = ""
    method: str = ""             # pix | boleto | credit_card | debit_card | ...


@dataclass
class NormalizedEvent:
    """Evento canônico que todos os adapters produzem."""
    platform: str                # "kiwify" | "hotmart" | "shopify" | ...
    event_kind: EventKind
    raw_event_type: str          # nome nativo do evento na plataforma
    customer: Customer
    product: Product
    payment: Payment = field(default_factory=Payment)
    raw_payload: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class PlatformAdapter(Protocol):
    """Interface obrigatória pra qualquer adapter de plataforma."""

    name: str  # identificador minúsculo: "kiwify", "hotmart", "shopify"

    def validate_signature(
        self,
        raw_body: bytes,
        headers: Mapping[str, str],
        query_params: Mapping[str, str],
        secret: str,
    ) -> bool:
        """Retorna True se signature do request bate com o secret configurado.
        Se secret for vazio, retorna True (modo dev)."""
        ...

    def event_kind(self, payload: dict[str, Any]) -> EventKind:
        """Mapeia evento nativo da plataforma → EventKind interno."""
        ...

    def normalize(self, payload: dict[str, Any]) -> NormalizedEvent:
        """Constrói NormalizedEvent a partir do payload bruto."""
        ...


# ---------- Helpers comuns ----------

def normalize_phone_br(raw: str) -> str:
    """Limpa, garante DDI 55, normaliza pra padrão wpp BR."""
    phone = "".join(c for c in (raw or "") if c.isdigit())
    if phone.startswith("0"):
        phone = phone[1:]
    if phone and not phone.startswith("55"):
        phone = "55" + phone
    return phone


def first_name_of(full: str) -> str:
    return (full or "").strip().split(" ")[0]
