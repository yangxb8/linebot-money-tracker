import { describe, expect, it } from "vitest";
import type { BudgetCategoryNode } from "@/lib/budget/types";
import {
  buildL1SpendSlices,
  selectAttentionL1Categories,
} from "@/lib/dashboard/overview";

function l1(
  partial: Partial<BudgetCategoryNode> &
    Pick<BudgetCategoryNode, "node_id" | "name_ja" | "spent_aggregate">,
): BudgetCategoryNode {
  return {
    code: partial.code ?? partial.node_id,
    level: 1,
    limit: partial.limit ?? null,
    spent: partial.spent_aggregate,
    spent_assigned: partial.spent_assigned ?? 0,
    suggested_from_children: null,
    has_limit: partial.has_limit ?? partial.limit != null,
    ...partial,
  };
}

describe("selectAttentionL1Categories", () => {
  it("returns empty when no category has a limit", () => {
    const cats = [
      l1({ node_id: "a", name_ja: "食費", spent_aggregate: 10000 }),
    ];
    expect(selectAttentionL1Categories(cats, 15, 30)).toEqual([]);
  });

  it("skips on-track (green) categories", () => {
    const cats = [
      l1({
        node_id: "a",
        name_ja: "食費",
        spent_aggregate: 10000,
        limit: 50000,
        has_limit: true,
      }),
    ];
    expect(selectAttentionL1Categories(cats, 15, 30)).toEqual([]);
  });

  it("includes caution and bad categories, bad first", () => {
    const cats = [
      l1({
        node_id: "good",
        name_ja: "Good",
        spent_aggregate: 10000,
        limit: 50000,
        has_limit: true,
      }),
      l1({
        node_id: "caution",
        name_ja: "Caution",
        spent_aggregate: 28000,
        limit: 50000,
        has_limit: true,
      }),
      l1({
        node_id: "bad",
        name_ja: "Bad",
        spent_aggregate: 35000,
        limit: 50000,
        has_limit: true,
      }),
    ];
    const result = selectAttentionL1Categories(cats, 15, 30);
    expect(result.map((c) => c.node_id)).toEqual(["bad", "caution"]);
  });
});

describe("buildL1SpendSlices", () => {
  it("returns empty when all amounts are zero", () => {
    const cats = [
      l1({ node_id: "a", name_ja: "食費", spent_aggregate: 0 }),
    ];
    expect(buildL1SpendSlices(cats)).toEqual([]);
  });

  it("computes percentages sorted by amount desc", () => {
    const cats = [
      l1({ node_id: "a", name_ja: "食費", spent_aggregate: 3000 }),
      l1({ node_id: "b", name_ja: "交通", spent_aggregate: 7000 }),
      l1({ node_id: "c", name_ja: "ゼロ", spent_aggregate: 0 }),
    ];
    const slices = buildL1SpendSlices(cats);
    expect(slices).toHaveLength(2);
    expect(slices[0]).toMatchObject({ id: "b", pct: 0.7 });
    expect(slices[1]).toMatchObject({ id: "a", pct: 0.3 });
  });

  it("collapses excess categories into Other", () => {
    const cats = Array.from({ length: 8 }, (_, i) =>
      l1({
        node_id: `c${i}`,
        name_ja: `Cat ${i}`,
        spent_aggregate: 1000 - i * 10,
      }),
    );
    const slices = buildL1SpendSlices(cats, {
      maxSlices: 4,
      otherLabel: "その他",
    });
    expect(slices).toHaveLength(4);
    expect(slices[3]?.id).toBe("__other__");
    expect(slices[3]?.label).toBe("その他");
    const sumPct = slices.reduce((s, row) => s + row.pct, 0);
    expect(sumPct).toBeCloseTo(1, 5);
  });
});
