export type ExpenseMetadata = {
  store_name?: string;
  merchant_key?: string;
  display_merchant?: string;
};

const GENERIC_DENYLIST = new Set([
  "expense",
  "payment",
  "misc",
  "unknown",
  "不明",
  "食費",
  "買い物",
  "支出",
  "支払",
  "支払い",
  "shopping",
  "grocery",
  "food",
  "lunch",
  "dinner",
  "transport",
]);

const BRANCH_SUFFIX_RE =
  /(?:\s+|\(|\[|（|【)(?:[\d０-９]+号店|[\p{L}\p{N}_\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f]{1,12}(?:店|支店|駅前店|駅店)|駅前|本店|支店)(?:\)|\]|\)|）|】)?\s*$/iu;

export type MerchantAliasMap = Record<string, string[]>;

export function parseMerchantAliases(yaml: string): MerchantAliasMap {
  const result: MerchantAliasMap = {};
  let currentKey: string | null = null;

  for (const line of yaml.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    if (trimmed.endsWith(":") && !trimmed.startsWith("-")) {
      currentKey = trimmed.slice(0, -1);
      result[currentKey] = [];
      continue;
    }
    if (trimmed.startsWith("- ") && currentKey) {
      result[currentKey].push(trimmed.slice(2));
    }
  }

  return result;
}

function nfkc(text: string): string {
  return text.normalize("NFKC").trim();
}

function asciiKey(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function isGenericMerchantText(text: string): boolean {
  const normalized = nfkc(text).toLowerCase();
  if (!normalized || normalized.length < 2) return true;
  if (GENERIC_DENYLIST.has(normalized)) return true;
  const compact = normalized.replace(/\s+/g, "");
  return GENERIC_DENYLIST.has(compact);
}

export function stripBranchSuffix(text: string): string {
  let cleaned = nfkc(text);
  let previous: string | null = null;
  while (cleaned && cleaned !== previous) {
    previous = cleaned;
    cleaned = cleaned.replace(BRANCH_SUFFIX_RE, "").trim().replace(/[ -@:，、.]+$/u, "");
  }
  return cleaned;
}

function buildVariantToKey(aliases: MerchantAliasMap): Map<string, string> {
  const variantToKey = new Map<string, string>();
  for (const [merchantKey, variants] of Object.entries(aliases)) {
    const key = merchantKey.trim().toLowerCase();
    if (!key) continue;
    variantToKey.set(nfkc(key).toLowerCase(), key);
    for (const variant of variants ?? []) {
      const normalized = nfkc(String(variant)).toLowerCase();
      if (normalized) variantToKey.set(normalized, key);
    }
  }
  return variantToKey;
}

function matchAlias(text: string, variantToKey: Map<string, string>): string | null {
  const normalized = nfkc(text).toLowerCase();
  if (!normalized) return null;
  const direct = variantToKey.get(normalized);
  if (direct) return direct;

  const compact = normalized.replace(/[\s\-・.]+/g, "");
  for (const [variant, key] of variantToKey.entries()) {
    const variantCompact = variant.replace(/[\s\-・.]+/g, "");
    if (!variantCompact) continue;
    if (
      variantCompact.includes(compact) ||
      compact.includes(variantCompact)
    ) {
      if (variantCompact.length >= 3 || compact.length >= 3) return key;
    }
  }
  return null;
}

export function normalizeMerchantKey(
  rawMerchant: string | null | undefined,
  aliases: MerchantAliasMap,
): string | null {
  if (rawMerchant == null) return null;

  const stripped = stripBranchSuffix(String(rawMerchant));
  if (isGenericMerchantText(stripped)) return null;

  const variantToKey = buildVariantToKey(aliases);
  const aliasKey = matchAlias(stripped, variantToKey);
  if (aliasKey) return aliasKey;

  const key = asciiKey(stripped);
  if (!key || key.length < 2) return null;
  if (isGenericMerchantText(key)) return null;
  return key;
}

function displayLabelForKey(
  merchantKey: string,
  aliases: MerchantAliasMap,
  fallback?: string | null,
): string | null {
  const trimmedFallback = fallback?.trim();
  if (trimmedFallback && !isGenericMerchantText(trimmedFallback)) {
    return trimmedFallback;
  }

  const variants = aliases[merchantKey] ?? [];
  const preferred = variants.find((variant) => /[\u3040-\u9fff]/u.test(variant));
  if (preferred) return preferred;
  if (variants[0]) return variants[0];
  return merchantKey.replace(/_/g, " ");
}

function metadataObject(metadata: unknown): ExpenseMetadata {
  if (!metadata || typeof metadata !== "object") return {};
  return metadata as ExpenseMetadata;
}

export function resolveMerchantDisplay(
  metadata: unknown,
  description: string,
  aliases: MerchantAliasMap,
): string | null {
  const md = metadataObject(metadata);
  const merchantKey = md.merchant_key?.trim();
  const displayMerchant = md.display_merchant?.trim();

  if (merchantKey) {
    const label = displayLabelForKey(merchantKey, aliases, displayMerchant);
    return label && !isGenericMerchantText(label) ? label : null;
  }

  const storeName = md.store_name?.trim();
  if (storeName) {
    const stripped = stripBranchSuffix(storeName);
    const key = normalizeMerchantKey(stripped, aliases);
    if (key) {
      return displayLabelForKey(key, aliases, stripped);
    }
  }

  const cleanedDescription = stripBranchSuffix(description.split("|")[0]?.split("/")[0] ?? "");
  const descriptionKey = normalizeMerchantKey(cleanedDescription, aliases);
  if (descriptionKey) {
    return displayLabelForKey(descriptionKey, aliases, cleanedDescription);
  }

  return null;
}
