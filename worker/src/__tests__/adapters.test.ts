import { describe, expect, it } from "vitest";
import { getAdapter, listPlatforms } from "../adapters";
import { hmacSha1Hex, hmacSha256Base64, hmacSha256Hex } from "../crypto";
import { buildTagsFor } from "../ghl";

function buildHeaders(map: Record<string, string>): Headers {
  const h = new Headers();
  for (const [k, v] of Object.entries(map)) h.set(k, v);
  return h;
}

function buildQuery(map: Record<string, string>): URLSearchParams {
  return new URLSearchParams(map);
}

// ---------- Kiwify ----------

describe("Kiwify adapter", () => {
  const adapter = getAdapter("kiwify")!;
  const payload = {
    webhook_event_type: "pix_created",
    Customer: { full_name: "João Silva", email: "j@x.com", mobile: "11987654321" },
    Product: { product_name: "Investidor Coeso", product_id: "p1" },
    Commissions: { charge_amount: "197.00" },
    pix_code: "00020126...",
    pix_expiration: "2026-05-08",
  };
  const raw = JSON.stringify(payload);

  it("valida HMAC-SHA1 query", async () => {
    const sig = await hmacSha1Hex("sec", raw);
    expect(
      await adapter.validateSignature(raw, buildHeaders({}), buildQuery({ signature: sig }), "sec")
    ).toBe(true);
  });

  it("rejeita signature inválida", async () => {
    expect(
      await adapter.validateSignature(raw, buildHeaders({}), buildQuery({ signature: "x" }), "sec")
    ).toBe(false);
  });

  it("normaliza pix_created → pix", () => {
    const ev = adapter.normalize(payload);
    expect(ev.platform).toBe("kiwify");
    expect(ev.eventKind).toBe("pix");
    expect(ev.customer.firstName).toBe("João");
    expect(ev.product.valueCents).toBe(19700);
  });

  it.each([
    ["billet_created", "boleto"],
    ["order_approved", "compra_aprovada"],
    ["order_refused", "recusada"],
    ["abandoned_cart", "carrinho"],
    ["evento_estranho", "outro"],
  ])("event_kind: %s → %s", (raw, expected) => {
    expect(adapter.normalize({ webhook_event_type: raw }).eventKind).toBe(expected);
  });
});

// ---------- Hotmart ----------

describe("Hotmart adapter", () => {
  const adapter = getAdapter("hotmart")!;
  const payload = {
    event: "PURCHASE_APPROVED",
    data: {
      buyer: { name: "Maria Souza", email: "m@x.com", checkout_phone: "11999998888" },
      purchase: { payment: { type: "CREDIT_CARD" }, price: { value: 297.0 } },
      product: { id: 99, name: "Curso XPTO" },
    },
  };

  it("valida Hottok", async () => {
    expect(
      await adapter.validateSignature("", buildHeaders({ "x-hotmart-hottok": "tok" }), buildQuery({}), "tok")
    ).toBe(true);
    expect(
      await adapter.validateSignature("", buildHeaders({ "x-hotmart-hottok": "x" }), buildQuery({}), "tok")
    ).toBe(false);
  });

  it("normaliza PURCHASE_APPROVED", () => {
    const ev = adapter.normalize(payload);
    expect(ev.eventKind).toBe("compra_aprovada");
    expect(ev.customer.firstName).toBe("Maria");
    expect(ev.product.valueCents).toBe(29700);
  });

  it("PIX vs BILLET via payment.type", () => {
    const base: any = { event: "PURCHASE_BILLET_PRINTED", data: { purchase: { payment: { type: "PIX" } } } };
    expect(adapter.normalize(base).eventKind).toBe("pix");
    base.data.purchase.payment.type = "BILLET";
    expect(adapter.normalize(base).eventKind).toBe("boleto");
  });
});

// ---------- Shopify ----------

describe("Shopify adapter", () => {
  const adapter = getAdapter("shopify")!;
  const payload = {
    _topic: "orders/paid",
    id: 12345,
    email: "buyer@x.com",
    phone: "+5511999998888",
    total_price: "397.00",
    financial_status: "paid",
    customer: { first_name: "Carlos", last_name: "Lima" },
    line_items: [{ title: "Camiseta", product_id: 99 }],
    order_status_url: "https://shop/orders/12345",
  };
  const raw = JSON.stringify(payload);

  it("valida HMAC-SHA256 base64", async () => {
    const sig = await hmacSha256Base64("sec", raw);
    expect(
      await adapter.validateSignature(raw, buildHeaders({ "x-shopify-hmac-sha256": sig }), buildQuery({}), "sec")
    ).toBe(true);
    expect(
      await adapter.validateSignature(raw, buildHeaders({ "x-shopify-hmac-sha256": "x" }), buildQuery({}), "sec")
    ).toBe(false);
  });

  it("orders/paid → compra_aprovada", () => {
    const ev = adapter.normalize(payload);
    expect(ev.eventKind).toBe("compra_aprovada");
    expect(ev.customer.firstName).toBe("Carlos");
    expect(ev.product.valueCents).toBe(39700);
  });
});

// ---------- Lastlink (real schema, validado contra payloads reais) ----------

describe("Lastlink adapter — schema real", () => {
  const adapter = getAdapter("lastlink")!;

  const renewalPendingPix = {
    Id: "evt-1",
    IsTest: true,
    Event: "Subscription_Renewal_Pending",
    Data: {
      Products: [{ Id: "prod-1", Name: "Claude Code do zero ao avançado" }],
      Buyer: {
        Id: "buyer-1",
        Email: "test@example.com",
        Name: "Moises Pereira",
        PhoneNumber: "+5500987645312",
        Document: "663.614.400-95",
        Address: { ZipCode: "15056-131", Street: "Rua A", StreetNumber: "1", City: "São Paulo", State: "SP" },
      },
      Purchase: {
        Recurrency: 1,
        Price: { Value: 12.5 },
        Payment: { NumberOfInstallments: 1, PaymentMethod: "pix" },
        Affiliate: { Id: "aff-1", Email: "aff@x.com" },
        Pix: { QrCode: "https://pix.com/qr", QrCodeText: "00020126..." },
        InvoiceUrl: "https://invoice.lastlink.com/test",
      },
      Subscriptions: [{ Id: "sub-1", ProductId: "prod-1" }],
      Offer: { Id: "off-1", Name: "Oferta", Url: "https://lastlink.com/p/X" },
      Utm: { UtmSource: "instagram", UtmMedium: "stories", UtmCampaign: "lanc-2026" },
    },
  };
  const raw = JSON.stringify(renewalPendingPix);

  it("valida HMAC-SHA256 hex (com e sem prefixo sha256=)", async () => {
    const sig = await hmacSha256Hex("ll", raw);
    expect(
      await adapter.validateSignature(raw, buildHeaders({ "x-lastlink-signature": sig }), buildQuery({}), "ll")
    ).toBe(true);
    expect(
      await adapter.validateSignature(raw, buildHeaders({ "x-lastlink-signature": `sha256=${sig}` }), buildQuery({}), "ll")
    ).toBe(true);
    expect(
      await adapter.validateSignature(raw, buildHeaders({ "x-lastlink-signature": "wrong" }), buildQuery({}), "ll")
    ).toBe(false);
  });

  it("Subscription_Renewal_Pending (pix) → pix", () => {
    const ev = adapter.normalize(renewalPendingPix);
    expect(ev.platform).toBe("lastlink");
    expect(ev.eventKind).toBe("pix");
    expect(ev.isTest).toBe(true);
    expect(ev.customer.firstName).toBe("Moises");
    expect(ev.customer.document).toBe("663.614.400-95");
    expect(ev.customer.address?.city).toBe("São Paulo");
    expect(ev.product.valueCents).toBe(1250);
    expect(ev.payment.pixCode).toBe("00020126...");
    expect(ev.payment.pixQrUrl).toBe("https://pix.com/qr");
    expect(ev.payment.invoiceUrl).toBe("https://invoice.lastlink.com/test");
    expect(ev.tracking?.utmSource).toBe("instagram");
    expect(ev.tracking?.affiliateEmail).toBe("aff@x.com");
    expect(ev.subscription?.id).toBe("sub-1");
    expect(ev.subscription?.recurrency).toBe(1);
  });

  it("Purchase_Order_Confirmed (real payload) → compra_aprovada", () => {
    const ev = adapter.normalize({
      Event: "Purchase_Order_Confirmed",
      IsTest: true,
      Data: {
        Products: [{ Id: "p1", Name: "Curso" }],
        Buyer: { Email: "x@x.com", Name: "Moises" },
        Purchase: {
          PaymentId: "pay-1",
          PaymentDate: "2026-05-09T23:47:50Z",
          NextBilling: "2026-06-09T23:47:50Z",
          Price: { Value: 12.5 },
          Payment: { PaymentMethod: "pix", NumberOfInstallments: 1 },
          Pix: { QrCode: "https://qr", QrCodeText: "code" },
          InvoiceUrl: "https://inv",
        },
        Subscriptions: [{ Id: "sub-1" }],
      },
    });
    expect(ev.eventKind).toBe("compra_aprovada");
    expect(ev.payment.paymentId).toBe("pay-1");
    expect(ev.subscription?.nextBilling).toBe("2026-06-09T23:47:50Z");
  });

  it("Purchase_Request_Expired (bankslip) → boleto", () => {
    const ev = adapter.normalize({
      Event: "Purchase_Request_Expired",
      Data: {
        Products: [{ Id: "p1", Name: "X" }],
        Buyer: { Name: "Y" },
        Purchase: {
          Payment: { PaymentMethod: "bankslip" },
          BankSlip: {
            DigitableLine: "34191.09008 63571.277447 91020.150008 5 12340000000000",
            BarCodeData: "341911902000635712774479102015000812340000000000",
            BarCode: "https://barcode.com.br/barcode",
          },
          InvoiceUrl: "https://inv",
        },
        Subscriptions: [{ Id: "sub-1", ExpiredDate: "2026-05-09T23:47:50Z" }],
      },
    });
    expect(ev.eventKind).toBe("boleto");
    expect(ev.payment.boletoBarcode).toBe("34191.09008 63571.277447 91020.150008 5 12340000000000");
    expect(ev.payment.boletoBarcodeRaw).toBe("341911902000635712774479102015000812340000000000");
    expect(ev.payment.boletoBarcodeImage).toBe("https://barcode.com.br/barcode");
    expect(ev.payment.boletoUrl).toBe("https://inv");
    expect(ev.subscription?.expiredDate).toBe("2026-05-09T23:47:50Z");
  });

  it("Purchase_Request_Canceled → cancelada (com reason + canceledDate)", () => {
    const ev = adapter.normalize({
      Event: "Purchase_Request_Canceled",
      Data: {
        Products: [{ Id: "p1", Name: "X" }],
        Buyer: { Name: "Y" },
        Purchase: { Payment: { PaymentMethod: "bankslip" } },
        Subscriptions: [
          {
            Id: "sub-1",
            CanceledDate: "2026-05-09T23:47:50Z",
            CancellationReason: "Teste de cancelamento",
          },
        ],
      },
    });
    expect(ev.eventKind).toBe("cancelada");
    expect(ev.subscription?.canceledDate).toBe("2026-05-09T23:47:50Z");
    expect(ev.subscription?.cancellationReason).toBe("Teste de cancelamento");
  });

  it("Payment_Refund (com chargebackDate) → cancelada", () => {
    const ev = adapter.normalize({
      Event: "Payment_Refund",
      Data: {
        Products: [{ Id: "p1", Name: "X" }],
        Buyer: { Name: "Y" },
        Purchase: {
          ChargebackDate: "2026-05-09T23:47:50Z",
          PaymentDate: "2026-05-08T00:00:00Z",
          Payment: { PaymentMethod: "bankslip" },
          BankSlip: { DigitableLine: "X", BarCodeData: "Y" },
        },
      },
    });
    expect(ev.eventKind).toBe("cancelada");
    expect(ev.subscription?.chargebackDate).toBe("2026-05-09T23:47:50Z");
    expect(ev.payment.paymentDate).toBe("2026-05-08T00:00:00Z");
  });

  it("Refund_Period_Over → outro (workflow custom)", () => {
    const ev = adapter.normalize({ Event: "Refund_Period_Over", Data: {} });
    expect(ev.eventKind).toBe("outro");
    expect(ev.rawEventType).toBe("Refund_Period_Over");
  });

  it("Abandoned_Cart minimal (sem Purchase) → carrinho", () => {
    const ev = adapter.normalize({
      Event: "Abandoned_Cart",
      IsTest: true,
      Data: {
        Products: [{ Id: "p1", Name: "Curso" }],
        Buyer: { Email: "x@x.com", Name: "João da Silva", PhoneNumber: "+5500987645312" },
        Offer: { Url: "https://lastlink.com/p/ABC" },
        Utm: { UtmSource: "instagram" },
      },
    });
    expect(ev.eventKind).toBe("carrinho");
    expect(ev.product.valueCents).toBe(0); // sem Purchase = sem Price
    expect(ev.payment.method).toBe("");
    expect(ev.payment.accessUrl).toBe("https://lastlink.com/p/ABC");
    expect(ev.tracking?.utmSource).toBe("instagram");
  });

  it.each([
    ["Subscription_Renewal_Approved", "renovacao"],
    ["Subscription_Canceled", "cancelada"],
    ["Subscription_Expired", "cancelada"],
    ["Purchase_Refused", "recusada"],
  ])("event_kind: %s → %s", (rawEvt, expected) => {
    expect(adapter.normalize({ Event: rawEvt, Data: {} }).eventKind).toBe(expected);
  });
});

// ---------- GHL tags ----------

describe("buildTagsFor", () => {
  it("inclui platform, ev, produto, pgto, source:test, utm", () => {
    const adapter = getAdapter("lastlink")!;
    const ev = adapter.normalize({
      Event: "Subscription_Renewal_Pending",
      IsTest: true,
      Data: {
        Products: [{ Name: "Claude Code do Zero ao Avançado" }],
        Buyer: {},
        Purchase: { Payment: { PaymentMethod: "pix" }, Price: { Value: 100 } },
        Utm: { UtmSource: "instagram" },
      },
    });
    const tags = buildTagsFor(ev);
    expect(tags).toContain("platform:lastlink");
    expect(tags).toContain("ev:pix");
    expect(tags).toContain("source:test");
    expect(tags).toContain("pgto:pix");
    expect(tags).toContain("utm:instagram");
    expect(tags.some((t) => t.startsWith("produto:"))).toBe(true);
  });

  it("Purchase_Request_Expired (pix) → tag pix_expirado", () => {
    const adapter = getAdapter("lastlink")!;
    const ev = adapter.normalize({
      Event: "Purchase_Request_Expired",
      Data: { Purchase: { Payment: { PaymentMethod: "pix" } }, Buyer: {} },
    });
    const tags = buildTagsFor(ev);
    expect(tags).toContain("ev:pix");
    expect(tags).toContain("pix_expirado");
  });

  it("Purchase_Request_Expired (bankslip) → tag boleto_expirado", () => {
    const adapter = getAdapter("lastlink")!;
    const ev = adapter.normalize({
      Event: "Purchase_Request_Expired",
      Data: { Purchase: { Payment: { PaymentMethod: "bankslip" } }, Buyer: {} },
    });
    expect(buildTagsFor(ev)).toContain("boleto_expirado");
  });

  it("Purchase_Request_Canceled → tag pedido_cancelado", () => {
    const adapter = getAdapter("lastlink")!;
    const ev = adapter.normalize({ Event: "Purchase_Request_Canceled", Data: { Buyer: {} } });
    expect(buildTagsFor(ev)).toContain("pedido_cancelado");
  });

  it("Payment_Refund → tag refund_solicitado", () => {
    const adapter = getAdapter("lastlink")!;
    const ev = adapter.normalize({ Event: "Payment_Refund", Data: { Buyer: {} } });
    expect(buildTagsFor(ev)).toContain("refund_solicitado");
  });

  it("Purchase_Refused → tag pagamento_recusado", () => {
    const adapter = getAdapter("lastlink")!;
    const ev = adapter.normalize({ Event: "Purchase_Refused", Data: { Buyer: {} } });
    expect(buildTagsFor(ev)).toContain("pagamento_recusado");
  });
});

// ---------- Registry ----------

describe("Registry", () => {
  it("expõe 4 plataformas", () => {
    expect(listPlatforms()).toEqual(["hotmart", "kiwify", "lastlink", "shopify"]);
  });
});
