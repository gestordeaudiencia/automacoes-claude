/**
 * Cliente mínimo da API GHL (LeadConnector).
 *
 * Pra cada evento normalizado:
 *   1. upsertContact   → cria/atualiza contato (email/phone/name) + custom fields
 *   2. addTags         → tags trigam workflows GHL
 *
 * Workflows ficam montados na UI GHL.
 */

import type { NormalizedEvent } from "./types";
import { valueBrl } from "./types";

export interface GhlEnv {
  GHL_API_KEY: string;
  GHL_LOCATION_ID: string;
  GHL_BASE_URL?: string;
}

interface GhlContact {
  id: string;
  contactId?: string;
}

const DEFAULT_BASE = "https://services.leadconnectorhq.com";
const API_VERSION = "2021-07-28";

async function ghlFetch(env: GhlEnv, path: string, init: RequestInit = {}): Promise<Response> {
  const base = env.GHL_BASE_URL || DEFAULT_BASE;
  return fetch(`${base}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${env.GHL_API_KEY}`,
      "Content-Type": "application/json",
      Accept: "application/json",
      Version: API_VERSION,
      ...(init.headers || {}),
    },
  });
}

export async function upsertContact(env: GhlEnv, ev: NormalizedEvent): Promise<GhlContact> {
  const addr = ev.customer.address;
  const body: Record<string, unknown> = {
    locationId: env.GHL_LOCATION_ID,
    firstName: ev.customer.firstName || undefined,
    name: ev.customer.name || undefined,
    email: ev.customer.email || undefined,
    phone: ev.customer.phone ? `+${ev.customer.phone}` : undefined,
    source: ev.platform,
    customFields: buildCustomFields(ev),
  };
  if (addr) {
    body.address1 = [addr.street, addr.streetNumber, addr.complement].filter(Boolean).join(", ");
    body.city = addr.city;
    body.state = addr.state;
    body.postalCode = addr.zipCode;
    body.country = addr.country || "BR";
  }

  const res = await ghlFetch(env, "/contacts/upsert", {
    method: "POST",
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GHL upsertContact ${res.status}: ${text}`);
  }
  const data = (await res.json()) as { contact?: { id: string } };
  const id = data.contact?.id;
  if (!id) throw new Error("GHL upsertContact não retornou contact.id");
  return { id };
}

export async function addTags(env: GhlEnv, contactId: string, tags: string[]): Promise<void> {
  if (!tags.length) return;
  const res = await ghlFetch(env, `/contacts/${contactId}/tags`, {
    method: "POST",
    body: JSON.stringify({ tags }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GHL addTags ${res.status}: ${text}`);
  }
}

export async function addToWorkflow(
  env: GhlEnv,
  contactId: string,
  workflowId: string
): Promise<void> {
  if (!workflowId) return;
  const res = await ghlFetch(env, `/contacts/${contactId}/workflow/${workflowId}`, {
    method: "POST",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GHL addToWorkflow ${res.status}: ${text}`);
  }
}

export function buildTagsFor(ev: NormalizedEvent): string[] {
  const tags: string[] = [`platform:${ev.platform}`, `ev:${ev.eventKind}`];
  if (ev.product.name) {
    const slug = ev.product.name
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .slice(0, 40)
      .replace(/^-|-$/g, "");
    if (slug) tags.push(`produto:${slug}`);
  }
  if (ev.payment.method) tags.push(`pgto:${ev.payment.method}`);
  if (ev.isTest) tags.push("source:test");
  if (ev.tracking?.utmSource) {
    const utm = ev.tracking.utmSource.toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 30);
    if (utm) tags.push(`utm:${utm}`);
  }

  // Tags específicas pra trigger limpo de workflows (evita ambiguidade entre
  // ev:pix de "fatura criada" vs ev:pix de "expirado").
  const raw = (ev.rawEventType || "").toLowerCase();
  if (raw.includes("expired") || raw.includes("expirad")) {
    if (ev.eventKind === "pix") tags.push("pix_expirado");
    else if (ev.eventKind === "boleto") tags.push("boleto_expirado");
    else tags.push("expirado");
  }
  if (raw.includes("canceled") || raw.includes("cancelled") || raw.includes("cancelad")) {
    tags.push("pedido_cancelado");
  }
  if (raw.includes("refund") || raw.includes("reversal") || raw.includes("reversed") || raw.includes("chargeback")) {
    tags.push("refund_solicitado");
  }
  if (raw.includes("refused") || raw.includes("failed") || raw.includes("recusad")) {
    tags.push("pagamento_recusado");
  }

  return tags;
}

function buildCustomFields(ev: NormalizedEvent): Array<{ key: string; field_value: string }> {
  // Os keys precisam corresponder aos custom fields cadastrados na location GHL.
  // Snake_case é o que GHL gera por padrão a partir do nome do campo.
  const fields: Array<{ key: string; field_value: string }> = [];
  const push = (key: string, val: string | number | undefined | null) => {
    if (val === undefined || val === null || val === "") return;
    fields.push({ key, field_value: String(val) });
  };

  // Plataforma + evento
  push("plataforma_origem", ev.platform);
  push("evento_recente", ev.eventKind);
  push("raw_event_type", ev.rawEventType);

  // Produto
  push("produto_nome", ev.product.name);
  push("produto_id", ev.product.id);
  push("valor_brl", valueBrl(ev.product.valueCents));

  // Pagamento
  push("pix_code", ev.payment.pixCode);
  push("pix_qr_url", ev.payment.pixQrUrl);
  push("pix_expiration", ev.payment.pixExpiration);
  push("boleto_url", ev.payment.boletoUrl);
  push("boleto_barcode", ev.payment.boletoBarcode);
  push("boleto_expiry", ev.payment.boletoExpiry);
  push("invoice_url", ev.payment.invoiceUrl);
  push("access_url", ev.payment.accessUrl);
  push("rejection_reason", ev.payment.rejectionReason);
  push("payment_method", ev.payment.method);

  // Cliente
  push("documento", ev.customer.document);

  // Tracking / atribuição
  if (ev.tracking) {
    push("utm_source", ev.tracking.utmSource);
    push("utm_medium", ev.tracking.utmMedium);
    push("utm_campaign", ev.tracking.utmCampaign);
    push("utm_term", ev.tracking.utmTerm);
    push("utm_content", ev.tracking.utmContent);
    push("affiliate_id", ev.tracking.affiliateId);
    push("affiliate_email", ev.tracking.affiliateEmail);
  }

  // Assinatura
  if (ev.subscription) {
    push("subscription_id", ev.subscription.id);
    push("subscription_recurrency", ev.subscription.recurrency);
  }

  return fields;
}

export async function dispatchEventToGhl(env: GhlEnv, ev: NormalizedEvent): Promise<{
  contactId: string;
  tags: string[];
}> {
  const contact = await upsertContact(env, ev);
  const tags = buildTagsFor(ev);
  await addTags(env, contact.id, tags);
  return { contactId: contact.id, tags };
}
