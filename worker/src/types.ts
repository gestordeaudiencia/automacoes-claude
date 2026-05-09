/**
 * Schema unificado que todos os adapters cospem.
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

export interface Address {
  zipCode?: string;
  street?: string;
  streetNumber?: string;
  complement?: string;
  district?: string;
  city?: string;
  state?: string;
  country?: string;
}

export interface Customer {
  name: string;
  firstName: string;
  email: string;
  phone: string; // somente dígitos com DDI 55
  document?: string; // CPF/CNPJ quando disponível
  address?: Address;
}

export interface Product {
  name: string;
  id: string;
  valueCents: number;
}

export interface Payment {
  pixCode?: string;
  pixQrUrl?: string;
  pixExpiration?: string;
  boletoUrl?: string;          // URL pra abrir boleto (alguns providers)
  boletoBarcode?: string;       // linha digitável formatada (humano)
  boletoBarcodeRaw?: string;    // código de barras numérico puro
  boletoBarcodeImage?: string;  // URL da imagem do código de barras
  boletoExpiry?: string;
  accessUrl?: string;
  invoiceUrl?: string;
  rejectionReason?: string;
  method?: string;
  installments?: number;
  paymentId?: string;
  paymentDate?: string;
}

export interface Tracking {
  utmSource?: string;
  utmMedium?: string;
  utmCampaign?: string;
  utmTerm?: string;
  utmContent?: string;
  src?: string;
  sck?: string;
  vtid?: string;
  affiliateId?: string;
  affiliateEmail?: string;
}

export interface SubscriptionInfo {
  id?: string;
  recurrency?: number; // 1 = primeira cobrança, 2 = primeira renovação, etc
  status?: string;
  nextBilling?: string;
  canceledDate?: string;
  expiredDate?: string;
  cancellationReason?: string;
  chargebackDate?: string;
}

export interface NormalizedEvent {
  platform: string;
  eventKind: EventKind;
  rawEventType: string;
  isTest: boolean;
  customer: Customer;
  product: Product;
  payment: Payment;
  tracking?: Tracking;
  subscription?: SubscriptionInfo;
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
