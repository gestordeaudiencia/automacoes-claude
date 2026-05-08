# Workflow GHL — Recovery de pix/boleto vencido

**Objetivo:** alcançar quem gerou pagamento mas não pagou no prazo. Última chance antes do lead sumir.

## Trigger

Tag `pix_expirado` ou `boleto_expirado` adicionada.

Essas tags são adicionadas pelos workflows `pix-gerado` e `boleto-gerado` no final do fluxo (quando o prazo acabou e o cliente não comprou).

## Steps

1. **No wait** — quando essa tag aparece, já passou o tempo
2. **If/Else** → has tag `ev:compra_aprovada` (criada DEPOIS do pix gerar)?
   - Yes → End (comprou em outro produto/checkout)
   - No → continua
3. **Send Email**
   - **Subject:** `Seu pagamento expirou — quer um novo?`
   - **Body:**
     ```html
     <p>Oi {{contact.first_name}},</p>
     <p>Notei que o pagamento do <strong>{{contact.produto_nome}}</strong> expirou.</p>
     <p>Sem pressão — só quero saber se ainda faz sentido pra você. Se sim, posso gerar um novo:</p>
     <p><a href="{{custom_value.checkout_link}}" style="display:inline-block;background:#10b981;color:white;padding:12px 20px;border-radius:6px;text-decoration:none;">Gerar novo pagamento</a></p>
     <p>Se mudou de ideia ou já resolveu de outro jeito, ignora este email.</p>
     ```

4. **Wait 3 days**
5. **If/Else** has tag `ev:compra_aprovada`?
   - Yes → End
   - No → continua
6. **Send Email** (último toque)
   - **Subject:** `Última pergunta sobre {{contact.produto_nome}}`
   - Body curto: pergunta direta. Oferece desconto ou condição especial se a operação permite.

7. **Add Tag** `recovery_concluido` → marcar contato como ciclo encerrado

## Diferença vs Python cron-recovery-vencidos

A versão Python tinha um cron horário que **varria o banco** procurando pix vencidos. Aqui no GHL, a tag `pix_expirado` é adicionada **na conclusão do próprio workflow `pix-gerado`** (final do fluxo). Funciona se o workflow `pix-gerado` rodar até o fim — se o contato sair do workflow ou o admin pausar, perde.

**Trade-off:** GHL é por-contato. Python era por-query SQL. Pra volume baixo (até alguns milhares de eventos/mês) GHL aguenta. Acima disso, considerar voltar a varredura SQL.

## Tom

Recovery de pagamento expirado tem 2 cenários típicos:

1. **Cliente esqueceu** (50% dos casos) → email gentil é suficiente
2. **Cliente desistiu** (50% dos casos) → não adianta insistir

Email único + 1 follow-up + parar. Mais que isso queima.
