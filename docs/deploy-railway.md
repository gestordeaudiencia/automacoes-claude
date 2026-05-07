# Deploy no Railway

Os dois templates rodam no Railway com setup mínimo. Cada um vira um **service** separado no mesmo projeto.

## Pré-requisitos

- Conta Railway com cartão (Hobby plan = $5/mês, sobra)
- Repo no GitHub (push do `automacoes-claude`)

## Passo a passo

### 1. Cria projeto + Postgres

```
New Project → Empty Project
→ + New → Database → PostgreSQL
```

Anote `DATABASE_URL` (Variables tab do serviço Postgres).

### 2. Aplica schema

No Railway, abra o serviço Postgres → **Connect** → copie comando `psql`. Localmente:

```bash
psql 'postgresql://...' -f shared/schema.sql
```

### 3. Service do template `cron-recovery-vencidos`

```
+ New → GitHub Repo → escolha automacoes-claude
Settings → Root Directory: templates/cron-recovery-vencidos
Settings → Build Command: cd ../.. && uv sync
Settings → Start Command: cd ../.. && uv run python templates/cron-recovery-vencidos/app.py --schedule
```

**Variables** (Settings → Variables):

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
OPENAI_API_KEY=sk-...
WHATSAPP_DRIVER=avisaapi
WHATSAPP_API_URL=https://www.avisaapi.com.br/api/actions/sendMessage
WHATSAPP_API_TOKEN=...
AGENT_NAME=Laura
AGENT_OWNER=Matheus
COMPANY_NAME=Coeso Capital
PRODUCT_A_NAME=Investidor Coeso
PRODUCT_A_LINK=https://pay.kiwify.com.br/...
PRODUCT_B_NAME=Mentoria O Caminho
PRODUCT_B_LINK=https://pay.kiwify.com.br/...
```

Deploy. Logs devem mostrar `Scheduler iniciado. Cron a cada 1h.`

### 4. Service do template `kiwify-webhooks`

```
+ New → GitHub Repo → mesmo repo (segundo serviço)
Settings → Root Directory: templates/kiwify-webhooks
Settings → Build Command: cd ../.. && uv sync
Settings → Start Command: cd ../.. && uv run uvicorn templates.kiwify-webhooks.app:app --host 0.0.0.0 --port $PORT
Settings → Generate Domain (Networking)
```

Variables: mesmas do cron + `KIWIFY_WEBHOOK_SECRET` + `RESEND_API_KEY` (se for usar email).

Pegue o domínio gerado (ex: `automacoes-kiwify.up.railway.app`) e cadastre na Kiwify:

```
URL: https://automacoes-kiwify.up.railway.app/webhook/kiwify?signature={signature}
Eventos: pix_created, billet_created, order_approved, order_refused, abandoned_cart
```

### 5. Validar

```bash
curl https://automacoes-kiwify.up.railway.app/health
# {"ok":true}
```

Mande um pix de teste pelo checkout Kiwify e veja os logs do service no Railway.

## Custo estimado

- Postgres Hobby: ~$5/mês
- Cron service (idle 99% do tempo): ~$1/mês
- Webhook service (sob demanda): ~$3-5/mês

Total: **~$10/mês** vs n8n self-hosted (~$15-30/mês de instância + manutenção).
