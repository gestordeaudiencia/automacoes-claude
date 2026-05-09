import { hmacSha1Hex, safeEqual } from "../crypto";
import type { EventKind, NormalizedEvent, PlatformAdapter } from "../types";
import { firstNameOf, normalizePhoneBr, valueBrl } from "../types";

export const KiwifyAdapter: PlatformAdapter = {
  name: "kiwify",

  async validateSignature(rawBody, _headers, query, secret) {
    if (!secret) return true;
    const signature = (query.get("signature") || "").toLowerCase();
    if (!signature) return false;

    // Tenta raw body
    const expectedRaw = await hmacSha1Hex(secret, rawBody);
    if (safeEqual(expectedRaw, signature)) return true;

    // Fallback: re-stringify (compat com n8n / payload já parseado)
    try {
      const body = JSON.parse(rawBody);
      const canonical = JSON.stringify(body);
      const expectedCanon = await hmacSha1Hex(secret, canonical);
      return safeEqual(expectedCanon, signature);
    } catch {
      return false;
    }
  },

  normalize(payload) {
    const customer = payload.Customer || {};
    const product = payload.Product || {};
    const commissions = payload.Commissions || {};

    const fullName = customer.full_name || customer.first_name || "";
    const phone = normalizePhoneBr(customer.mobile || customer.phone || "");
    const valueCents = Math.round(parseFloat(commissions.charge_amount || "0") * 100) || 0;

    return {
      platform: "kiwify",
      eventKind: mapKind(payload.webhook_event_type || ""),
      rawEventType: payload.webhook_event_type || "",
      isTest: Boolean(payload.is_test || payload.test),
      customer: {
        name: fullName,
        firstName: firstNameOf(fullName),
        email: customer.email || "",
        phone,
      },
      product: {
        name: product.product_name || "",
        id: product.product_id || "",
        valueCents,
      },
      payment: {
        pixCode: payload.pix_code || "",
        pixExpiration: payload.pix_expiration || "",
        boletoUrl: payload.boleto_URL || payload.boleto_url || "",
        boletoBarcode: payload.boleto_barcode || "",
        boletoExpiry: payload.boleto_expiry_date || "",
        accessUrl: payload.access_url || "",
        rejectionReason: payload.card_rejection_reason || "",
        method: payload.payment_method || "",
      },
      rawPayload: payload,
    };
  },
};

function mapKind(raw: string): EventKind {
  const e = raw.toLowerCase();
  if (e === "pix_created") return "pix";
  if (e === "billet_created" || e === "boleto_created") return "boleto";
  if (e === "order_approved") return "compra_aprovada";
  if (e === "order_refused") return "recusada";
  if (e === "abandoned_cart" || e === "cart_abandoned") return "carrinho";
  if (e === "subscription_canceled") return "cancelada";
  if (e === "subscription_renewed") return "renovacao";
  return "outro";
}

export { valueBrl };
