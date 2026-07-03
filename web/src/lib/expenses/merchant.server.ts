import "server-only";

import { readFileSync } from "node:fs";
import { join } from "node:path";

import {
  parseMerchantAliases,
  resolveMerchantDisplay,
  type MerchantAliasMap,
} from "@/lib/expenses/merchant";

let aliasCache: MerchantAliasMap | null = null;

function merchantAliases(): MerchantAliasMap {
  if (!aliasCache) {
    const path = join(process.cwd(), "..", "data", "merchant_aliases_ja.yaml");
    aliasCache = parseMerchantAliases(readFileSync(path, "utf8"));
  }
  return aliasCache;
}

export function resolveExpenseMerchantDisplay(
  metadata: unknown,
  description: string,
): string | null {
  return resolveMerchantDisplay(metadata, description, merchantAliases());
}
