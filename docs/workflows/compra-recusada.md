# Workflow GHL — Compra recusada

**Objetivo:** abordar empático, sugerir tentar outro método, sem expor detalhes técnicos.

## Trigger

Tag `ev:recusada` adicionada.

## Steps

1. **Wait 1 minute**
2. **Send Email**
   - **Subject:** `Tivemos um problema com seu pagamento`
   - **Body:**
     ```html
     <p>Oi {{contact.first_name}},</p>
     <p>Tivemos um problema ao processar seu pagamento do <strong>{{contact.produto_nome}}</strong>.</p>
     <p>Pode ser bandeira do cartão, limite ou um detalhe pequeno.
     Tenta de novo com PIX, boleto ou outro cartão:</p>
     <p><a href="{{custom_value.checkout_link}}" style="display:inline-block;background:#10b981;color:white;padding:12px 20px;border-radius:6px;text-decoration:none;">Tentar novamente</a></p>
     <p>Se precisar de ajuda, é só responder este email.</p>
     ```
   - **Importante:** o link de checkout precisa ser uma `Custom Value` (não custom field) com a URL do produto. GHL → Settings → Custom Values → cria `checkout_link_default` ou um por produto se quiser.

3. **Wait 12 hours**
4. **If/Else** → has tag `ev:compra_aprovada`?
   - Yes → End
   - No → continua
5. **Send Email** (segundo toque, mais leve):
   - **Subject:** `Posso te ajudar com algo?`
   - Body curto: oferece suporte, link, sem pressão

## Variação por produto

Se tu tem mais de um produto, crie 1 workflow por produto OR usa um único workflow com **If/Else** baseado em tag `produto:xxx`:

```
trigger: ev:recusada
  ↓
If has tag "produto:investidor-coeso":
  send_email(template_investidor)
Else if has tag "produto:mentoria-o-caminho":
  send_email(template_mentoria)
Else:
  send_email(template_default)
```
