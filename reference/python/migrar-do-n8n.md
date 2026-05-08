# Migrar do n8n pra automacoes-claude

> Por que: n8n resolve bem o primeiro workflow. Quando a operação cresce, JSON gigante vira passivo. Migrar pra código Python paga em manutenção, custo e auditabilidade.

## Quando vale migrar

| Sinal | Migrar? |
|-------|---------|
| Tem 1-2 workflows simples e nunca vai mudar | **Não** — fica no n8n |
| Mais de 5 workflows, ou lógica complexa em Code nodes | **Sim** |
| Já edita Code nodes em todo workflow | **Sim** (já é Python/JS no fundo) |
| Precisa versionar prompts ou regras de negócio em Git | **Sim** |
| Cliente exige auditoria/compliance | **Sim** |
| Time tem alguém que escreve Python | **Sim** |

## Mapeamento conceitual

| n8n | automacoes-claude |
|-----|-------------------|
| Workflow | Diretório em `templates/` |
| Cron Trigger | `APScheduler` em `app.py` ou cron externo |
| Webhook Trigger | FastAPI endpoint `@app.post(...)` |
| Postgres node | `core/db.py` (asyncpg) |
| HTTP Request node | `httpx.AsyncClient` |
| Code node | Função Python normal |
| AI Agent node | `core/llm.py` (OpenAI/Anthropic SDK) |
| Switch node | `if/elif` ou `match` |
| If node | `if` |
| Set node | construção de dict |
| Wait node | `await asyncio.sleep(...)` |
| Merge node | dict merge |
| Loop (SplitInBatches) | `for ... in items` |
| Credentials | `.env` + `pydantic-settings` |
| Execution Data | `loguru` (logs estruturados) |

## Passo a passo (workflow → template Python)

### 1. Mapeie o workflow no papel

Abra o n8n. Liste os nodes em ordem. Identifique:
- **Gatilho:** webhook? cron? manual?
- **Entradas externas:** quais APIs ele chama?
- **Saídas externas:** WhatsApp? Gmail? webhook outro?
- **Estado persistente:** quais tabelas Postgres ele lê/escreve?
- **Lógica condicional:** quais Switch/If existem?

### 2. Identifique variáveis hardcoded

Use `grep` no JSON exportado:
```bash
grep -E '(http|Bearer|@|R\$ |[A-Z]{4,})' workflow.json
```
Tudo que estiver hardcoded vira `.env` var.

### 3. Crie um novo template

```bash
cp -r templates/cron-recovery-vencidos templates/seu-novo-template
cd templates/seu-novo-template
# adapte app.py
```

### 4. Reescreva node por node

Não tente fazer tudo de uma vez. Abra o `app.py` ao lado do n8n e:
1. Reescreva o gatilho (cron ou FastAPI)
2. Reescreva a query/normalização
3. Reescreva a lógica de roteamento
4. Reescreva chamadas externas (LLM, WhatsApp, email)
5. Reescreva persistência

### 5. Testa unitariamente

Crie `tests/test_seu_template.py` mockando deps externas. Veja exemplos em `tests/test_smoke_*.py`.

### 6. Valida em paralelo

Rode os dois ao mesmo tempo (n8n e Python) por 1-2 dias. Compara output. Quando os números baterem, desliga o n8n.

## Armadilhas comuns

- **Webhook signature**: n8n às vezes calcula HMAC sobre `JSON.stringify(body)` (re-stringificado). Replicar exatamente — usar mesmo encoding (`separators=(",", ":")` no Python).
- **Wait nodes longos**: em código, `asyncio.sleep` mantém a coroutine viva. Pra waits longos (>1h), prefira agendamento externo (cron, Celery beat, Sidekiq) ou fila persistente — se o servidor reinicia, a task morre.
- **Credenciais OAuth (Gmail, GHL)**: re-fazer fluxo OAuth quando migrar. Tokens de n8n não viajam.
- **Loops com Wait dentro**: o n8n permite. Em Python, é preferível `for + await asyncio.sleep`. Mas se o loop é longo, considere fila com workers.

## Quanto tempo leva?

- Workflow simples (1 trigger, ~10 nodes): **2-4 horas**
- Workflow médio (1 trigger, ~30 nodes, lógica condicional): **1 dia**
- Workflow complexo (multi-trigger, integrações OAuth): **2-3 dias**

Se você usar Claude Code com este pacote como base, divida esse tempo por 3.
