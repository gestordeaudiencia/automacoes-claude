import type { PlatformAdapter } from "../types";
import { HotmartAdapter } from "./hotmart";
import { KiwifyAdapter } from "./kiwify";
import { LastlinkAdapter } from "./lastlink";
import { ShopifyAdapter } from "./shopify";

const adapters: Record<string, PlatformAdapter> = {
  kiwify: KiwifyAdapter,
  hotmart: HotmartAdapter,
  shopify: ShopifyAdapter,
  lastlink: LastlinkAdapter,
};

export function getAdapter(slug: string): PlatformAdapter | null {
  return adapters[slug.toLowerCase()] || null;
}

export function listPlatforms(): string[] {
  return Object.keys(adapters).sort();
}
