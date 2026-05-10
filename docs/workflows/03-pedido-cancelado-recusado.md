# Workflow #3 — Pedido cancelado / Cartão recusado

**Objetivo:** o **golden case** — lead tentou comprar, deu erro técnico (cartão recusado, limite, bandeira), Lastlink só faz cancel genérico. Recovery aqui pega cliente **quente** querendo comprar mas com problema técnico.

**ROI esperado:** 20-40% conversão. Especialmente alto se for upsell (cliente já comprou outra coisa antes).

---

## Trigger

Duas tags cobrem o cenário:

- `pedido_cancelado` (Purchase_Request_Canceled)
- `pagamento_recusado` (Purchase_Refused / Payment_Failed)

Faz **2 workflows** com mesmo conteúdo OU **1 workflow** triggado pela tag `pedido_cancelado` (cobre maioria dos casos Lastlink, que coloca cartão recusado dentro de Canceled).

Sugestão: começa com `pedido_cancelado` (1 workflow). Adiciona `pagamento_recusado` se Lastlink mandar separadamente em algum cenário.

## Steps

### 1. Wait 1 minute

Pequeno respiro pra evitar email durante webhook race condition.

- **Wait** → 1 minute

### 2. If/Else — já comprou agora?

- Condition: tag `ev:compra_aprovada`
- Yes → End
- No → continua

### 3. If/Else — cliente recorrente?

Custom field `subscription_id` preenchido = já é cliente.

- **+ If/Else** → "Contact custom field `subscription_id` is not empty"
- **Yes** → versão B (cliente quente, upsell falhou)
- **No** → versão A (primeira compra falhou)

### 4-A. Send Email — versão NOVA TENTATIVA

- **Subject:** `tivemos um problema no seu pagamento`
- **Body:**

```
Oi {{contact.first_name}},

Tentou pagar o {{contact.produto_nome}} e deu um erro no caminho.

Geralmente é coisa pequena: bandeira do cartão que não aceita,
limite, antifraude do banco. Acontece bastante.

Se quiser tentar de novo, sugiro PIX ou outro cartão. Deixei
um cupom de {{custom_values.cupom_recovery_desconto}} pra compensar o transtorno:

{{custom_values.cupom_recovery_link}}

Cupom: {{custom_values.cupom_recovery_codigo}}
Validade: {{custom_values.cupom_recovery_validade}}

Se precisar de ajuda, é só responder aqui.

Abraço,
{{custom_values.agent_name}}
```

### 4-B. Send Email — versão CLIENTE RECORRENTE (upsell falhou)

- **Subject:** `{{contact.first_name}}, deu erro mas tô aqui`
- **Body:**

```
Oi {{contact.first_name}}, é o {{custom_values.agent_name}}.

Vi que tu já é cliente e tentou pegar o {{contact.produto_nome}}
mas o pagamento foi recusado.

Provavelmente cartão (limite, bandeira, antifraude). Acontece.

Como tu já é da casa, te falo direto:
1. Tenta com PIX que costuma passar
2. Ou outro cartão se tiver
3. Ou me responde aqui que vejo se consigo dar uma jeitinho

Cupom de {{custom_values.cupom_recovery_desconto}} válido por {{custom_values.cupom_recovery_validade}}:

{{custom_values.cupom_recovery_link}}
({{custom_values.cupom_recovery_codigo}})

Tu fala que rolou ou não rolou que ajudo.

Abraço,
{{custom_values.agent_name}}
```

### 5. Wait 1 day

- **Wait** → 1 day

### 6. If/Else — comprou?

- Condition: tag `ev:compra_aprovada`
- Yes → End
- No → continua

### 7. Send Email — segundo toque (curto)

- **Subject:** `posso te ajudar com isso?`
- **Body:**

```
{{contact.first_name}}, deu certo no fim?

Se ainda não, conta pra mim que tipo de erro apareceu —
talvez consiga te orientar. Se mudou de ideia, sem problema.

Cupom ainda tá válido por mais alguns dias se quiser:
{{custom_values.cupom_recovery_link}}

Abraço,
{{custom_values.agent_name}}
```

### 8. Add Tag

- **Add Tag** → `recusada_recovery_concluido`

---

## Por que esse é o de maior ROI

1. **Cliente declarou intenção de comprar** (chegou a colocar dados de cartão)
2. **Não foi falta de interesse** — foi problema técnico
3. **Cupom + jeitinho pessoal** resolve 30-50% dos casos
4. Em **upsell** (B branch), cliente já confia → conversão sobe ainda mais

Nenhuma plataforma de pagamento (Lastlink incluso) faz esse toque pessoal.
Email automático "pagamento recusado" parece com support, queima a vibe.

## Workflow visual

```
[Tag added: pedido_cancelado]
       ↓
[Wait 1 min]
       ↓
[If has ev:compra_aprovada?] → Yes → End
       ↓ No
[If subscription_id not empty?]
   ├─ Yes → [Send Email B — recorrente]
   └─ No  → [Send Email A — primeira tentativa]
       ↓
[Wait 1 day]
       ↓
[If has ev:compra_aprovada?] → Yes → End
       ↓ No
[Send Email segundo toque]
       ↓
[Add Tag: recusada_recovery_concluido]
       ↓
End
```
