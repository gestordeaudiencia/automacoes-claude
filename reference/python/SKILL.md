---
name: customize-automacao
description: Customiza um template de automação (cron-recovery-vencidos ou kiwify-webhooks) pra um cliente novo. Pergunta nome do agente, produtos, links de checkout, credenciais. Gera .env e ajusta prompts. Use quando alguém clonar este repo e quiser plug-and-play sem editar arquivo manualmente.
---

# Skill: customize-automacao

Esta skill leva o cliente do "acabei de clonar o repo" até "está tudo configurado pra deploy".

## Quando rodar

Cliente clonou `automacoes-claude`, abriu Claude Code dentro do diretório, e quer:
- Configurar `.env` sem editar à mão
- Customizar prompts da agente comercial pro contexto dele
- Validar credenciais (Postgres, OpenAI/Anthropic, WhatsApp provider)

## Fluxo

### 1. Identifica qual template

Pergunte ao cliente qual template está customizando:
- `cron-recovery-vencidos` (cron horário)
- `kiwify-webhooks` (webhook server)
- `ambos` (configuração compartilhada)

Se ambos: configurar `.env` na raiz cobre os dois.

### 2. Coleta dados básicos

Use AskUserQuestion (ou pergunte sequencialmente) para:

**Identidade do agente comercial:**
- Nome do agente (ex: "Laura", "João")
- Nome do dono/responsável (ex: "Matheus", "Carlos")
- Nome da empresa (ex: "Coeso Capital")

**Produtos (até 2 no template; pra mais, instrua a editar `app.py`):**
- Produto A: nome + link de checkout
- Produto B (opcional): nome + link de checkout

**Suporte:**
- URL do WhatsApp de suporte (`https://wa.me/55...`)
- URL do clube/área de membros (se houver)

### 3. Coleta credenciais

**Postgres:**
- `DATABASE_URL` (ex: `postgresql://user:pass@host:5432/db`)
- Confirme que o cliente vai rodar `psql $DATABASE_URL -f shared/schema.sql` antes do deploy

**LLM (escolher um):**
- OpenAI: `OPENAI_API_KEY` + opcional `OPENAI_MODEL` (default `gpt-4.1-mini`)
- Anthropic: `ANTHROPIC_API_KEY` + opcional `ANTHROPIC_MODEL` (default `claude-haiku-4-5-20251001`)

**WhatsApp (escolher driver):**
- `avisaapi`: `WHATSAPP_API_URL` + `WHATSAPP_API_TOKEN` (Bearer)
- `evolution`: URL da instância + apikey
- `zapi`: URL + Client-Token

**Email (opcional, só pra `kiwify-webhooks`):**
- `none`: pula emails
- `resend`: `RESEND_API_KEY` + `EMAIL_FROM`

**Kiwify (só pra `kiwify-webhooks`):**
- `KIWIFY_WEBHOOK_SECRET` (HMAC-SHA1 token cadastrado no Kiwify)

### 4. Escreve `.env`

Baseie-se no `.env.example`. Use o tool Write pra criar `.env` na raiz do repo. Mantenha vars não preenchidas comentadas.

### 5. Customiza prompts (opcional)

Pergunte se o cliente quer ajustar tom/estilo dos prompts da agente:
- Se sim, mostre os prompts atuais (`templates/cron-recovery-vencidos/app.py:_system_prompt` e `templates/kiwify-webhooks/contexts.py:system_prompt`/`user_prompt`/`build_contexto`)
- Pergunte: tom mais formal? Mais informal? Outra língua? Persona diferente?
- Use Edit pra atualizar **só** o trecho de prompt relevante

### 6. Valida credenciais

Antes de declarar "pronto", rode (com permissão do cliente):

```bash
# Testa Postgres
psql $DATABASE_URL -c "SELECT 1;"

# Testa schema aplicado
psql $DATABASE_URL -c "SELECT to_regclass('public.eventos_kiwify');"
# deve retornar 'eventos_kiwify', não NULL
```

Se schema não aplicado, ofereça rodar:
```bash
psql $DATABASE_URL -f shared/schema.sql
```

### 7. Deploy hint

Pergunte onde vai deployar:
- **Railway**: aponte pra `docs/deploy-railway.md`
- **Fly.io**: `fly launch` no template específico
- **VPS**: `docs/deploy-vps.md`
- **Local/teste**: `python app.py` (cron) ou `uvicorn app:app` (webhook)

## Não faça

- NÃO comite `.env` (já está no `.gitignore`)
- NÃO escreva tokens/secrets em README ou comments
- NÃO altere lógica em `packages/core/` — só `templates/*/app.py` ou `.env`
- NÃO assuma defaults pra dados sensíveis — pergunte sempre

## Saída esperada

Ao final, o cliente deve ter:
1. `.env` na raiz, preenchido
2. Schema Postgres aplicado
3. Confirmação visual de qual template foi configurado
4. Comando exato pra subir o template em produção/dev
