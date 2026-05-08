/**
 * Helpers HMAC usando WebCrypto (disponível em Cloudflare Workers).
 */

const enc = new TextEncoder();

async function hmac(
  algo: "SHA-1" | "SHA-256",
  secret: string,
  data: string | Uint8Array
): Promise<ArrayBuffer> {
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: algo },
    false,
    ["sign"]
  );
  const dataBytes = typeof data === "string" ? enc.encode(data) : data;
  return crypto.subtle.sign("HMAC", key, dataBytes);
}

function bufToHex(buf: ArrayBuffer): string {
  return [...new Uint8Array(buf)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function bufToBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let bin = "";
  for (let i = 0; i < bytes.byteLength; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin);
}

export async function hmacSha1Hex(secret: string, data: string): Promise<string> {
  return bufToHex(await hmac("SHA-1", secret, data));
}

export async function hmacSha256Hex(secret: string, data: string): Promise<string> {
  return bufToHex(await hmac("SHA-256", secret, data));
}

export async function hmacSha256Base64(secret: string, data: string): Promise<string> {
  return bufToBase64(await hmac("SHA-256", secret, data));
}

/**
 * Compare de forma constante no tempo. Para strings pequenas (signatures), suficiente.
 */
export function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let mismatch = 0;
  for (let i = 0; i < a.length; i++) {
    mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return mismatch === 0;
}
