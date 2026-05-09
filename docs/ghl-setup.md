# Setup GHL — passo-a-passo

Configurar a Location do GHL pra receber eventos do Worker e disparar workflows.

## 1. Coletar credenciais

### `GHL_LOCATION_ID`

GHL → ⚙️ Settings → **Business Profile** → topo da página, Location Id.

### `GHL_API_KEY` (Private Integration token)

1. GHL → ⚙️ Settings → **Private Integrations**
2. Clique **+ Create New Integration**
3. Nome: `automacoes-claude-worker`
4. Scopes mínimos:
   - `contacts.write`
   - `contacts.readonly`
5. Copia o token gerado (`pit-...`). **Salva agora**, GHL não mostra de novo.

## 2. Custom Fields

Crie em GHL → ⚙️ Settings → **Custom Fields** → tab **Contact** → **+ Add Field**.

**Lista validada contra payloads reais Lastlink** (camadas: plataforma, produto, pagamento, cliente, tracking, assinatura).

### Plataforma + evento

| Field name (label) | Type | Field key esperado |
|---|---|---|
| Plataforma origem | Single Line | `plataforma_origem` |
| Evento recente | Single Line | `evento_recente` |
| Raw event type | Single Line | `raw_event_type` |

### Produto

| Field name | Type | Key |
|---|---|---|
| Produto nome | Single Line | `produto_nome` |
| Produto ID | Single Line | `produto_id` |
| Valor BRL | Single Line | `valor_brl` |

### Pagamento — PIX

| Field name | Type | Key |
|---|---|---|
| PIX code | Multi Line | `pix_code` |
| PIX QR URL | Single Line | `pix_qr_url` |
| PIX expiration | Single Line | `pix_expiration` |

### Pagamento — Boleto

| Field name | Type | Key |
|---|---|---|
| Boleto URL | Single Line | `boleto_url` |
| Boleto barcode (linha digitável) | Multi Line | `boleto_barcode` |
| Boleto expiry | Single Line | `boleto_expiry` |

### Pagamento — geral

| Field name | Type | Key |
|---|---|---|
| Invoice URL | Single Line | `invoice_url` |
| Access URL | Single Line | `access_url` |
| Payment method | Single Line | `payment_method` |
| Rejection reason | Single Line | `rejection_reason` |

### Cliente

| Field name | Type | Key |
|---|---|---|
| Documento | Single Line | `documento` |

(Endereço completo é gravado nos campos nativos do GHL — `address1`, `city`, `state`, `postalCode` — não precisa criar custom.)

### Tracking / atribuição (UTMs + afiliado)

| Field name | Type | Key |
|---|---|---|
| UTM source | Single Line | `utm_source` |
| UTM medium | Single Line | `utm_medium` |
| UTM campaign | Single Line | `utm_campaign` |
| UTM term | Single Line | `utm_term` |
| UTM content | Single Line | `utm_content` |
| Affiliate ID | Single Line | `affiliate_id` |
| Affiliate email | Single Line | `affiliate_email` |

### Assinatura (se vendes recorrente)

| Field name | Type | Key |
|---|---|---|
| Subscription ID | Single Line | `subscription_id` |
| Subscription recurrency | Single Line | `subscription_recurrency` |

**Total: 23 custom fields.** Cria todos pra cobrir todo payload.

**Importante:** o `Field key` é gerado automático pelo GHL baseado no nome. Confirma após criar que ficou em snake_case exatamente como a coluna "Key" acima. Se algum sair diferente (ex: `plataformaorigem` sem underscore), me avisa que ajusto Worker.

## 3. Deploy do Worker

Já feito! URL: `https://automacoes-claude.gestordeaudiencia.workers.dev`

## 4. Cadastrar URL nas plataformas

URL pra cada plataforma:

| Plataforma | URL |
|---|---|
| Kiwify | `https://automacoes-claude.gestordeaudiencia.workers.dev/webhook/kiwify` |
| Hotmart | `https://automacoes-claude.gestordeaudiencia.workers.dev/webhook/hotmart` |
| Shopify | `https://automacoes-claude.gestordeaudiencia.workers.dev/webhook/shopify` |
| Lastlink | `https://automacoes-claude.gestordeaudiencia.workers.dev/webhook/lastlink` |

### Lastlink — eventos recomendados

Marca estes (cobertos pelo adapter):

✅ **Compra Completa** (`Purchase_Order_Confirmed`) → onboarding
✅ **Fatura Criada** (`Purchase_Request_Confirmed`) → confirmação pix/boleto
✅ **Carrinho Abandonado** (`Abandoned_Cart`) → mensagem consultiva
✅ **Pedido de Compra Expirada** (`Purchase_Request_Expired`) → recovery pix/boleto vencido
✅ **Pedido de Compra Cancelado** (`Purchase_Request_Canceled`) → cancelamento
✅ **Pagamento Estornado** / **Reembolsado** (`Payment_Refund`) → cancelamento
✅ **Pagamento de Renovação Pendente** (`Subscription_Renewal_Pending`) → recovery renovação
✅ **Pagamento de Renovação Efetuado** (`Subscription_Renewal_Approved`) → renovação confirmada
✅ **Assinatura Cancelada** (`Subscription_Canceled`) → churn

Opcionais (caso queira workflows custom via tag `ev:outro` + `raw_event_type`):

- **Periodo de Reembolso Terminado** (`Refund_Period_Over`) — útil pra tag "venda firmada"
- **Liberação/remoção de acesso** — info-only

## 5. Tags geradas pelo Worker

Pra cada evento, Worker adiciona tags no contato GHL:

```
platform:lastlink              ← qual plataforma
ev:pix                         ← kind interno (pix|boleto|compra_aprovada|recusada|carrinho|cancelada|renovacao|outro)
produto:claude-code-do-zero-ao-avancado  ← slug do produto
pgto:pix                       ← método de pagamento
source:test                    ← se IsTest=true
utm:instagram                  ← UTM source (slugged)
```

**Use estas tags como triggers dos teus workflows GHL.**

## 6. Workflows GHL

Templates prontos em `docs/workflows/`:
- [pix-gerado.md](workflows/pix-gerado.md)
- [boleto-gerado.md](workflows/boleto-gerado.md)
- [compra-recusada.md](workflows/compra-recusada.md)
- [carrinho-abandonado.md](workflows/carrinho-abandonado.md)
- [onboarding.md](workflows/onboarding.md)
- [recovery-vencidos.md](workflows/recovery-vencidos.md)
