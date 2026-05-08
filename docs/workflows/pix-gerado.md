# Workflow GHL — PIX gerado

**Objetivo:** confirmar que o PIX foi gerado, mandar código pra facilitar o pagamento, lembrar antes de vencer.

## Trigger

Tag `ev:pix` adicionada ao contato.

## Steps

1. **Wait 2 minutes** — dá um respiro pro lead voltar do checkout
2. **Send Email** — usa custom fields do evento

   - **Subject:** `Seu PIX do {{contact.produto_nome}} está pronto`
   - **Body (HTML):**
     ```html
     <p>Oi {{contact.first_name}},</p>
     <p>Seu PIX de R$ {{contact.valor_brl}} para o <strong>{{contact.produto_nome}}</strong> foi gerado.
     Ele expira em 24 horas ({{contact.pix_expiration}}).</p>
     <p>Código PIX (copia e cola):</p>
     <pre style="background:#f3f3f3;padding:12px;border-radius:6px;word-break:break-all;">{{contact.pix_code}}</pre>
     <p>Qualquer dúvida, é só responder esse email.</p>
     ```

3. **Wait 18 hours**
4. **Send Email** (lembrete) — apenas se ainda não comprou:
   - **Condition (If/Else):** "Has tag `ev:compra_aprovada`?" → se SIM, exit workflow
   - Se NÃO:
     - **Subject:** `Falta pouco — seu PIX do {{contact.produto_nome}} vence hoje`
     - **Body:**
       ```html
       <p>Oi {{contact.first_name}},</p>
       <p>Seu PIX vence em algumas horas. Se ainda quer garantir o {{contact.produto_nome}}, segue o código:</p>
       <pre style="background:#f3f3f3;padding:12px;border-radius:6px;word-break:break-all;">{{contact.pix_code}}</pre>
       <p>Se já pagou ou não tem mais interesse, ignora este email.</p>
       ```

5. **Wait 5 hours**
6. **Remove tag `ev:pix`** + adiciona tag `pix_expirado` (faz dispara workflow recovery-vencidos)

## Como montar na UI

GHL → **Automation** → **Workflows** → **+ Create Workflow** → start from scratch:

1. **Trigger:** Contact Tag → "When Tag Added" → tag = `ev:pix`
2. **+ Add Action** → **Wait** → 2 minutes
3. **+ Add Action** → **Send Email** → cole subject + body acima
4. **+ Add Action** → **Wait** → 18 hours
5. **+ Add Action** → **If/Else** → condition: "Contact has tag `ev:compra_aprovada`"
   - Yes branch: **+ End Workflow**
   - No branch: continua
6. **+ Add Action** → **Send Email** (lembrete)
7. **+ Add Action** → **Wait** → 5 hours
8. **+ Add Action** → **Remove Tag** `ev:pix`
9. **+ Add Action** → **Add Tag** `pix_expirado`

**Save & Activate.**

## WhatsApp (futuro)

Quando WA Business via GHL ativo, troque os "Send Email" por "Send WhatsApp" usando os mesmos custom fields. Estrutura do workflow não muda.
