import { describe, expect, it } from "vitest";
import { getAdapter, listPlatforms } from "../adapters";
import { hmacSha1Hex, hmacSha256Base64, hmacSha256Hex } from "../crypto";

const enc = (s: string) => s;

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

  it("valida assinatura HMAC-SHA1 em query", async () => {
    const sig = await hmacSha1Hex("sec", raw);
    expect(
      await adapter.validateSignature(raw, buildHeaders({}), buildQuery({ signature: sig }), "sec")
    ).toBe(true);
  });

  it("rejeita assinatura inválida", async () => {
    expect(
      await adapter.validateSignature(raw, buildHeaders({}), buildQuery({ signature: "x" }), "sec")
    ).toBe(false);
  });

  it("aceita sem secret (modo dev)", async () => {
    expect(
      await adapter.validateSignature(raw, buildHeaders({}), buildQuery({}), "")
    ).toBe(true);
  });

  it("normaliza pix_created → pix", () => {
    const ev = adapter.normalize(payload);
    expect(ev.platform).toBe("kiwify");
    expect(ev.eventKind).toBe("pix");
    expect(ev.customer.firstName).toBe("João");
    expect(ev.customer.phone).toBe("5511987654321");
    expect(ev.product.valueCents).toBe(19700);
    expect(ev.payment.pixCode).toBe("00020126...");
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

  it("valida Hottok header", async () => {
    expect(
      await adapter.validateSignature("", buildHeaders({ "x-hotmart-hottok": "tok" }), buildQuery({}), "tok")
    ).toBe(true);
    expect(
      await adapter.validateSignature("", buildHeaders({ "x-hotmart-hottok": "x" }), buildQuery({}), "tok")
    ).toBe(false);
  });

  it("normaliza PURCHASE_APPROVED → compra_aprovada", () => {
    const ev = adapter.normalize(payload);
    expect(ev.platform).toBe("hotmart");
    expect(ev.eventKind).toBe("compra_aprovada");
    expect(ev.customer.firstName).toBe("Maria");
    expect(ev.customer.phone).toBe("5511999998888");
    expect(ev.product.valueCents).toBe(29700);
  });

  it("distingue PIX vs BILLET via payment.type", () => {
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
      await adapter.validateSignature(raw, buildHeaders({ "x-shopify-hmac-sha256": "deadbeef" }), buildQuery({}), "sec")
    ).toBe(false);
  });

  it("normaliza orders/paid → compra_aprovada", () => {
    const ev = adapter.normalize(payload);
    expect(ev.eventKind).toBe("compra_aprovada");
    expect(ev.customer.firstName).toBe("Carlos");
    expect(ev.customer.phone).toBe("5511999998888");
    expect(ev.product.valueCents).toBe(39700);
  });

  it("checkouts/create + abandoned → carrinho", () => {
    const p: any = { _topic: "checkouts/create", abandoned_checkout_url: "https://shop/abc" };
    expect(adapter.normalize(p).eventKind).toBe("carrinho");
  });
});

// ---------- Lastlink ----------

describe("Lastlink adapter", () => {
  const adapter = getAdapter("lastlink")!;
  const payload = {
    Id: "evt_1",
    Event: "Purchase_Request_Confirmed",
    Data: {
      Buyer: { Name: "Carla Mendes", Email: "c@x.com", PhoneNumber: "11966665555" },
      Products: [{ Id: "p_xyz", Name: "Curso Pro" }],
      Payment: { Method: "Pix", Amount: 497.0, PixCode: "00020126LL" },
    },
  };
  const raw = JSON.stringify(payload);

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

  it("normaliza Purchase_Request_Confirmed (PIX) → pix", () => {
    const ev = adapter.normalize(payload);
    expect(ev.eventKind).toBe("pix");
    expect(ev.customer.firstName).toBe("Carla");
    expect(ev.customer.phone).toBe("5511966665555");
    expect(ev.product.valueCents).toBe(49700);
    expect(ev.payment.pixCode).toBe("00020126LL");
  });

  it("Purchase_Order_Confirmed → compra_aprovada", () => {
    const p: any = { Event: "Purchase_Order_Confirmed", Data: { Payment: { Method: "CreditCard" } } };
    expect(adapter.normalize(p).eventKind).toBe("compra_aprovada");
  });
});

// ---------- Registry ----------

describe("Registry", () => {
  it("expõe 4 plataformas built-in", () => {
    const plats = listPlatforms();
    expect(plats).toEqual(["hotmart", "kiwify", "lastlink", "shopify"]);
  });
});
