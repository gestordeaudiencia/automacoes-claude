# automacoes-claude

> **Cloudflare Worker** que recebe webhooks de plataformas de pagamento (Kiwify, Hotmart, Shopify, Lastlink) e dispara workflows no **GoHighLevel**. Validação HMAC nativa, deploy zero-ops, custo praticamente zero.

[![tests](https://img.shields.io/badge/tests-19%20passing-brightgreen)](.github/workflows/test.yml)
[![runtime](https://img.shields.io/badge/runtime-cloudflare%20workers-orange)](https://workers.cloudflare.com/)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Arquitetura

```
[Kiwify | Hotmart | Shopify | Lastlink]
        │ webhook
        ▼
[Cloudflare Worker] ←─ você só mantém isto (~400 linhas TS)
   • valida HMAC
   • normaliza payload
   • upsert contato no GHL + adiciona tags
        │ GHL API
        ▼
[GoHighLevel]
   • Workflows triggados por tags fazem o resto:
     - emails (templates)
     - waits (timing)
     - condicionais (já comprou? pagou?)
     - WhatsApp Business (quando ativar)
     - SMS, pipelines, ...
```

**O que tu monta na UI do GHL** (uma vez): 6 workflows usando templates do diretório `docs/workflows/`.
**O que tu deploya** (uma vez): 1 Cloudflare Worker via `wrangler deploy`.
**O que custa**: $0 no Cloudflare (free tier 100k req/dia), $0 extra no GHL (tu já paga).

## Por quê

- **n8n** = JSON gigante, lock-in, manutenção 24/7.
- **Tudo no GHL native** = inseguro (não valida HMAC) + difícil debugar.
- **Híbrido (este repo)** = valida segurança no Worker, lógica de negócio no GHL UI. Manutenção mínima.

## Plataformas suportadas

| Plataforma | Slug | Validação | Eventos |
|------------|------|-----------|---------|
| Kiwify | `kiwify` | HMAC-SHA1 query | pix, boleto, compra_aprovada, recusada, carrinho, ... |
| Hotmart | `hotmart` | Hottok header | PURCHASE_APPROVED/BILLET/REFUSED/... |
| Shopify | `shopify` | HMAC-SHA256 base64 | orders/paid, checkouts/create, ... |
| Lastlink | `lastlink` | HMAC-SHA256 hex | Purchase_Order_Confirmed, Purchase_Request_Confirmed, ... |

Adicionar plataforma nova = ~80 linhas de TypeScript (ver `worker/src/adapters/`).

## Quickstart

```bash
git clone https://github.com/gestordeaudiencia/automacoes-claude
cd automacoes-claude/worker
npm install

# 1. Configurar secrets (Cloudflare gerencia)
wrangler login
wrangler secret put GHL_API_KEY            # Private Integration token
wrangler secret put KIWIFY_WEBHOOK_SECRET  # token HMAC do painel Kiwify
# ... outras plataformas conforme uso

# 2. Editar wrangler.toml
# [vars]
# GHL_LOCATION_ID = "abc123..."

# 3. Deploy
npm run deploy
# → https://automacoes-claude.SEU.workers.dev
```

## Setup completo

Passo-a-passo: [docs/ghl-setup.md](docs/ghl-setup.md)

Workflows GHL pré-prontos (copia da doc, cola na UI):
- [PIX gerado](docs/workflows/pix-gerado.md)
- [Boleto gerado](docs/workflows/boleto-gerado.md)
- [Compra recusada](docs/workflows/compra-recusada.md)
- [Carrinho abandonado](docs/workflows/carrinho-abandonado.md)
- [Onboarding](docs/workflows/onboarding.md)
- [Recovery vencidos](docs/workflows/recovery-vencidos.md)

## Estrutura

```
worker/                          ← Cloudflare Worker (TypeScript)
  src/
    index.ts                     ← entry, roteia /webhook/{platform}
    adapters/                    ← 1 arquivo por plataforma
      kiwify.ts / hotmart.ts / shopify.ts / lastlink.ts
      index.ts                   ← registry
    crypto.ts                    ← HMAC helpers (WebCrypto)
    ghl.ts                       ← cliente GHL API
    types.ts                     ← NormalizedEvent, helpers
    __tests__/adapters.test.ts   ← 19 tests
  wrangler.toml
  package.json

docs/                            ← passo-a-passo GHL + workflows
  ghl-setup.md
  workflows/

reference/python/                ← versão Python anterior, mantida como educacional
```

## Migrar do n8n

[docs/migrar-do-n8n.md (na pasta reference)](reference/python/migrar-do-n8n.md)

## Quem mantém

[Daniel Feitosa](https://instagram.com/gestordeaudiencia) ([@gestordeaudiencia](https://instagram.com/gestordeaudiencia)) — [Cloud Coding Brasil](https://cloudcoding.com.br).

## Licença

MIT.
