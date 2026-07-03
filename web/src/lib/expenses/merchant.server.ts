import "server-only";

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import {
  parseMerchantAliases,
  resolveMerchantDisplay,
  type MerchantAliasMap,
} from "@/lib/expenses/merchant";

let aliasCache: MerchantAliasMap | null = null;
let aliasLoadAttempted = false;

function merchantAliasPaths(): string[] {
  const cwd = process.cwd();
  return [
    join(cwd, "src/data/merchant_aliases_ja.yaml"),
    join(cwd, "data/merchant_aliases_ja.yaml"),
    join(cwd, "..", "data/merchant_aliases_ja.yaml"),
  ];
}

function merchantAliases(): MerchantAliasMap {
  if (aliasCache) return aliasCache;
  if (aliasLoadAttempted) return {};

  aliasLoadAttempted = true;
  for (const path of merchantAliasPaths()) {
    if (!existsSync(path)) continue;
    aliasCache = parseMerchantAliases(readFileSync(path, "utf8"));
    return aliasCache;
  }

  aliasCache = {};
  return aliasCache;
}

export function resolveExpenseMerchantDisplay(
  metadata: unknown,
  description: string,
): string | null {
  try {
    return resolveMerchantDisplay(metadata, description, merchantAliases());
  } catch {
    return null;
  }
}
