/**
 * Schema unificado que todos os adapters cospem.
 * Equivalente ao NormalizedEvent do Python.
 */

export type EventKind =
  | "pix"
  | "boleto"
  | "compra_aprovada"
  | "recusada"
  | "carrinho"
  | "cancelada"
  | "renovacao"
  | "outro";

export interface Customer {
  name: string;
  firstName: string;
  email: string;
  phone: string; // somente dígitos com DDI 55
}

export interface Product {
  name: string;
  id: string;
  valueCents: number;
}

export interface Payment {
  pixCode?: string;
  pixExpiration?: string;
  boletoUrl?: string;
  boletoBarcode?: string;
  boletoExpiry?: string;
  accessUrl?: string;
  rejectionReason?: string;
  method?: string;
}

export interface NormalizedEvent {
  platform: string;
  eventKind: EventKind;
  rawEventType: string;
  customer: Customer;
  product: Product;
  payment: Payment;
  rawPayload: unknown;
}

export interface PlatformAdapter {
  name: string;
  validateSignature(
    rawBody: string,
    headers: Headers,
    query: URLSearchParams,
    secret: string
  ): Promise<boolean>;
  normalize(payload: any): NormalizedEvent;
}

export function valueBrl(cents: number): string {
  return (cents / 100).toFixed(2).replace(".", ",");
}

export function normalizePhoneBr(raw: string | undefined | null): string {
  if (!raw) return "";
  let phone = String(raw).replace(/\D/g, "");
  if (phone.startsWith("0")) phone = phone.slice(1);
  if (phone && !phone.startsWith("55")) phone = "55" + phone;
  return phone;
}

export function firstNameOf(full: string | undefined | null): string {
  return (full || "").trim().split(" ")[0] || "";
}
