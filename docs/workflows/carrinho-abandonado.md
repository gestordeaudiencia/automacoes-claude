# Workflow GHL — Carrinho abandonado

**Objetivo:** abrir conversa consultiva. NÃO recuperar a venda na bala. Pergunta se ficou dúvida, sem pressão.

## Trigger

Tag `ev:carrinho` adicionada.

## Steps

1. **Wait 30 minutes** — dá tempo do lead voltar sozinho. Mensagem imediata é cara e queima o lead.
2. **If/Else** → has tag `ev:compra_aprovada`?
   - Yes → End (já comprou nesse meio tempo)
   - No → continua
3. **Send Email**
   - **Subject:** `Posso te ajudar com algo?`
   - **Body:**
     ```html
     <p>Oi {{contact.first_name}},</p>
     <p>Vi que você começou o cadastro pro <strong>{{contact.produto_nome}}</strong> mas não finalizou.</p>
     <p>Sou {{custom_value.agent_name}}, do time da {{custom_value.company_name}}.
     Se ficou alguma dúvida, posso te ajudar.</p>
     <p>Se quiser dar uma olhada de novo: <a href="{{custom_value.checkout_link}}">retomar checkout</a></p>
     ```

4. **Wait 1 day**
5. **If/Else** has tag `ev:compra_aprovada`?
   - Yes → End
   - No → continua
6. **Send Email** (último toque)
   - **Subject:** `Última pergunta`
   - Body bem curto: "ainda faz sentido pra você ou era só curiosidade?". Foca em RESPOSTA, não em VENDA.

## Custom values necessários

GHL → Settings → Custom Values → criar:
- `agent_name` — nome de quem assina (ex: "Laura")
- `company_name` — nome da empresa
- `checkout_link` — URL default de checkout

Se quiser personalizar por produto, usa custom values específicos: `checkout_link_investidor`, `checkout_link_mentoria`, etc.

## Tom — cuidado

Carrinho abandonado é a etapa mais sensível. Tom errado QUEIMA o lead pra sempre. Regras:

- ❌ Não menciona preço
- ❌ Não inclui urgência ("últimas vagas", "só hoje")
- ❌ Não usa linguagem de vendas ("aproveita", "garanta")
- ✅ Conversa de gente. Pergunta. Oferece ajuda. Espera resposta.
