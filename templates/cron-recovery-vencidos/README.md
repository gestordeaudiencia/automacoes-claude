# Template: cron-recovery-vencidos

Cron horário que busca pix/boletos vencidos no Postgres e dispara mensagem de recovery via WhatsApp.

## O que faz

1. A cada 1h, busca em `eventos_kiwify` todos os pix/boletos vencidos onde:
   - Lead **não** comprou depois (sem `order_approved` posterior)
   - Lead **não** está em atendimento humano (`contatos_agente.agente != 'off'`)
   - Lead **não** teve conversa nas últimas 2h (não está no meio de SPIN)
   - **Não** foi processado ainda (sem `follow_up` do tipo `pix_vencido`/`boleto_vencido` posterior)
2. Para cada lead, monta contexto, gera mensagem com LLM e envia via WhatsApp
3. Registra em `follow_up` (idempotência)
4. Espera 5s entre leads

## Setup

```bash
# 1. Crie tabelas
psql $DATABASE_URL -f ../../shared/schema.sql

# 2. Configure .env (raiz do repo)
cp ../../.env.example ../../.env
# preencha DATABASE_URL, OPENAI_API_KEY, WHATSAPP_*, AGENT_*, PRODUCT_*

# 3. Instale deps
cd ../..
uv sync   # ou: pip install -e .

# 4. Rode uma vez (manual)
cd templates/cron-recovery-vencidos
python app.py

# 5. Rode em produção (cron interno)
python app.py --schedule
```

## Customização

**Prompts da Laura** estão em `app.py` nas funções `_system_prompt()` e `_user_prompt()`. Edite à mão ou rode a skill `/customize` (em breve).

**Query Postgres** em `QUERY_VENCIDOS`. Ajuste janelas (25h pix, 2h chat) se sua operação for diferente.

## Variáveis sensíveis (.env)

| Var | Pra que serve |
|-----|---------------|
| `DATABASE_URL` | Postgres com schema aplicado |
| `OPENAI_API_KEY` (ou `ANTHROPIC_API_KEY`) | LLM que escreve mensagem |
| `WHATSAPP_API_TOKEN` | Token do provider (AvisaAPI/Evolution/Z-API) |
| `AGENT_NAME` / `AGENT_OWNER` / `COMPANY_NAME` | Identidade do bot |
| `PRODUCT_A_LINK` / `PRODUCT_B_LINK` | Fallback se lead não tem `link_oferta` em `contatos_agente` |

## Deploy

- **Railway / Fly:** processo único `python app.py --schedule`
- **VPS:** systemd + service file (exemplo em `docs/deploy-vps.md`)
- **Lambda / Cloud Run:** trigger externo (EventBridge/Cloud Scheduler) chamando `python app.py`
