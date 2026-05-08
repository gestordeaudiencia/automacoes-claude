#!/usr/bin/env bash
#
# Dispara webhook de teste contra Worker rodando local (wrangler dev).
# Usa fixtures/{platform}-*.json + assina conforme esquema da plataforma.
#
# Uso:
#   ./scripts/test-webhook.sh kiwify   fixtures/kiwify-pix-created.json
#   ./scripts/test-webhook.sh hotmart  fixtures/hotmart-purchase-approved.json
#   ./scripts/test-webhook.sh shopify  fixtures/shopify-orders-paid.json
#   ./scripts/test-webhook.sh lastlink fixtures/lastlink-purchase-confirmed-pix.json
#
# Pré-requisitos:
#   1. Worker rodando: `npm run dev` (wrangler dev) em outro terminal
#   2. Secrets locais setados via .dev.vars (criado automaticamente abaixo)
#
set -euo pipefail

PLATFORM="${1:-}"
FIXTURE="${2:-}"
WORKER_URL="${WORKER_URL:-http://localhost:8787}"

if [[ -z "$PLATFORM" || -z "$FIXTURE" ]]; then
  echo "Uso: $0 <platform> <fixture-file>"
  echo "Exemplo: $0 kiwify fixtures/kiwify-pix-created.json"
  exit 1
fi

if [[ ! -f "$FIXTURE" ]]; then
  echo "❌ Fixture não encontrada: $FIXTURE"
  exit 1
fi

# Garante .dev.vars com secrets fake pra dev local
if [[ ! -f .dev.vars ]]; then
  cat > .dev.vars <<'EOF'
KIWIFY_WEBHOOK_SECRET=test-kiwify-secret
HOTMART_WEBHOOK_SECRET=test-hotmart-token
SHOPIFY_WEBHOOK_SECRET=test-shopify-secret
LASTLINK_WEBHOOK_SECRET=test-lastlink-secret
GHL_API_KEY=test-pit-token
GHL_LOCATION_ID=test-location
EOF
  echo "📝 Criei .dev.vars com secrets fake. Reinicia 'npm run dev' antes de testar."
fi

BODY=$(cat "$FIXTURE")
URL="$WORKER_URL/webhook/$PLATFORM"

case "$PLATFORM" in
  kiwify)
    SIG=$(printf '%s' "$BODY" | openssl dgst -sha1 -hmac "test-kiwify-secret" -hex | awk '{print $2}')
    URL="$URL?signature=$SIG"
    HEADERS=(-H "Content-Type: application/json")
    ;;
  hotmart)
    HEADERS=(-H "Content-Type: application/json" -H "X-Hotmart-Hottok: test-hotmart-token")
    ;;
  shopify)
    SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "test-shopify-secret" -binary | base64)
    HEADERS=(-H "Content-Type: application/json" -H "X-Shopify-Hmac-Sha256: $SIG" -H "X-Shopify-Topic: orders/paid")
    ;;
  lastlink)
    SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "test-lastlink-secret" -hex | awk '{print $2}')
    HEADERS=(-H "Content-Type: application/json" -H "X-Lastlink-Signature: $SIG")
    ;;
  *)
    echo "❌ Plataforma desconhecida: $PLATFORM"
    exit 1
    ;;
esac

echo "→ POST $URL"
echo "→ Body: $FIXTURE ($(wc -c < "$FIXTURE") bytes)"
echo

curl -sS -X POST "$URL" "${HEADERS[@]}" --data-raw "$BODY" -w "\n\nStatus: %{http_code}\n"
