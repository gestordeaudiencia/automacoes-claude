import { hmacSha256Hex, safeEqual } from "../crypto";
import type { EventKind, NormalizedEvent, PlatformAdapter } from "../types";
import { firstNameOf, normalizePhoneBr } from "../types";

export const LastlinkAdapter: PlatformAdapter = {
  name: "lastlink",

  async validateSignature(rawBody, headers, _query, secret) {
    if (!secret) return true;
    let sig =
      headers.get("x-lastlink-signature") || headers.get("x-hub-signature-256") || "";
    if (sig.startsWith("sha256=")) sig = sig.slice(7);
    const expected = await hmacSha256Hex(secret, rawBody);
    return safeEqual(expected, sig);
  },

  normalize(payload) {
    const data = payload.Data || {};
    const buyer = data.Buyer || {};
    const products: any[] = data.Products || [];
    const firstProduct = products[0] || {};
    const payment = data.Payment || {};
    const offer = data.Offer || {};

    const fullName = buyer.Name || "";
    const phone = normalizePhoneBr(buyer.PhoneNumber || buyer.Phone || "");
    const valueCents =
      Math.round(parseFloat(payment.Amount || payment.TotalAmount || "0") * 100) || 0;

    return {
      platform: "lastlink",
      eventKind: mapKind(payload.Event || "", payment.Method || ""),
      rawEventType: payload.Event || "",
      customer: {
        name: fullName,
        firstName: firstNameOf(fullName),
        email: buyer.Email || "",
        phone,
      },
      product: {
        name: firstProduct.Name || "",
        id: String(firstProduct.Id || ""),
        valueCents,
      },
      payment: {
        pixCode: payment.PixCode || payment.PixCopyPaste || "",
        pixExpiration: payment.PixExpirationDate || "",
        boletoUrl: payment.BankSlipUrl || payment.BoletoUrl || "",
        boletoBarcode: payment.BankSlipBarcode || payment.BoletoBarcode || "",
        boletoExpiry: payment.BankSlipDueDate || payment.BoletoExpiry || "",
        accessUrl: offer.Url || data.AccessUrl || "",
        rejectionReason: payment.RefusalReason || "",
        method: (payment.Method || "").toLowerCase(),
      },
      rawPayload: payload,
    };
  },
};

function mapKind(rawEvt: string, rawMethod: string): EventKind {
  const e = rawEvt.toLowerCase();
  const m = rawMethod.toLowerCase();
  if (e === "purchase_order_confirmed" || e === "purchase_approved") return "compra_aprovada";
  if (
    e === "purchase_request_confirmed" ||
    e === "purchase_pending_payment" ||
    e === "purchase_request_created"
  ) {
    if (m.includes("pix")) return "pix";
    if (m.includes("bankslip") || m.includes("boleto")) return "boleto";
    return "outro";
  }
  if (e === "purchase_request_expired" || e === "purchase_canceled" || e === "subscription_canceled")
    return "cancelada";
  if (e === "purchase_refused" || e === "purchase_failed") return "recusada";
  if (e === "abandoned_cart" || e === "purchase_abandoned") return "carrinho";
  if (e === "subscription_renewed") return "renovacao";
  return "outro";
}
