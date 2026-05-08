# Workflow GHL — Onboarding (compra aprovada)

**Objetivo:** boas-vindas calorosas, entrega de acesso, primeira instrução clara.

## Trigger

Tag `ev:compra_aprovada` adicionada.

## Steps

1. **Wait 1 minute**
2. **Send Email**
   - **Subject:** `Bem-vindo(a) ao {{contact.produto_nome}} 🎉`
   - **Body:**
     ```html
     <p>Oi {{contact.first_name}}, parabéns pela decisão!</p>
     <p>Seu acesso ao <strong>{{contact.produto_nome}}</strong> está pronto:</p>
     <p><a href="{{contact.access_url}}" style="display:inline-block;background:#10b981;color:white;padding:14px 24px;border-radius:6px;text-decoration:none;font-size:16px;">Acessar agora</a></p>
     <p>Se não conseguir entrar, responde esse email que te ajudo.</p>
     <p>— {{custom_value.agent_name}}</p>
     ```

3. **Wait 2 days** — dá tempo do lead acessar
4. **If/Else** → has tag `acesso_realizado`?
   - Esse tag tu adiciona via outro workflow ou trigger externo (login no club). Se não tem como detectar, pula esse step.
5. **Send Email** (check-in dia 2)
   - **Subject:** `Como tá indo?`
   - Body: pergunta se conseguiu acessar, se tem dúvida, oferece ajuda. SEM upsell.

6. **Wait 5 days**
7. **Send Email** (check-in dia 7)
   - **Subject:** `Pequena dica pra aproveitar melhor`
   - Body: 1 dica de uso, link pra recurso específico, convite pra responder com dúvida.

## Por que dois check-ins (dia 2, dia 7)

Métrica que mais importa em onboarding: **% de quem ativou o produto** (logou + consumiu primeiro conteúdo).

- Dia 2: tira inércia. Cliente que pagou e não acessou = lead frio.
- Dia 7: cria hábito. Quem usou na primeira semana fica.

Não usa esses pra vender. Usa pra ATIVAR.

## Variação produto

Se mentoria tem turma com data, adiciona step específico:
```
If has tag "produto:mentoria-o-caminho":
  Send Email "Sua turma começa em..."
```

## WhatsApp (futuro)

Onboarding é um dos lugares que **mais beneficia** de WhatsApp. Email tem 20% de open rate; WA tem 90%+. Quando ativar:
1. Send WhatsApp imediato com `access_url`
2. Send WhatsApp dia 2 (check-in)
3. Send WhatsApp dia 7 (dica)
