# Workflow #2 — PIX / Boleto expirado

**Objetivo:** lead gerou PIX ou boleto, não pagou no prazo, deixou dinheiro na mesa. Lastlink notifica genérico — Daniel manda email pessoal com cupom + novo link.

**ROI esperado:** 5-15% recovery (último toque antes do lead esfriar pra sempre).

---

## Trigger

Duas tags possíveis (uniformiza no mesmo workflow):

- `pix_expirado` (quando `Purchase_Request_Expired` + method pix)
- `boleto_expirado` (idem com bankslip)

GHL UI: criar **2 workflows separados** OU **1 workflow com OR trigger**.

GHL não suporta OR no trigger — então **2 workflows** com mesmo conteúdo, só muda o trigger.

### Workflow A: trigger `pix_expirado`
### Workflow B: trigger `boleto_expirado`

(Texto do email referencia "pagamento" genérico, serve pros dois.)

## Steps

### 1. (Sem wait — evento já é "venceu")

Tag dispara imediato após Lastlink mandar `Purchase_Request_Expired`.

### 2. If/Else — já comprou?

- Condition: tag `ev:compra_aprovada` (se cliente fez nova compra entre o expirar e o webhook chegar)
- Yes → End
- No → continua

### 3. Send Email — recovery com cupom

- **From email:** `{{custom_values.agent_email}}`
- **From name:** `{{custom_values.agent_name}}`
- **Subject:** `seu pagamento do {{contact.produto_nome}} expirou`
- **Body:**

```
Oi {{contact.first_name}},

Notei aqui que seu pagamento do {{contact.produto_nome}}
expirou sem ter sido finalizado.

Sem pressão. Se ainda faz sentido pra ti, deixei um cupom
de {{custom_values.cupom_recovery_desconto}} de desconto pra facilitar:

{{custom_values.cupom_recovery_link}}

Cupom: {{custom_values.cupom_recovery_codigo}}
Válido por {{custom_values.cupom_recovery_validade}}.

Se mudou de ideia ou já resolveu por outro caminho, ignora
esse email. E se quiser conversar antes de decidir, é só
responder aqui.

Abraço,
{{custom_values.agent_name}}
```

### 4. Wait 3 days

- **+ Wait** → 3 days

### 5. If/Else — comprou nesse meio tempo?

- Condition: tag `ev:compra_aprovada`
- Yes → End
- No → continua

### 6. Send Email — último toque

- **Subject:** `última pergunta — {{contact.produto_nome}}`
- **Body:**

```
{{contact.first_name}}, última vez que te chamo aqui sobre isso.

Se ainda quiser entrar com o cupom de {{custom_values.cupom_recovery_desconto}},
o link tá aqui:

{{custom_values.cupom_recovery_link}}

Se não rolou, sem problema. Mas me responde uma coisa só:
o que segurou? Preço, dúvida, momento? Tu me ajuda a melhorar
respondendo isso.

Abraço,
{{custom_values.agent_name}}
```

### 7. Add Tag

- **Add Tag** → `recovery_concluido`

---

## Notas

- **Recovery email genérico Lastlink** já sai. Esse aqui é o **toque pessoal +
  cupom** que diferencia.
- Cupom temporário hoje: `VOLTA10` (10% off, 7 dias). Daniel substitui via
  Custom Values quando definir o real.
- Cliente recorrente (`subscription_id` preenchido) recebe **mesmo email** —
  não dá pra subdividir aqui sem ficar invasivo.

## Workflow visual

```
[Tag added: pix_expirado | boleto_expirado]
       ↓
[If has ev:compra_aprovada?] → Yes → End
       ↓ No
[Send Email recovery com cupom]
       ↓
[Wait 3 days]
       ↓
[If has ev:compra_aprovada?] → Yes → End
       ↓ No
[Send Email último toque]
       ↓
[Add Tag: recovery_concluido]
       ↓
End
```
