# worker/

Cloudflare Worker em TypeScript. Recebe webhooks, valida HMAC, dispatcha pra GHL.

## Estrutura

```
src/
  index.ts                ← entry point. Roteia POST /webhook/{platform}
  types.ts                ← NormalizedEvent + helpers (phone, names)
  crypto.ts               ← HMAC-SHA1/256 via WebCrypto
  ghl.ts                  ← cliente GHL (upsertContact + addTags)
  adapters/
    kiwify.ts             ← HMAC-SHA1 query, 7 eventos
    hotmart.ts            ← Hottok header, PURCHASE_*
    shopify.ts            ← HMAC-SHA256 base64 header, topics
    lastlink.ts           ← HMAC-SHA256 hex header, Purchase_*
    index.ts              ← getAdapter / listPlatforms

  __tests__/
    adapters.test.ts      ← 19 vitest tests

fixtures/                  ← payloads exemplo (real-ish) por plataforma
scripts/test-webhook.sh    ← dispara fixture local com HMAC válido
```

## Comandos

```bash
npm install
npm run dev            # roda local em http://localhost:8787
npm test               # vitest (19 tests)
npm run typecheck      # tsc --noEmit
npm run deploy         # wrangler deploy → produção

# Testar local com fixture (Worker precisa estar rodando via npm run dev)
npm run test:webhook -- kiwify   fixtures/kiwify-pix-created.json
npm run test:webhook -- hotmart  fixtures/hotmart-purchase-approved.json
npm run test:webhook -- shopify  fixtures/shopify-orders-paid.json
npm run test:webhook -- lastlink fixtures/lastlink-purchase-confirmed-pix.json
```

## Configurar produção

```bash
wrangler login
wrangler secret put KIWIFY_WEBHOOK_SECRET
wrangler secret put HOTMART_WEBHOOK_SECRET
wrangler secret put SHOPIFY_WEBHOOK_SECRET
wrangler secret put LASTLINK_WEBHOOK_SECRET
wrangler secret put GHL_API_KEY

# Editar wrangler.toml:
# [vars]
# GHL_LOCATION_ID = "..."

npm run deploy
```

Ver setup completo em `../docs/ghl-setup.md`.
