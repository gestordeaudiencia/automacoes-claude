# CONTEXTO — leia primeiro após /clear

> Arquivo de **handover entre sessões Claude**. Próxima sessão (após `/clear` do Daniel) lê isso primeiro pra retomar trabalho sem perder contexto.

---

## Quem é o user

**Daniel Feitosa** ([@gestordeaudiencia](https://instagram.com/gestordeaudiencia))
- Criador de conteúdo + estrategista de IA, baseado em João Pessoa
- Vende **Claude Code do zero ao avançado** (assinatura) via Lastlink
- Email business: `contato@cloudcoding.com.br`
- GitHub: `gestordeaudiencia`

## O que está sendo construído

**Repo:** https://github.com/gestordeaudiencia/automacoes-claude

**Stack:** Cloudflare Worker (TypeScript) → recebe webhooks de plataformas de pagamento → dispara workflows GoHighLevel via API.

**Arquitetura:**
```
[Lastlink/Kiwify/Hotmart/Shopify] webhook
       ↓
[Cloudflare Worker]  (https://automacoes-claude.gestordeaudiencia.workers.dev)
   - valida HMAC
   - normaliza payload
   - cria/atualiza contato GHL + adiciona tags
       ↓
[GoHighLevel]
   - Workflows triggados por tags
   - Email via contato@cloudcoding.com.br
   - WhatsApp Business (futuro, quando ativar)
```

## Estado atual — confirmado funcionando

✅ Worker no ar (`/health` retorna 200, 32 tests vitest verde, CI verde)
✅ Adapter Lastlink validado contra **7 payloads reais** (Subscription_Renewal_Pending, Purchase_Order_Confirmed, Abandoned_Cart, Payment_Refund, Purchase_Request_Canceled, Purchase_Request_Expired, Refund_Period_Over)
✅ Lastlink webhook prod cadastrado, secret gravado via `wrangler secret put`
✅ 6 eventos Lastlink ativos (Compra Completa, Fatura Criada, Pedido Expirada, Renovação Pendente, Assinatura Cancelada, Carrinho Abandonado)
✅ **26 custom fields** criados no GHL via MCP (todos batendo com keys do Worker)
✅ **10 custom values** criados no GHL via MCP (agent_*, checkout_*, cupom_*)
✅ **Pipeline E2E testado** — contato `Moises Pereira` (id `rLdvpikK15oZqaMQMUqV`) criado no GHL com tags + custom fields preenchidos via webhook real Lastlink
✅ Versão Python preservada em `reference/python/` (educacional)

## Credenciais já gravadas (Cloudflare Worker secrets)

Listadas via `wrangler secret list`:

```
GHL_API_KEY              ✅ gravado (pit-... do Private Integration)
GHL_LOCATION_ID          ✅ gravado
LASTLINK_WEBHOOK_SECRET  ✅ gravado
KIWIFY_WEBHOOK_SECRET    ❌ não setado
HOTMART_WEBHOOK_SECRET   ❌ não setado
SHOPIFY_WEBHOOK_SECRET   ❌ não setado
```

**Onde achar valores reais** (NÃO commitar aqui):
- Cloudflare API token + account ID: peça ao Daniel ou regenere em
  https://dash.cloudflare.com/profile/api-tokens
- GHL API key: GHL → Settings → Private Integrations → procurar
  `automacoes-claude-worker`
- GHL Location ID: salvo em `wrangler secret`. Ou GHL → Settings →
  Business Profile
- Lastlink secret: painel Lastlink → Webhook → token visível

Pra exportar env vars na sessão:
```bash
export CLOUDFLARE_API_TOKEN="<peça ao Daniel ou regenere>"
export CLOUDFLARE_ACCOUNT_ID="<peça ao Daniel>"
```

## Tags que o Worker emite

```
platform:lastlink
ev:<kind>                    pix | boleto | compra_aprovada | recusada | carrinho | cancelada | renovacao | outro
produto:<slug>
pgto:<method>                pix | bankslip | credit_card
source:test                  se IsTest=true
utm:<source>                 se vier
pix_expirado                 Purchase_Request_Expired (pix)
boleto_expirado              Purchase_Request_Expired (bankslip)
pedido_cancelado             Purchase_Request_Canceled
refund_solicitado            Payment_Refund/Reversal/Chargeback
pagamento_recusado           Purchase_Refused/Payment_Failed
```

## Custom Values GHL (já criados)

| Key | Valor atual | Notas |
|---|---|---|
| `agent_name` | Daniel | |
| `agent_email` | contato@cloudcoding.com.br | |
| `company_name` | Cloud Coding Brasil | |
| `checkout_principal` | https://lastlink.com/p/CB7B75824 | |
| `checkout_oferta_2` | PREENCHER_QUANDO_TIVER_SEGUNDA_OFERTA | placeholder |
| `cupom_recovery_codigo` | VOLTA10 | **temporário** |
| `cupom_recovery_desconto` | 10% | **temporário** |
| `cupom_recovery_validade` | 7 dias | **temporário** |
| `cupom_recovery_link` | https://lastlink.com/p/CB7B75824?coupon=VOLTA10 | **temporário** |
| `support_whatsapp` | PREENCHER_WA_SUPORTE | placeholder |

## Decisões tomadas

1. **Não duplicar Lastlink.** Lastlink já manda email de acesso pós-compra, PIX code, boleto link, boleto vencido genérico, renovação. Workflows GHL só pra **gaps**.

2. **Foco em 3 workflows hoje** (ROI imediato sem WhatsApp):
   - **Carrinho abandonado** (`ev:carrinho`) — Lastlink não cobre
   - **PIX/Boleto expirado** (`pix_expirado`/`boleto_expirado`) — Lastlink só notifica genérico, GHL adiciona cupom + voz pessoal
   - **Pedido cancelado / cartão recusado** (`pedido_cancelado`/`pagamento_recusado`) — golden case, especialmente em upsell. Cliente quente com problema técnico.

3. **Tom dos emails:**
   - **Voz Daniel**, oralizado, "teu/tua"
   - Frases longas com vírgulas
   - "te falo na cara", "tu já é da casa"
   - Sem header/logo corporativo
   - Subject minúsculo, texto curto
   - Diferenciação cliente novo vs cliente recorrente (via tag `subscription_id` preenchido)

4. **Cupom temporário:** `VOLTA10` 10% off / 7 dias. Daniel pesquisa o que mercado faz, depois substitui via UI GHL → Settings → Custom Values.

5. **WhatsApp = futuro.** Daniel ainda **não tem chip/número WA**. Decisão: esperar ativar WA Business via GHL oficial (não comprar chip). Quando ativar, troca "Send Email" por "Send WhatsApp" nos workflows.

## Próximos passos pendentes

### 🔴 Crítico — Daniel precisa fazer (UI GHL não automatizável)

1. **Montar 3 workflows na UI GHL** seguindo specs em `docs/workflows/`:
   - `01-carrinho-abandonado.md`
   - `02-pix-boleto-expirado.md`
   - `03-pedido-cancelado-recusado.md`

2. **Validar/substituir cupom** (`VOLTA10` é temporário):
   - Decidir desconto real e validade
   - Atualizar 4 custom values: `cupom_recovery_codigo`, `cupom_recovery_desconto`, `cupom_recovery_validade`, `cupom_recovery_link`
   - GHL → Settings → Custom Values

3. **Preencher placeholders:**
   - `support_whatsapp` (quando ativar)
   - `checkout_oferta_2` (se tiver outro produto)

4. **Testar workflows com webhook real Lastlink** (botão "Testar" na UI Lastlink dispara payload).

### 🟡 Quando Daniel ativar WhatsApp Business GHL

5. Trocar steps "Send Email" por "Send WhatsApp" nos 3 workflows. Mesmos merge fields funcionam.
6. Considerar adicionar workflows extras (onboarding dia 2/7, win-back churn).

### ⚪ Opcional / futuro

7. Se Daniel rodar tráfego pago, monitorar conversão de `ev:carrinho` (volume sobe muito).
8. Se vender outros produtos via Lastlink, criar custom values específicos por produto.
9. Adicionar **Kiwify/Hotmart/Shopify** se Daniel virar produto multi-plataforma (adapters já prontos, só faltam secrets + cadastrar URL nos painéis).

## Voz / preferências do Daniel (pra próxima sessão respeitar)

Do `~/.claude/CLAUDE.md` global:
- Comunicação **direta e desafiadora**, pode discordar com fundamento
- **Plain text ou markdown**, sem formatação visual pesada
- **Precisão > confiança aparente** — se não souber, diz "não sei"
- Católico tradicional (respeitar tom)
- **Voz em PT-BR:** frases mais longas, oralizado, "teu/tua" sempre, expressões "te fala na cara", "faz a conta fria", sem paralelismo forçado, sem adjetivos empilhados, sem metáforas inventadas
- Atualmente em **caveman mode** (drop articles/filler/pleasantries — fragmentos OK)

## Comandos úteis pra próxima sessão

```bash
# Repo path
cd ~/Projects/cloud-coding-brasil/automacoes-claude

# Health check Worker
curl https://automacoes-claude.gestordeaudiencia.workers.dev/health

# Re-deploy Worker (precisa env vars Cloudflare exportadas)
cd worker && export CLOUDFLARE_API_TOKEN="<token>" CLOUDFLARE_ACCOUNT_ID="<id>" && ./node_modules/.bin/wrangler deploy

# Logs em tempo real
./node_modules/.bin/wrangler tail --format=pretty

# Tests
npm test

# MCP GHL — Location ID
PtR6a0KmYTQDEFkRBiCM
```

## Arquivos importantes

- `worker/src/index.ts` — entry point
- `worker/src/adapters/lastlink.ts` — adapter Lastlink (validado contra payloads reais)
- `worker/src/ghl.ts` — cliente GHL + buildTagsFor
- `worker/src/types.ts` — NormalizedEvent schema
- `docs/workflows/` — specs dos 3 workflows pra Daniel montar na UI
- `docs/ghl-setup.md` — setup completo da Location GHL
- `SETUP.md` — checklist 8 passos (alguns já feitos)
- `reference/python/` — versão Python anterior (educacional)
