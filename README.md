# automacoes-claude

> **Toolkit Python multi-plataforma pra automação de operações comerciais.** Substitui fluxos n8n por código auditável, versionado, sem lock-in. Recovery de pagamento, webhooks de checkout e follow-up automático em ~750 linhas de Python.

[![tests](https://img.shields.io/badge/tests-16%20passing-brightgreen)](.github/workflows/test.yml)
[![python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![template](https://img.shields.io/badge/use-template-orange)](https://github.com/SEU_USER/automacoes-claude/generate)

---

## Manifesto

n8n resolve bem o **primeiro** workflow. Quando a operação cresce, vira passivo:

- Lógica trancada em JSON gigante, impossível revisar em PR
- Custo escala com execução, não com valor entregue
- Manutenção exige instância 24/7 + re-config quando muda de servidor
- Versionamento de prompts e regras: inexistente
- Migração entre plataformas (Kiwify → Hotmart): refazer tudo

Este repo porta os fluxos mais comuns pra **Python + FastAPI + Postgres**, com **adapters plug-and-play** pra qualquer plataforma de pagamento. Roda em VPS, Railway, Fly, ou local.

---

## Plataformas suportadas

Built-in (adapters prontos + testes verde):

| Plataforma | Slug | Validação |
|------------|------|-----------|
| Kiwify | `kiwify` | HMAC-SHA1 query string |
| Hotmart | `hotmart` | Hottok (token estático) |
| Shopify | `shopify` | HMAC-SHA256 base64 header |
| Lastlink | `lastlink` | HMAC-SHA256 hex header |

Eduzz, Kirvano, Pepper, Cademí, Cademi Pay, etc: adicionar custa **~30 linhas** (config-driven via `GenericAdapter`) ou **~50 linhas** (adapter Python custom). Ver [docs/adicionar-plataforma.md](docs/adicionar-plataforma.md).

---

## O que vem pronto

### Template 1: `cron-recovery-vencidos`

Cron horário em Python que:
1. Busca `eventos_pagamento` com pix/boleto vencido
2. Filtra leads que **não compraram**, **não estão em atendimento humano** e **não foram processados**
3. Gera mensagem WhatsApp via LLM (OpenAI ou Anthropic)
4. Envia via WhatsApp (driver pluggable: AvisaAPI, Evolution, Z-API)
5. Registra `follow_up` pra idempotência

### Template 2: `payment-webhooks`

FastAPI server com endpoint único `POST /webhook/{platform}` que:
1. Valida assinatura específica da plataforma
2. Normaliza payload → `NormalizedEvent` schema unificado
3. Persiste em `eventos_pagamento`
4. Roteia por kind de evento (pix/boleto/compra_aprovada/recusada/carrinho/onboarding)
5. Dispara recovery em background (mensagem WhatsApp + email após X minutos)

---

## Quickstart (5 minutos)

```bash
git clone https://github.com/SEU_USER/automacoes-claude
cd automacoes-claude
cp .env.example .env       # preencha as chaves
uv sync
psql $DATABASE_URL -f shared/schema.sql

# Webhook server (em um terminal)
cd templates/payment-webhooks
uvicorn app:app --reload --port 8000

# Cron de recovery (em outro terminal)
cd templates/cron-recovery-vencidos
python app.py --schedule
```

URLs ativas:
- `POST http://localhost:8000/webhook/kiwify`
- `POST http://localhost:8000/webhook/hotmart`
- `POST http://localhost:8000/webhook/shopify`
- `POST http://localhost:8000/webhook/lastlink`

---

## Estrutura

```
packages/core/
  platforms/        ← adapters por plataforma + interface comum
    base.py         ← NormalizedEvent + PlatformAdapter Protocol
    kiwify.py / hotmart.py / shopify.py / lastlink.py
    generic.py      ← config-driven, sem código novo
    registry.py     ← get_adapter, register_adapter, list_platforms
  config.py         ← settings via .env (pydantic-settings)
  db.py             ← asyncpg helpers
  llm.py            ← OpenAI / Anthropic
  whatsapp.py       ← drivers AvisaAPI / Evolution / Z-API

templates/
  cron-recovery-vencidos/    ← cron horário, agnóstico de plataforma
  payment-webhooks/          ← endpoint /webhook/{platform}, multi-plataforma

shared/schema.sql            ← Postgres tables (eventos_pagamento + ...)
docs/                        ← deploy, migrar do n8n, adicionar plataforma
tests/                       ← 16 smoke tests verde
```

## Stack

- Python 3.11+
- FastAPI + Uvicorn (webhooks)
- APScheduler (cron in-process)
- asyncpg (Postgres async)
- OpenAI / Anthropic SDK (LLM)
- httpx (HTTP client)
- pydantic-settings (.env loader)
- loguru (logs)

---

## Docs

- [docs/migrar-do-n8n.md](docs/migrar-do-n8n.md) — passo-a-passo pra portar workflows do n8n
- [docs/adicionar-plataforma.md](docs/adicionar-plataforma.md) — como suportar Eduzz/Kirvano/qualquer plataforma nova
- [docs/deploy-railway.md](docs/deploy-railway.md) — deploy em Railway (~$10/mês)
- [docs/deploy-vps.md](docs/deploy-vps.md) — deploy em VPS Ubuntu

---

## Quem mantém

Toolkit construído por [Daniel Feitosa](https://instagram.com/gestordeaudiencia) ([@gestordeaudiencia](https://instagram.com/gestordeaudiencia)) e a comunidade [Cloud Coding Brasil](https://cloudcoding.com.br) — educação sobre Claude Code em PT-BR.

Encontrou bug? Quer adicionar plataforma nova? PRs e issues bem-vindas.

---

## Licença

MIT — usa, modifica, distribui, ganha dinheiro com isso. Sem warranty.
