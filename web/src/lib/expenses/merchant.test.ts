import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  isGenericMerchantText,
  normalizeMerchantKey,
  parseMerchantAliases,
  resolveMerchantDisplay,
  stripBranchSuffix,
} from "@/lib/expenses/merchant";

const bundledAliasPath = join(process.cwd(), "src/data/merchant_aliases_ja.yaml");
const aliases = parseMerchantAliases(readFileSync(bundledAliasPath, "utf8"));

describe("merchant display", () => {
  it("ships bundled alias data for production deploys", () => {
    expect(existsSync(bundledAliasPath)).toBe(true);
  });
  it("strips branch suffixes", () => {
    expect(stripBranchSuffix("スターバックス 渋谷店")).toBe("スターバックス");
  });

  it("rejects generic merchant text", () => {
    expect(isGenericMerchantText("食費")).toBe(true);
    expect(isGenericMerchantText("スターバックス")).toBe(false);
  });

  it("normalizes known aliases", () => {
    expect(normalizeMerchantKey("セブン-イレブン", aliases)).toBe("seven_eleven");
  });

  it("returns persisted merchant display", () => {
    expect(
      resolveMerchantDisplay(
        {
          merchant_key: "starbucks",
          display_merchant: "スターバックス",
        },
        "ラテ",
        aliases,
      ),
    ).toBe("スターバックス");
  });

  it("derives merchant display from store_name metadata", () => {
    expect(
      resolveMerchantDisplay(
        { store_name: "イオン 〇〇店" },
        "牛乳",
        aliases,
      ),
    ).toBe("イオン");
  });

  it("returns null when no specific merchant is available", () => {
    expect(resolveMerchantDisplay({}, "食費", aliases)).toBeNull();
    expect(resolveMerchantDisplay({ store_name: "食費" }, "食費", aliases)).toBeNull();
  });
});
