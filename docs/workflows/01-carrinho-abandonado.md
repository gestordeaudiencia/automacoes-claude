# Workflow #1 — Carrinho Abandonado

**Objetivo:** abrir conversa com lead que entrou no checkout, deu dados, mas não finalizou. Lastlink não envia nada nesse caso.

**ROI esperado:** 5-15% de conversão (varia conforme origem do tráfego).

---

## Trigger

Tag adicionada: **`ev:carrinho`**

GHL UI: **Automation → Workflows → + Create Workflow → Start from scratch**

- **Trigger:** Contact Tag → "When Tag Added" → tag = `ev:carrinho`

## Steps

### 1. Wait 30 minutes

Não dispara imediato. Dá tempo do lead voltar sozinho. Mensagem em < 30min queima.

- **+ Add Action** → **Wait** → 30 minutes

### 2. If/Else — já comprou enquanto isso?

- **+ Add Action** → **If/Else**
- Condition: "Contact has tag `ev:compra_aprovada`"
- **Yes** → **+ End Workflow**
- **No** → continua

### 3. If/Else — é cliente recorrente?

Cliente já com tag `ev:compra_aprovada` adicionada **antes** do `ev:carrinho` (de alguma compra anterior) = cliente quente.

- **+ Add Action** → **If/Else**
- Condition: ainda checa `ev:compra_aprovada` (se chegou aqui = não tem) → essa branca cobre só novos leads
- Em vez disso, use o **custom field `subscription_id`**: se preenchido = já é cliente recorrente
- Condition: "Contact custom field `subscription_id` is not empty"
- **Yes** → vai pra Step 4-B (versão cliente recorrente)
- **No** → vai pra Step 4-A (versão novo lead)

### 4-A. Send Email — versão NOVO LEAD

- **From email:** `{{ custom_values.agent_email }}`
- **From name:** `{{ custom_values.agent_name }}` (Cloud Coding Brasil)
- **Subject:** `ficou alguma dúvida sobre o {{ contact.produto_nome }}?`
- **Body (HTML, modo Plain):**

```
Oi {{contact.first_name}},

Vi aqui que tu começou o cadastro do {{contact.produto_nome}}
mas não chegou a finalizar.

Sem pressão nenhuma — quero entender se ficou alguma dúvida ou
se foi só uma olhada por curiosidade. Os dois são válidos.

Se quiser bater um papo, é só responder aqui mesmo. Ou se quiser
voltar pro checkout, segue o link:

{{custom_values.checkout_principal}}

Abraço,
{{custom_values.agent_name}}
```

### 4-B. Send Email — versão CLIENTE RECORRENTE

Mesma config de From, **subject + body diferentes**:

- **Subject:** `{{contact.first_name}}, vi que tu tentou de novo`
- **Body:**

```
Oi {{contact.first_name}}, é o {{custom_values.agent_name}}.

Tu já é da casa, então te falo na cara: vi que tu entrou no
checkout do {{contact.produto_nome}} mas não fechou. Tudo bem,
acontece.

Se foi grana, conta pra mim que vejo se rola condição.
Se foi dúvida, manda a pergunta que respondo aqui mesmo.
Se foi distração, segue o link com {{custom_values.cupom_recovery_desconto}} de desconto:

{{custom_values.cupom_recovery_link}}

Cupom {{custom_values.cupom_recovery_codigo}}, válido por
{{custom_values.cupom_recovery_validade}}.

Tu me ajuda muito respondendo, mesmo que seja "não rolou".

Abraço,
{{custom_values.agent_name}}
```

### 5. Wait 1 day

- **+ Add Action** → **Wait** → 1 day

### 6. If/Else — comprou agora?

- Condition: tag `ev:compra_aprovada`
- Yes → End
- No → continua

### 7. Send Email — última pergunta (curto)

- **Subject:** `última pergunta sobre o {{contact.produto_nome}}`
- **Body:**

```
Oi {{contact.first_name}},

Última coisa rapidinho: ainda faz sentido pra ti ou era
só curiosidade? Pode responder qualquer coisa, eu leio.

Se quiser dar uma segunda olhada com {{custom_values.cupom_recovery_desconto}} de desconto:

{{custom_values.cupom_recovery_link}}

Cupom {{custom_values.cupom_recovery_codigo}}.

Abraço,
{{custom_values.agent_name}}
```

### 8. Add Tag

- **+ Add Action** → **Add Tag** → `carrinho_recovery_concluido`

Marca contato como "passou pelo workflow", evita reenfileiramento se evento `ev:carrinho` for re-disparado.

---

## Tom — diretrizes

❌ Não menciona preço cheio
❌ Não cria urgência falsa ("últimas vagas", "só hoje")
❌ Não usa "garanta sua vaga" / "aproveite essa oportunidade"
✅ Pergunta direta. Oferece ajuda. Espera resposta.
✅ Texto curto. Sem header/logo corporativo.
✅ Assina como pessoa, não como empresa.

## Workflow visual final

```
[Tag added: ev:carrinho]
       ↓
[Wait 30 min]
       ↓
[If has ev:compra_aprovada?] → Yes → End
       ↓ No
[If subscription_id not empty?]
   ├─ Yes (recorrente) → [Send Email B]
   └─ No (novo lead)   → [Send Email A]
       ↓
[Wait 1 day]
       ↓
[If has ev:compra_aprovada?] → Yes → End
       ↓ No
[Send Email última pergunta]
       ↓
[Add Tag: carrinho_recovery_concluido]
       ↓
End
```
