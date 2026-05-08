# Setup GHL — passo-a-passo

Configurar a Location do GHL pra receber eventos do Worker e disparar workflows.

## 1. Coletar credenciais

Você precisa de **dois valores**:

### `GHL_LOCATION_ID`

GHL → menu lateral → ⚙️ Settings → **Business Profile** → topo da página, Location Id (ex: `abc123XYZ...`).

### `GHL_API_KEY` (Private Integration token)

Recomendado usar **Private Integration** (não a API key legacy):

1. GHL → ⚙️ Settings → **Private Integrations**
2. Clique **+ Create New Integration**
3. Nome: `automacoes-claude-worker`
4. Scopes mínimos:
   - `contacts.write` (upsert contato)
   - `contacts.readonly`
   - `workflows.readonly` (se for triggar workflow via API)
5. Copia o token gerado — começa com `pit-...`. **Salva agora**, GHL não mostra de novo.

## 2. Criar custom fields na Location

O Worker grava dados do evento em custom fields. Crie na UI antes:

GHL → ⚙️ Settings → **Custom Fields** → tab **Contact** → **+ Add Field** pra cada um abaixo:

| Field name | Field key (auto) | Type |
|------------|------------------|------|
| Plataforma origem | `plataforma_origem` | Single line |
| Evento recente | `evento_recente` | Single line |
| Produto nome | `produto_nome` | Single line |
| Produto ID | `produto_id` | Single line |
| Valor BRL | `valor_brl` | Single line |
| PIX code | `pix_code` | Multi-line text |
| PIX expiration | `pix_expiration` | Single line |
| Boleto URL | `boleto_url` | Single line |
| Boleto barcode | `boleto_barcode` | Multi-line text |
| Boleto expiry | `boleto_expiry` | Single line |
| Access URL | `access_url` | Single line |
| Rejection reason | `rejection_reason` | Single line |

**Importante:** o `Field key` precisa bater **exatamente** com o que o Worker manda (case-insensitive). GHL gera automaticamente baseado no nome — confirma os keys.

## 3. Tags que o Worker adiciona

Pra cada evento, o Worker adiciona automaticamente:

- `platform:kiwify` (ou `hotmart`/`shopify`/`lastlink`)
- `ev:pix` (ou `boleto`/`compra_aprovada`/`recusada`/`carrinho`/`cancelada`)
- `produto:<slug-do-nome>` (ex: `produto:investidor-coeso`)
- `pgto:credit_card` (se método disponível)

**Esses tags trigam os workflows.** Você não precisa criar tags manualmente — o Worker cria sob demanda.

## 4. Deploy do Worker

```bash
cd worker
npm install
wrangler login                                    # autentica no Cloudflare
wrangler secret put KIWIFY_WEBHOOK_SECRET         # cola token Kiwify
wrangler secret put HOTMART_WEBHOOK_SECRET        # cola Hottok
wrangler secret put SHOPIFY_WEBHOOK_SECRET        # cola API secret Shopify
wrangler secret put LASTLINK_WEBHOOK_SECRET       # cola signing secret Lastlink
wrangler secret put GHL_API_KEY                   # cola pit-... do passo 1
```

Edita `worker/wrangler.toml`:

```toml
[vars]
GHL_LOCATION_ID = "abc123..."   # do passo 1
```

Deploy:

```bash
npm run deploy
```

Cloudflare retorna URL: `https://automacoes-claude.SEU_USUARIO.workers.dev`.

Test:

```bash
curl https://automacoes-claude.SEU_USUARIO.workers.dev/health
# {"ok":true,"platforms":["hotmart","kiwify","lastlink","shopify"]}
```

## 5. Cadastrar URL nas plataformas

Pra cada plataforma que você usa, cadastre a URL `/webhook/{platform}`:

| Plataforma | URL |
|------------|-----|
| Kiwify | `https://automacoes-claude.SEU.workers.dev/webhook/kiwify` |
| Hotmart | `https://automacoes-claude.SEU.workers.dev/webhook/hotmart` |
| Shopify | `https://automacoes-claude.SEU.workers.dev/webhook/shopify` |
| Lastlink | `https://automacoes-claude.SEU.workers.dev/webhook/lastlink` |

Em cada painel:
- **Kiwify**: Configurações → Webhooks → cole URL + escolha eventos (pix_created, billet_created, order_approved, order_refused, abandoned_cart) + copie token HMAC pra `KIWIFY_WEBHOOK_SECRET`
- **Hotmart**: App de Postback → cole URL + escolha eventos PURCHASE_* + copie Hottok pra `HOTMART_WEBHOOK_SECRET`
- **Shopify**: Settings → Notifications → Webhooks → cole URL pra cada evento (orders/paid, orders/cancelled, checkouts/create) + copie API secret pra `SHOPIFY_WEBHOOK_SECRET`
- **Lastlink**: Configurações → Integrações → Webhooks → cole URL + copie signing secret pra `LASTLINK_WEBHOOK_SECRET`

## 6. Montar workflows GHL

Pronto pra montar os workflows. Cada cenário tem doc própria em `docs/workflows/`:

- [pix-gerado.md](workflows/pix-gerado.md) — confirma PIX + manda código + lembra perto do vencimento
- [boleto-gerado.md](workflows/boleto-gerado.md) — confirma boleto + link/barcode
- [compra-recusada.md](workflows/compra-recusada.md) — empático + tenta outro método
- [carrinho-abandonado.md](workflows/carrinho-abandonado.md) — consultivo, sem pressão
- [onboarding.md](workflows/onboarding.md) — boas-vindas + acesso
- [recovery-vencidos.md](workflows/recovery-vencidos.md) — pix/boleto que venceu sem pagamento

Cada uma tem o **trigger** (qual tag dispara), os **steps** (quais ações), e o **template de email**.
