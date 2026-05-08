import { hmacSha256Base64, safeEqual } from "../crypto";
import type { EventKind, NormalizedEvent, PlatformAdapter } from "../types";
import { firstNameOf, normalizePhoneBr } from "../types";

export const ShopifyAdapter: PlatformAdapter = {
  name: "shopify",

  async validateSignature(rawBody, headers, _query, secret) {
    if (!secret) return true;
    const sig =
      headers.get("x-shopify-hmac-sha256") ||
      headers.get("x-shopify-hmac-sha-256") ||
      "";
    if (!sig) return false;
    const expected = await hmacSha256Base64(secret, rawBody);
    return safeEqual(expected, sig);
  },

  normalize(payload) {
    const customer = payload.customer || {};
    const billing = payload.billing_address || payload.shipping_address || {};
    const lineItems: any[] = payload.line_items || [];

    const fullName =
      `${customer.first_name || ""} ${customer.last_name || ""}`.trim() ||
      billing.name ||
      "";
    const email = customer.email || payload.email || billing.email || "";
    const phone = normalizePhoneBr(customer.phone || payload.phone || billing.phone);

    const totalCents = Math.round(parseFloat(payload.total_price || "0") * 100) || 0;
    const productName = lineItems
      .map((li) => li.title || "")
      .filter(Boolean)
      .join(", ")
      .slice(0, 200);
    const productId = lineItems.map((li) => String(li.product_id || "")).join(",");

    const noteAttrs: any[] = payload.note_attributes || [];
    const meta: Record<string, string> = {};
    for (const a of noteAttrs) {
      if (a && typeof a.name === "string") meta[a.name.toLowerCase()] = a.value || "";
    }

    return {
      platform: "shopify",
      eventKind: mapKind(payload),
      rawEventType: payload._topic || "",
      customer: {
        name: fullName,
        firstName: firstNameOf(fullName),
        email,
        phone,
      },
      product: {
        name: productName,
        id: productId,
        valueCents: totalCents,
      },
      payment: {
        pixCode: meta.pix_code || "",
        pixExpiration: meta.pix_expiration || "",
        boletoUrl: meta.boleto_url || "",
        boletoBarcode: meta.boleto_barcode || "",
        boletoExpiry: meta.boleto_expiry || "",
        accessUrl: payload.order_status_url || "",
        rejectionReason: payload.cancel_reason || "",
        method: (payload.gateway || "").toLowerCase(),
      },
      rawPayload: payload,
    };
  },
};

function mapKind(payload: any): EventKind {
  const topic = (payload._topic || "").toLowerCase();
  const gateway = (payload.gateway || "").toLowerCase();
  const financial = (payload.financial_status || "").toLowerCase();

  if (topic === "orders/paid" || financial === "paid") return "compra_aprovada";
  if (topic === "orders/cancelled" || financial === "voided") return "cancelada";
  if (topic === "orders/create" && financial === "pending") {
    if (gateway.includes("mercado") || gateway.includes("pix")) return "pix";
    if (gateway.includes("boleto")) return "boleto";
  }
  if (topic === "checkouts/create" || topic === "checkouts/update") {
    if (payload.abandoned_checkout_url || !payload.completed_at) return "carrinho";
  }
  return "outro";
}
