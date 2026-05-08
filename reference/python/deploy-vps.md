# Deploy em VPS (Ubuntu/Debian)

Pra clientes que já têm VPS ou querem controle total.

## Stack

- Python 3.11+ via `uv`
- systemd (managers de processo)
- nginx (reverse proxy pro webhook)
- Postgres 14+

## Setup inicial

```bash
# Como root
apt update && apt install -y python3.11 python3.11-venv postgresql nginx git
curl -LsSf https://astral.sh/uv/install.sh | sh

# Postgres
sudo -u postgres psql -c "CREATE DATABASE automacoes;"
sudo -u postgres psql -c "CREATE USER automacoes WITH PASSWORD 'TROCAR_SENHA';"
sudo -u postgres psql -c "GRANT ALL ON DATABASE automacoes TO automacoes;"

# Clona e instala
cd /opt
git clone <seu-repo> automacoes-claude
cd automacoes-claude
uv sync
psql 'postgresql://automacoes:TROCAR_SENHA@localhost/automacoes' -f shared/schema.sql
cp .env.example .env
nano .env   # preencha
```

## systemd: cron-recovery-vencidos

`/etc/systemd/system/automacoes-cron.service`:

```ini
[Unit]
Description=Automacoes Cron Recovery Vencidos
After=network.target postgresql.service

[Service]
Type=simple
User=automacoes
WorkingDirectory=/opt/automacoes-claude
EnvironmentFile=/opt/automacoes-claude/.env
ExecStart=/root/.local/bin/uv run python templates/cron-recovery-vencidos/app.py --schedule
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable --now automacoes-cron
journalctl -u automacoes-cron -f
```

## systemd: kiwify-webhooks

`/etc/systemd/system/automacoes-webhook.service`:

```ini
[Unit]
Description=Automacoes Kiwify Webhooks
After=network.target postgresql.service

[Service]
Type=simple
User=automacoes
WorkingDirectory=/opt/automacoes-claude
EnvironmentFile=/opt/automacoes-claude/.env
ExecStart=/root/.local/bin/uv run uvicorn templates.kiwify-webhooks.app:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## nginx

`/etc/nginx/sites-available/automacoes`:

```nginx
server {
    listen 80;
    server_name webhook.seudominio.com.br;

    location /webhook/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 1m;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/automacoes /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d webhook.seudominio.com.br
```

URL final: `https://webhook.seudominio.com.br/webhook/kiwify?signature={signature}`
