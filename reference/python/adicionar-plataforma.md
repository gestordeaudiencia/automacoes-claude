# Adicionar uma plataforma nova

Existem **dois caminhos**, dependendo de quão complexa é a plataforma.

---

## Caminho 1 — `GenericAdapter` config-driven (sem código)

Use quando a plataforma:
- Tem schema "plano" (campos no nível raiz ou aninhamento simples acessível com `a.b.c`)
- Usa um dos schemes de assinatura padrão: HMAC-SHA1/256 em header ou query, token estático em header, ou nenhuma assinatura
- Mapeia eventos via 1 campo string

### Exemplo: Eduzz

Eduzz envia POST com `trans_status` indicando o estado da venda. Status `3` = aprovada, `12` = boleto, etc.

Crie um arquivo de inicialização (ex: `templates/payment-webhooks/_setup_eduzz.py`) ou adicione no início do `app.py`:

```python
from core.platforms.registry import register_generic_from_config

register_generic_from_config({
    "name": "eduzz",
    "signature": {
        "scheme": "hmac_sha256_header",
        "header": "x-eduzz-signature",
        "encoding": "hex",
    },
    "event_field": "trans_status",
    "event_map": {
        "1":  "carrinho",
        "3":  "compra_aprovada",
        "8":  "recusada",
        "12": "boleto",
    },
    "fields": {
        "customer.name":  "cus_name",
        "customer.email": "cus_email",
        "customer.phone": "cus_tel",
        "product.name":   "product_name",
        "product.id":     "product_cod",
        "product.value_cents_x100": "trans_value",  # vem em reais → multiplica por 100
        "payment.method":         "trans_payment_method",
        "payment.boleto_url":     "trans_billet_link",
        "payment.boleto_expiry":  "trans_billet_due_date",
    },
})
```

Adicione no `.env`:
```
EDUZZ_WEBHOOK_SECRET=seu_secret_eduzz
```

Cadastre na Eduzz: `https://seu-dominio/webhook/eduzz`. Pronto.

### Schemes de assinatura suportados

| `scheme` | Como valida |
|----------|-------------|
| `none` | Aceita qualquer request (modo dev) |
| `static_token_header` | Compara `headers[<header>]` com o secret |
| `hmac_sha1_<source>` ou `hmac_sha256_<source>` | HMAC do raw body, source = `header` ou `query`, encoding = `hex` ou `base64` |

Exemplo HMAC-SHA256 base64 em query:
```python
"signature": {
    "scheme": "hmac_sha256_query",
    "query_param": "sig",
    "encoding": "base64",
}
```

### Field mapping — paths suportados

`fields` aceita paths estilo dot-notation: `a.b.c`, `data.purchase.payment.type`, `items.0.title`. Índices numéricos viram lookup em listas.

Para o campo de valor:
- `product.value_cents` — campo já vem em centavos (sem conversão)
- `product.value_cents_x100` — campo vem em reais, multiplica por 100

---

## Caminho 2 — Adapter Python custom (~50 linhas)

Use quando:
- Schema é aninhado/complexo (ex: Hotmart com nested data/purchase/payment)
- Validação de assinatura é não-padrão (ex: dois passos, headers múltiplos)
- Mapeamento de eventos depende de mais de um campo (ex: Hotmart distingue PIX/BILLET via `event` + `payment.type`)

### Exemplo: Lastlink

```python
# packages/core/platforms/lastlink.py
import hashlib
import hmac
from typing import Any, Mapping

from .base import (
    Customer, EventKind, NormalizedEvent, Payment, Product,
    first_name_of, normalize_phone_br,
)


class LastlinkAdapter:
    name = "lastlink"

    def validate_signature(
        self, raw_body: bytes, headers: Mapping[str, str],
        query_params: Mapping[str, str], secret: str,
    ) -> bool:
        if not secret:
            return True
        sig = headers.get("x-lastlink-signature", "")
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)

    def event_kind(self, payload: dict[str, Any]) -> EventKind:
        evt = (payload.get("Event") or "").lower()
        if evt == "purchase_paid":
            return "compra_aprovada"
        if evt == "purchase_pending_payment":
            method = (payload.get("Data", {}).get("Payment", {}).get("Method") or "").lower()
            return "pix" if "pix" in method else "boleto"
        if evt == "purchase_canceled":
            return "cancelada"
        return "outro"

    def normalize(self, payload: dict[str, Any]) -> NormalizedEvent:
        data = payload.get("Data") or {}
        buyer = data.get("Buyer") or {}
        product = data.get("Product") or {}
        payment = data.get("Payment") or {}

        full = buyer.get("Name") or ""
        phone = normalize_phone_br(buyer.get("Phone") or "")
        try:
            value_cents = int(round(float(payment.get("Amount") or 0) * 100))
        except (TypeError, ValueError):
            value_cents = 0

        return NormalizedEvent(
            platform=self.name,
            event_kind=self.event_kind(payload),
            raw_event_type=payload.get("Event", ""),
            customer=Customer(
                name=full,
                first_name=first_name_of(full),
                email=buyer.get("Email", ""),
                phone=phone,
                user_number=f"{phone}@s.whatsapp.net" if phone else "",
            ),
            product=Product(
                name=product.get("Name", ""),
                id=str(product.get("Id") or ""),
                value_cents=value_cents,
            ),
            payment=Payment(
                pix_code=payment.get("PixCode", ""),
                pix_expiration=payment.get("PixExpiration", ""),
                boleto_url=payment.get("BilletUrl", ""),
                boleto_barcode=payment.get("BilletCode", ""),
                boleto_expiry=payment.get("BilletDueDate", ""),
                method=(payment.get("Method") or "").lower(),
            ),
            raw_payload=payload,
        )
```

Registre em `packages/core/platforms/registry.py`:

```python
from .lastlink import LastlinkAdapter

_ADAPTERS = {
    "kiwify":  KiwifyAdapter(),
    "hotmart": HotmartAdapter(),
    "shopify": ShopifyAdapter(),
    "lastlink": LastlinkAdapter(),  # NOVO
}
```

Adicione no `.env`:
```
LASTLINK_WEBHOOK_SECRET=...
```

URL pra cadastrar: `https://seu-dominio/webhook/lastlink`.

---

## Testes pra adapter novo

Adicione caso ao `tests/test_smoke_adapters.py`:

```python
def test_lastlink_signature_e_normalize():
    adapter = get_adapter("lastlink")
    payload = { ... }  # exemplo real da plataforma
    raw = json.dumps(payload).encode()
    sig = hmac.new(b"sec", raw, hashlib.sha256).hexdigest()

    assert adapter.validate_signature(raw, {"x-lastlink-signature": sig}, {}, "sec")

    ev = adapter.normalize(payload)
    assert ev.platform == "lastlink"
    assert ev.event_kind == "compra_aprovada"
    assert ev.customer.first_name == "..."
    print("OK: Lastlink")
```

Rode `uv run python tests/test_smoke_adapters.py` e veja o ✓.

---

## Checklist final

- [ ] Adapter implementado (caminho 1 ou 2)
- [ ] Registrado no `registry.py` ou via `register_generic_from_config`
- [ ] `{PLATFORM}_WEBHOOK_SECRET` no `.env`
- [ ] Teste smoke verde
- [ ] URL `/webhook/{slug}` cadastrada no painel da plataforma
- [ ] Webhook de teste enviado e recebido com `200 OK`
