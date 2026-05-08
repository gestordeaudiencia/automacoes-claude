/**
 * automacoes-claude — Cloudflare Worker
 *
 * Recebe POST /webhook/{platform} de Kiwify, Hotmart, Shopify, Lastlink.
 * - Valida assinatura HMAC (cada plataforma tem o seu esquema)
 * - Normaliza payload pra schema unificado
 * - Faz upsert no GHL + adiciona tags
 * - Workflows GHL (montados na UI) são triggados pelas tags e fazem o resto
 *
 * Deploy:
 *   cd worker && npm install && npm run deploy
 */

import { getAdapter, listPlatforms } from "./adapters";
import { dispatchEventToGhl, type GhlEnv } from "./ghl";

interface Env extends GhlEnv {
  KIWIFY_WEBHOOK_SECRET?: string;
  HOTMART_WEBHOOK_SECRET?: string;
  SHOPIFY_WEBHOOK_SECRET?: string;
  LASTLINK_WEBHOOK_SECRET?: string;
  LOG_LEVEL?: string;
}

function getSecret(env: Env, platform: string): string {
  const key = `${platform.toUpperCase()}_WEBHOOK_SECRET` as keyof Env;
  return (env[key] as string) || "";
}

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    // GET /health
    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ok: true, platforms: listPlatforms() });
    }

    // POST /webhook/{platform}
    const match = url.pathname.match(/^\/webhook\/([a-z0-9_-]+)$/i);
    if (request.method !== "POST" || !match) {
      return json({ error: "not_found" }, 404);
    }

    const platform = match[1].toLowerCase();
    const adapter = getAdapter(platform);
    if (!adapter) {
      return json({ error: "platform_unknown", platform }, 404);
    }

    const rawBody = await request.text();
    let payload: any;
    try {
      payload = rawBody ? JSON.parse(rawBody) : {};
    } catch {
      return json({ error: "invalid_json" }, 400);
    }

    const secret = getSecret(env, platform);
    const isValid = await adapter.validateSignature(
      rawBody,
      request.headers,
      url.searchParams,
      secret
    );
    if (!isValid) {
      console.warn(`[${platform}] signature inválida`);
      return json({ error: "invalid_signature" }, 401);
    }

    // Shopify: topic vem em header
    if (platform === "shopify") {
      payload._topic = request.headers.get("x-shopify-topic") || "";
    }

    const ev = adapter.normalize(payload);

    // GHL dispatch é fire-and-forget — não bloqueia resposta ao webhook
    ctx.waitUntil(
      dispatchEventToGhl(env, ev).catch((err) => {
        console.error(`[${platform}] GHL dispatch falhou:`, err);
      })
    );

    return json({
      ok: true,
      platform: ev.platform,
      eventKind: ev.eventKind,
      rawEventType: ev.rawEventType,
    });
  },
};
