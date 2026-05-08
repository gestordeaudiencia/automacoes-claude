# Checklist de credenciais

Antes de rodar qualquer template, garanta:

## Obrigatório

- [ ] **Postgres** — `DATABASE_URL` apontando pra um banco com `shared/schema.sql` aplicado
- [ ] **LLM** — `OPENAI_API_KEY` **ou** `ANTHROPIC_API_KEY` (escolha em `LLM_PROVIDER`)
- [ ] **WhatsApp** — `WHATSAPP_DRIVER` + `WHATSAPP_API_URL` + `WHATSAPP_API_TOKEN`

## Por template

### `cron-recovery-vencidos`
- [ ] Acima
- [ ] Tabelas `eventos_kiwify`, `contatos_agente`, `follow_up`, `chat_histories` populadas (ou criadas pelo schema, esperando os webhooks)

### `kiwify-webhooks`
- [ ] Acima
- [ ] `KIWIFY_WEBHOOK_SECRET` (token HMAC-SHA1 cadastrado no painel Kiwify)
- [ ] (Opcional) Email: `EMAIL_PROVIDER=resend` + `RESEND_API_KEY` + `EMAIL_FROM`
- [ ] URL pública (ngrok pra dev, domínio HTTPS pra prod)

## WhatsApp providers — onde pegar

| Driver | Onde pegar |
|--------|------------|
| `avisaapi` | painel.avisaapi.com.br → API → token Bearer |
| `evolution` | sua instância Evolution → `/manager` → apikey |
| `zapi` | app.z-api.io → instância → token |

## Validação rápida

```bash
# Postgres
psql $DATABASE_URL -c "SELECT to_regclass('public.eventos_kiwify');"

# OpenAI
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY" | head

# WhatsApp (AvisaAPI)
curl -X POST $WHATSAPP_API_URL \
  -H "Authorization: Bearer $WHATSAPP_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"number":"5511999998888","message":"teste"}'
```
