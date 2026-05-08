import { safeEqual } from "../crypto";
import type { EventKind, NormalizedEvent, PlatformAdapter } from "../types";
import { firstNameOf, normalizePhoneBr } from "../types";

export const HotmartAdapter: PlatformAdapter = {
  name: "hotmart",

  async validateSignature(_rawBody, headers, query, secret) {
    if (!secret) return true;
    const token =
      headers.get("x-hotmart-hottok") ||
      headers.get("hottok") ||
      query.get("hottok") ||
      "";
    return safeEqual(token, secret);
  },

  normalize(payload) {
    const data = payload.data || {};
    const buyer = data.buyer || {};
    const purchase = data.purchase || {};
    const product = data.product || {};
    const payment = purchase.payment || {};
    const price = purchase.price || {};

    const fullName = buyer.name || "";
    const phone = normalizePhoneBr(buyer.checkout_phone || buyer.phone || "");
    const valueCents = Math.round(parseFloat(price.value || "0") * 100) || 0;

    return {
      platform: "hotmart",
      eventKind: mapKind(payload.event || "", payment.type || ""),
      rawEventType: payload.event || "",
      customer: {
        name: fullName,
        firstName: firstNameOf(fullName),
        email: buyer.email || "",
        phone,
      },
      product: {
        name: product.name || "",
        id: String(product.id || product.ucode || ""),
        valueCents,
      },
      payment: {
        pixCode: payment.pix_code || payment.pix || "",
        pixExpiration: payment.pix_expiration_date || payment.pix_expiration || "",
        boletoUrl: payment.billet_url || payment.billet_link || "",
        boletoBarcode: payment.billet_barcode || "",
        boletoExpiry: purchase.date_next_charge || payment.billet_expiration || "",
        accessUrl: (data.subscription || {}).subscriber_url || "",
        rejectionReason: payment.refusal_reason || "",
        method: (payment.type || "").toLowerCase(),
      },
      rawPayload: payload,
    };
  },
};

function mapKind(rawEvt: string, rawType: string): EventKind {
  const evt = rawEvt.toUpperCase();
  const type = rawType.toUpperCase();
  if (evt === "PURCHASE_APPROVED") return "compra_aprovada";
  if (evt === "PURCHASE_REFUSED") return "recusada";
  if (evt === "PURCHASE_BILLET_PRINTED") return type === "BILLET" ? "boleto" : "pix";
  if (evt === "PURCHASE_PROTEST") return "recusada";
  if (evt === "PURCHASE_CANCELED") return "cancelada";
  if (evt === "PURCHASE_OUT_OF_SHOPPING_CART") return "carrinho";
  if (evt === "PURCHASE_COMPLETE") return "compra_aprovada";
  if (evt === "SUBSCRIPTION_CANCELLATION") return "cancelada";
  return "outro";
}
