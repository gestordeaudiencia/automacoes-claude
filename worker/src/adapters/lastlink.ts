import { hmacSha256Hex, safeEqual } from "../crypto";
import type { Address, EventKind, NormalizedEvent, PlatformAdapter, Tracking } from "../types";
import { firstNameOf, normalizePhoneBr } from "../types";

export const LastlinkAdapter: PlatformAdapter = {
  name: "lastlink",

  async validateSignature(rawBody, headers, _query, secret) {
    if (!secret) return true;
    let sig =
      headers.get("x-lastlink-signature") ||
      headers.get("x-lastlink-token") ||
      headers.get("x-hub-signature-256") ||
      "";
    if (sig.startsWith("sha256=")) sig = sig.slice(7);
    if (!sig) return false;
    const expected = await hmacSha256Hex(secret, rawBody);
    return safeEqual(expected, sig);
  },

  normalize(payload) {
    const data = payload.Data || {};
    const buyer = data.Buyer || {};
    const products: any[] = data.Products || [];
    const firstProduct = products[0] || {};
    const purchase = data.Purchase || {};
    const purchasePayment = purchase.Payment || {};
    const price = purchase.Price || purchase.OriginalPrice || {};
    const pix = purchase.Pix || {};
    const bankSlip = purchase.BankSlip || purchase.Boleto || {};
    const offer = data.Offer || {};
    const subscriptions: any[] = data.Subscriptions || [];
    const subscription = subscriptions[0] || {};
    const utm = data.Utm || {};
    const affiliate = purchase.Affiliate || {};
    const buyerAddr = buyer.Address || {};

    const fullName = buyer.Name || "";
    const phone = normalizePhoneBr(buyer.PhoneNumber || buyer.Phone || "");
    const valueCents = Math.round(parseFloat(price.Value || "0") * 100) || 0;
    const method = (purchasePayment.PaymentMethod || purchasePayment.Method || "").toLowerCase();

    const address: Address | undefined = buyerAddr.Street || buyerAddr.City
      ? {
          zipCode: buyerAddr.ZipCode || "",
          street: buyerAddr.Street || "",
          streetNumber: buyerAddr.StreetNumber || "",
          complement: buyerAddr.Complement || "",
          district: buyerAddr.District || "",
          city: buyerAddr.City || "",
          state: buyerAddr.State || "",
        }
      : undefined;

    const tracking: Tracking | undefined = utm.UtmSource || utm.UtmMedium || affiliate.Id
      ? {
          utmSource: utm.UtmSource || "",
          utmMedium: utm.UtmMedium || "",
          utmCampaign: utm.UtmCampaign || "",
          utmTerm: utm.UtmTerm || "",
          utmContent: utm.UtmContent || "",
          src: utm.Src || "",
          sck: utm.Sck || "",
          vtid: utm.Vtid || "",
          affiliateId: affiliate.Id || "",
          affiliateEmail: affiliate.Email || "",
        }
      : undefined;

    return {
      platform: "lastlink",
      eventKind: mapKind(payload.Event || "", method),
      rawEventType: payload.Event || "",
      isTest: Boolean(payload.IsTest),
      customer: {
        name: fullName,
        firstName: firstNameOf(fullName),
        email: buyer.Email || "",
        phone,
        document: buyer.Document || "",
        address,
      },
      product: {
        name: firstProduct.Name || "",
        id: String(firstProduct.Id || ""),
        valueCents,
      },
      payment: {
        pixCode: pix.QrCodeText || "",
        pixQrUrl: pix.QrCode || "",
        pixExpiration: pix.ExpirationDate || pix.ExpiresAt || "",
        // Lastlink BankSlip schema:
        // - DigitableLine = linha digitável (humano)
        // - BarCodeData = código de barras numérico puro
        // - BarCode = URL da imagem do código de barras
        // Não há "URL do boleto" — usar InvoiceUrl como fallback
        boletoUrl: purchase.InvoiceUrl || bankSlip.Url || bankSlip.BankSlipUrl || "",
        boletoBarcode: bankSlip.DigitableLine || bankSlip.Barcode || bankSlip.BankSlipBarcode || "",
        boletoBarcodeRaw: bankSlip.BarCodeData || "",
        boletoBarcodeImage: bankSlip.BarCode || "",
        boletoExpiry: bankSlip.DueDate || bankSlip.BankSlipDueDate || subscription.NextBilling || "",
        accessUrl: offer.Url || subscription.SubscriberUrl || "",
        invoiceUrl: purchase.InvoiceUrl || "",
        rejectionReason: purchasePayment.RefusalReason || "",
        method,
        installments: purchasePayment.NumberOfInstallments || undefined,
        paymentId: purchase.PaymentId || "",
        paymentDate: purchase.PaymentDate || "",
      },
      tracking,
      subscription:
        subscription.Id ||
        purchase.NextBilling ||
        purchase.ChargebackDate ||
        subscription.CanceledDate ||
        subscription.ExpiredDate
          ? {
            id: subscription.Id || "",
            recurrency: typeof purchase.Recurrency === "number" ? purchase.Recurrency : undefined,
            status: subscription.Status || "",
            nextBilling: purchase.NextBilling || "",
            canceledDate: subscription.CanceledDate || "",
            expiredDate: subscription.ExpiredDate || "",
            cancellationReason: subscription.CancellationReason || "",
            chargebackDate: purchase.ChargebackDate || "",
          }
          : undefined,
      rawPayload: payload,
    };
  },
};

function mapKind(rawEvt: string, rawMethod: string): EventKind {
  const e = rawEvt.toLowerCase();
  const m = rawMethod.toLowerCase();

  if (
    e === "purchase_order_confirmed" ||
    e === "purchase_order_completed" ||
    e === "purchase_approved" ||
    e === "purchase_complete" ||
    e === "membership_started" ||
    e === "access_release_started"
  ) {
    return "compra_aprovada";
  }

  if (
    e === "purchase_request_confirmed" ||
    e === "purchase_request_created" ||
    e === "purchase_pending_payment" ||
    e === "invoice_created"
  ) {
    if (m.includes("pix")) return "pix";
    if (m.includes("bankslip") || m.includes("boleto")) return "boleto";
    return "outro";
  }

  if (e === "subscription_renewal_pending") {
    if (m.includes("pix")) return "pix";
    if (m.includes("bankslip") || m.includes("boleto")) return "boleto";
    return "outro";
  }

  if (
    e === "subscription_renewal_approved" ||
    e === "subscription_renewed" ||
    e === "renewal_payment_completed"
  ) {
    return "renovacao";
  }

  if (
    e === "purchase_request_expired" ||
    e === "purchase_expired" ||
    e === "purchase_order_expired"
  ) {
    if (m.includes("pix")) return "pix";
    if (m.includes("bankslip") || m.includes("boleto")) return "boleto";
    return "cancelada";
  }

  if (
    e === "purchase_canceled" ||
    e === "purchase_cancelled" ||
    e === "purchase_request_canceled" ||
    e === "purchase_request_cancelled" ||
    e === "subscription_canceled" ||
    e === "subscription_expired" ||
    e === "payment_chargeback" ||
    e === "payment_refunded" ||
    e === "payment_refund" ||
    e === "payment_reversal" ||
    e === "payment_reversed" ||
    e === "membership_ended" ||
    e === "access_release_ended" ||
    e === "refund_period_ended" ||
    e === "refund_requested"
  ) {
    return "cancelada";
  }

  if (e === "purchase_refused" || e === "purchase_failed" || e === "payment_failed") {
    return "recusada";
  }

  if (e === "abandoned_cart" || e === "purchase_abandoned" || e === "cart_abandoned") {
    return "carrinho";
  }

  // Refund_Period_Over: cliente passou prazo de 7 dias, "venda firmada"
  // Não é cancelada (cliente continua), não é recompra. Marca como "outro" — workflow custom via raw_event_type
  if (e === "refund_period_over" || e === "refund_period_ended") {
    return "outro";
  }

  return "outro";
}
