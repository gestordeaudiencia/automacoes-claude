# SETUP — passo-a-passo do que VOCÊ precisa fazer

> Tudo que dependia de código já está pronto. Resta a parte que precisa do TEU acesso (Cloudflare, GHL, plataformas de pagamento).

**Tempo estimado total:** 45-60 minutos.

Marca os checkboxes conforme termina:

---

## ☐ Etapa 1 — Deploy do Worker no Cloudflare (5 min)

```bash
cd ~/Projects/cloud-coding-brasil/automacoes-claude/worker
npm install
npx wrangler login                    # abre navegador, autoriza
npx wrangler deploy
```

**Resultado esperado:**
```
Published automacoes-claude (...)
  https://automacoes-claude.SEU_USER.workers.dev
```

**Anote a URL.** Vai usar nas etapas 4-5.

**Verificar funcionou:**
```bash
curl https://automacoes-claude.SEU_USER.workers.dev/health
# {"ok":true,"platforms":["hotmart","kiwify","lastlink","shopify"]}
```

---

## ☐ Etapa 2 — Pegar credenciais GHL (5 min)

### 2a. Location ID
1. GHL → ⚙️ **Settings** → **Business Profile**
2. Copia `Location Id` no topo (ex: `abc123XYZ...`)

### 2b. Private Integration token
1. GHL → ⚙️ **Settings** → **Private Integrations**
2. **+ Create New Integration**
3. Nome: `automacoes-claude-worker`
4. Scopes (mínimos):
   - `contacts.write`
   - `contacts.readonly`
5. Copia o token (`pit-...`). **Salva agora**, GHL não mostra de novo.

---

## ☐ Etapa 3 — Configurar custom fields GHL (10 min)

GHL → ⚙️ **Settings** → **Custom Fields** → tab **Contact** → **+ Add Field** para cada um:

| Field name (label) | Type |
|---|---|
| Plataforma origem | Single line |
| Evento recente | Single line |
| Produto nome | Single line |
| Produto ID | Single line |
| Valor BRL | Single line |
| PIX code | Multi-line text |
| PIX expiration | Single line |
| Boleto URL | Single line |
| Boleto barcode | Multi-line text |
| Boleto expiry | Single line |
| Access URL | Single line |
| Rejection reason | Single line |

**Importante:** GHL gera `field key` automático baseado no nome. Confirma que ficou em snake_case (ex: `plataforma_origem`, `pix_code`). O Worker manda exatamente esses keys.

---

## ☐ Etapa 4 — Configurar secrets do Worker (3 min)

```bash
cd ~/Projects/cloud-coding-brasil/automacoes-claude/worker

# Cola o pit-... do passo 2b
npx wrangler secret put GHL_API_KEY

# Vai pedir cada secret. Pra plataformas que ainda não usa, ignora:
npx wrangler secret put KIWIFY_WEBHOOK_SECRET
npx wrangler secret put HOTMART_WEBHOOK_SECRET
npx wrangler secret put SHOPIFY_WEBHOOK_SECRET
npx wrangler secret put LASTLINK_WEBHOOK_SECRET
```

Depois edita `worker/wrangler.toml`:
```toml
[vars]
GHL_LOCATION_ID = "abc123..."   # ← cola aqui o Location Id do passo 2a
```

Re-deploy:
```bash
npx wrangler deploy
```

---

## ☐ Etapa 5 — Cadastrar URL nas plataformas (5-10 min cada)

Pra cada plataforma que tu usa, cadastra a URL `/webhook/{platform}`:

### Kiwify
1. Painel Kiwify → **Configurações** → **Webhooks**
2. URL: `https://automacoes-claude.SEU.workers.dev/webhook/kiwify`
3. Eventos: marca todos relevantes (`pix_created`, `billet_created`, `order_approved`, `order_refused`, `abandoned_cart`)
4. Copia o **token HMAC** que Kiwify gera → cola em `KIWIFY_WEBHOOK_SECRET` (volta no passo 4)
5. **Save**

### Hotmart
1. Painel Hotmart → **Ferramentas** → **Webhooks**
2. URL: `https://automacoes-claude.SEU.workers.dev/webhook/hotmart`
3. Eventos: `PURCHASE_APPROVED`, `PURCHASE_BILLET_PRINTED`, `PURCHASE_REFUSED`, `PURCHASE_OUT_OF_SHOPPING_CART`, `PURCHASE_CANCELED`
4. Copia o **Hottok** → cola em `HOTMART_WEBHOOK_SECRET`

### Lastlink
1. Painel Lastlink → **Configurações** → **Integrações** → **Webhooks**
2. URL: `https://automacoes-claude.SEU.workers.dev/webhook/lastlink`
3. Eventos: `Purchase_Order_Confirmed`, `Purchase_Request_Confirmed`, `Purchase_Refused`, `Purchase_Request_Expired`
4. Copia o **signing secret** → cola em `LASTLINK_WEBHOOK_SECRET`

### Shopify
1. Shopify Admin → **Settings** → **Notifications** → **Webhooks**
2. Adiciona webhook pra cada evento (URL repete, muda só o topic):
   - `orders/paid` → URL `/webhook/shopify`
   - `orders/cancelled` → URL `/webhook/shopify`
   - `checkouts/create` → URL `/webhook/shopify`
3. Format: **JSON**
4. Copia o **API Secret Key** da app → cola em `SHOPIFY_WEBHOOK_SECRET`

---

## ☐ Etapa 6 — Montar workflow piloto no GHL (15 min)

Sugestão: começar com **onboarding** (mais simples e mais valioso).

1. Abre `docs/workflows/onboarding.md` no repo
2. GHL → **Automation** → **Workflows** → **+ Create Workflow**
3. Segue o passo-a-passo da doc:
   - Trigger: tag `ev:compra_aprovada`
   - Action: Wait + Send Email com merge fields dos custom fields
4. **Save & Activate**

**Custom Values necessários** (Settings → Custom Values):
- `agent_name` = "Laura" (ou nome que assina)
- `company_name` = nome da tua empresa
- `checkout_link` = URL default de checkout

---

## ☐ Etapa 7 — Testar end-to-end (10 min)

### Teste manual com curl
```bash
# Pega webhook secret usado em prod
SECRET="seu_token_kiwify_real"

# Cria payload de teste
PAYLOAD='{"webhook_event_type":"order_approved","Customer":{"full_name":"Teste E2E","email":"seu_email@example.com","mobile":"11999999999"},"Product":{"product_name":"Curso Teste"},"Commissions":{"charge_amount":"197.00"}}'

# Assina HMAC-SHA1
SIG=$(printf '%s' "$PAYLOAD" | openssl dgst -sha1 -hmac "$SECRET" -hex | awk '{print $2}')

# Dispara
curl -X POST "https://automacoes-claude.SEU.workers.dev/webhook/kiwify?signature=$SIG" \
  -H "Content-Type: application/json" \
  --data-raw "$PAYLOAD"

# Resposta esperada: {"ok":true,"platform":"kiwify","eventKind":"compra_aprovada",...}
```

### Verificar resultado no GHL
1. Vai em GHL → **Contacts** → busca por `seu_email@example.com`
2. Deve aparecer:
   - Contato criado
   - Tags: `platform:kiwify`, `ev:compra_aprovada`, `produto:curso-teste`
   - Custom fields preenchidos
3. Vai em **Automation** → **Workflows** → onboarding → **Stats** → deve mostrar 1 enrollment
4. Aguarda 1 minuto → email de boas-vindas chega na inbox

### Teste real
Faz uma compra teste numa das tuas plataformas (cupom 100% off ou produto $1). Verifica que webhook chegou e workflow rodou.

---

## ☐ Etapa 8 — Monitorar e iterar

### Logs do Worker
```bash
cd worker
npx wrangler tail
```
Mostra cada request em tempo real. Útil pra debugar.

### Logs do GHL
GHL → **Automation** → **Workflows** → workflow específico → **Stats / History** mostra cada execução, sucesso/falha.

### O que olhar primeiro
- Webhooks chegando com `200`? (Worker logs)
- Contatos sendo criados? (GHL Contacts)
- Tags certas sendo aplicadas?
- Workflow disparando?
- Email saindo? (GHL Email logs)

---

## Suporte / próximos passos

Funcionou? 🎉 Próximas direções possíveis:

1. **Ativar WhatsApp Business no GHL** quando tiver conta empresarial — workflows passam a mandar WA também sem mexer código
2. **Adicionar OpenAI no Worker** pra gerar mensagens variadas em vez de templates fixos (fase 2)
3. **Adicionar plataformas extras** (Eduzz/Kirvano/Cademí) — exemplo em `reference/python/adicionar-plataforma.md`, mesma lógica vale pro Worker

Algo quebrou? Abre issue em https://github.com/gestordeaudiencia/automacoes-claude/issues
