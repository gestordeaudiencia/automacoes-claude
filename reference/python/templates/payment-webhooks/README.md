# Template: payment-webhooks

FastAPI **multi-plataforma** que recebe webhooks de Kiwify, Hotmart, Shopify (e qualquer plataforma adicionada via adapter) e dispara recovery automático (WhatsApp + email).

## URL única

```
POST /webhook/{platform}
```

`{platform}` é o slug do adapter (`kiwify`, `hotmart`, `shopify`, ou um custom seu).

## Plataformas built-in

| Plataforma | Slug | Validação | Eventos suportados |
|------------|------|-----------|-------------------|
| Kiwify | `kiwify` | HMAC-SHA1 query `?signature=` | pix_created, billet_created, order_approved, order_refused, abandoned_cart, ... |
| Hotmart | `hotmart` | Header `X-Hotmart-Hottok` (token estático) | PURCHASE_APPROVED, PURCHASE_BILLET_PRINTED, PURCHASE_REFUSED, ... |
| Shopify | `shopify` | Header `X-Shopify-Hmac-Sha256` (HMAC-SHA256 base64) | orders/paid, orders/cancelled, checkouts/create, ... |
| Lastlink | `lastlink` | Header `X-Lastlink-Signature` (HMAC-SHA256 hex) | Purchase_Order_Confirmed, Purchase_Request_Confirmed (PIX/boleto), Purchase_Refused, Subscription_Renewed, ... |

## Adicionar plataforma nova

Ver `docs/adicionar-plataforma.md`. Resumo:

1. Crie `packages/core/platforms/sua_plataforma.py` implementando `PlatformAdapter`
2. Registre em `packages/core/platforms/registry.py`
3. Adicione `SUAPLATAFORMA_WEBHOOK_SECRET` no `.env`
4. Configure URL `/webhook/sua_plataforma` no painel da plataforma

Pra plataformas simples, use `GenericAdapter` config-driven (sem código novo).

## Setup

```bash
psql $DATABASE_URL -f ../../shared/schema.sql
cp ../../.env.example ../../.env
cd ../.. && uv sync
cd templates/payment-webhooks
uvicorn app:app --reload --port 8000
ngrok http 8000
```

## Vars por plataforma

| Var | Plataforma | Origem |
|-----|------------|--------|
| `KIWIFY_WEBHOOK_SECRET` | Kiwify | Token HMAC do painel |
| `HOTMART_WEBHOOK_SECRET` | Hotmart | Hottok (token estático) |
| `SHOPIFY_WEBHOOK_SECRET` | Shopify | API Secret Key |
| `LASTLINK_WEBHOOK_SECRET` | Lastlink | Webhook secret do painel |

Padrão: `{PLATFORM}_WEBHOOK_SECRET` em maiúsculas.

## Customização

| O quê | Onde |
|-------|------|
| Tempos de espera | `contexts.py` (`build_contexto` + `EMAIL_WAIT_MINUTES`) |
| Tom dos prompts | `contexts.py` (`system_prompt`, `user_prompt`) |
| Resolução produto → link | `contexts.py` (`_produto_resolve`) |
| Templates de email | `email_templates.py` |
| Driver WhatsApp | `.env` (`WHATSAPP_DRIVER`) |
