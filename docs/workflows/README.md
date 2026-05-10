# Workflows GHL

Workflows pra montar na UI GHL **uma vez**. Triggam pelas tags que o Worker
adiciona automático em cada evento.

## Princípio: não duplicar Lastlink

Lastlink já manda nativamente:
- ✅ Email de acesso pós-compra (onboarding inicial)
- ✅ Email com PIX code / boleto link gerado
- ✅ Email de boleto vencido (genérico)
- ✅ Notificação de renovação

**Workflows aqui cobrem só os GAPS** — onde Lastlink não envia ou onde a
voz pessoal do Daniel diferencia.

## 3 workflows que importam (ROI hoje)

| # | Workflow | Trigger | Por que |
|---|---|---|---|
| 1 | **Carrinho abandonado** | tag `ev:carrinho` | Lastlink não envia. Dinheiro do chão |
| 2 | **PIX/Boleto expirado** | tag `pix_expirado` ou `boleto_expirado` | Lastlink só notifica. GHL gera novo link com cupom |
| 3 | **Pedido cancelado / cartão recusado** | tag `pedido_cancelado` ou `pagamento_recusado` | Cliente quente que falhou no checkout, especialmente em upsell |

Os 6 workflows antigos (boas-vindas, pix gerado, boleto gerado, etc) foram
removidos — duplicavam Lastlink.

## Tags emitidas pelo Worker

Pra cada evento normalizado, Worker emite:

```
platform:lastlink                  ← sempre
ev:<kind>                          ← pix | boleto | compra_aprovada | recusada | carrinho | cancelada | renovacao | outro
produto:<slug>                     ← slug do nome do produto
pgto:<method>                      ← pix | bankslip | credit_card
```

Tags **específicas** (só quando aplicável):

```
pix_expirado                       ← Purchase_Request_Expired + method pix
boleto_expirado                    ← Purchase_Request_Expired + method bankslip
pedido_cancelado                   ← Purchase_Request_Canceled
refund_solicitado                  ← Payment_Refund / Reversal / Chargeback
pagamento_recusado                 ← Purchase_Refused / Payment_Failed
source:test                        ← payload IsTest=true
utm:<source>                       ← se vier UTM source
```

**Use as tags específicas como triggers** — não as `ev:*` que podem ser ambíguas.

## Custom Values disponíveis

Já criados via MCP. Use nos templates de email:

| `{{ custom_values.* }}` | Valor |
|---|---|
| `agent_name` | Daniel |
| `agent_email` | contato@cloudcoding.com.br |
| `company_name` | Cloud Coding Brasil |
| `checkout_principal` | https://lastlink.com/p/CB7B75824 |
| `checkout_oferta_2` | (placeholder — preencher quando tiver) |
| `cupom_recovery_codigo` | VOLTA10 (temporário) |
| `cupom_recovery_desconto` | 10% (temporário) |
| `cupom_recovery_validade` | 7 dias |
| `cupom_recovery_link` | https://lastlink.com/p/CB7B75824?coupon=VOLTA10 |
| `support_whatsapp` | (placeholder) |

**Importante:** cupom é temporário. Daniel vai validar valor/código real
e atualizar via UI GHL → Settings → Custom Values.

## Custom Fields preenchidos pelo Worker

Use nos templates de email com `{{ contact.<key> }}`:

```
contact.first_name              ← do payload Buyer.Name
contact.email
contact.phone
contact.address1, .city, .state, .postalCode, .country  ← nativos GHL
contact.documento               ← CPF/CNPJ
contact.plataforma_origem       ← "lastlink"
contact.evento_recente          ← kind interno
contact.raw_event_type          ← evento original ("Purchase_Request_Expired")
contact.produto_nome
contact.produto_id
contact.valor_brl               ← "12,50"
contact.pix_code                ← string copia-cola
contact.pix_qr_url
contact.pix_expiration
contact.boleto_url              ← Invoice URL como fallback
contact.boleto_barcode          ← linha digitável
contact.boleto_expiry
contact.invoice_url
contact.access_url
contact.payment_method
contact.rejection_reason
contact.utm_source / utm_medium / utm_campaign / utm_term / utm_content
contact.affiliate_id, contact.affiliate_email
contact.subscription_id, contact.subscription_recurrency
```

## Workflows individuais

- [01-carrinho-abandonado.md](01-carrinho-abandonado.md)
- [02-pix-boleto-expirado.md](02-pix-boleto-expirado.md)
- [03-pedido-cancelado-recusado.md](03-pedido-cancelado-recusado.md)
