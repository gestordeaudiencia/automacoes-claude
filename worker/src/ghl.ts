/**
 * Cliente mínimo da API GHL (LeadConnector).
 *
 * Docs: https://highlevel.stoplight.io/docs/integrations/
 *
 * Estratégia: pra cada evento normalizado, fazemos:
 *   1. upsertContact   → cria/atualiza contato com email/phone/name + custom fields
 *   2. addTags         → tag indica o tipo de evento (ex: "ev:pix", "produto:investidor")
 *   3. (opcional) addContactToWorkflow → dispara workflow GHL pré-montado
 *
 * Workflows ficam montados na UI GHL — eles cuidam de waits, mensagens, condicionais.
 * Aqui só populamos os dados certos.
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
  const body = {
    locationId: env.GHL_LOCATION_ID,
    firstName: ev.customer.firstName || undefined,
    name: ev.customer.name || undefined,
    email: ev.customer.email || undefined,
    phone: ev.customer.phone ? `+${ev.customer.phone}` : undefined,
    source: ev.platform,
    customFields: buildCustomFields(ev),
  };

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

/**
 * Tags geradas automaticamente pra cada evento.
 * Workflows GHL são triggados por essas tags (Trigger: "Tag added").
 */
export function buildTagsFor(ev: NormalizedEvent): string[] {
  const tags: string[] = [
    `platform:${ev.platform}`,
    `ev:${ev.eventKind}`,
  ];
  if (ev.product.name) {
    const slug = ev.product.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 40);
    tags.push(`produto:${slug}`);
  }
  if (ev.payment.method) tags.push(`pgto:${ev.payment.method}`);
  return tags;
}

function buildCustomFields(ev: NormalizedEvent): Array<{ key: string; field_value: string }> {
  // Os keys precisam corresponder aos custom fields cadastrados na location GHL.
  // Cliente cria estes campos uma vez na UI GHL antes de usar.
  // Adicione/remova conforme tua location.
  const fields: Array<{ key: string; field_value: string }> = [];
  const push = (key: string, val: string | undefined) => {
    if (val) fields.push({ key, field_value: val });
  };

  push("plataforma_origem", ev.platform);
  push("evento_recente", ev.eventKind);
  push("produto_nome", ev.product.name);
  push("produto_id", ev.product.id);
  push("valor_brl", valueBrl(ev.product.valueCents));
  push("pix_code", ev.payment.pixCode);
  push("pix_expiration", ev.payment.pixExpiration);
  push("boleto_url", ev.payment.boletoUrl);
  push("boleto_barcode", ev.payment.boletoBarcode);
  push("boleto_expiry", ev.payment.boletoExpiry);
  push("access_url", ev.payment.accessUrl);
  push("rejection_reason", ev.payment.rejectionReason);

  return fields;
}

/**
 * Pipeline completo: upsert + tags + (opcional) workflow.
 */
export async function dispatchEventToGhl(env: GhlEnv, ev: NormalizedEvent): Promise<{
  contactId: string;
  tags: string[];
}> {
  const contact = await upsertContact(env, ev);
  const tags = buildTagsFor(ev);
  await addTags(env, contact.id, tags);
  return { contactId: contact.id, tags };
}
