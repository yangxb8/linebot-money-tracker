import { describe, expect, it } from "vitest";
import type { BudgetCategoryNode } from "@/lib/budget/types";
import {
  buildL1SpendSlices,
  buildTopMerchants,
  dailyRemainingAllowance,
  selectAttentionL1Categories,
  selectUpcomingPeriodics,
  shouldShowUnbudgeted,
} from "@/lib/dashboard/overview";
import type { PeriodicScheduleResponse } from "@/lib/periodic/types";

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

function schedule(
  partial: Partial<PeriodicScheduleResponse> &
    Pick<PeriodicScheduleResponse, "id" | "name" | "amount" | "next_run_date">,
): PeriodicScheduleResponse {
  return {
    tenant_type: "user",
    tenant_id: "u1",
    currency: "JPY",
    assigned_level: 1,
    category_node_id: "c1",
    category_l1_id: "c1",
    category_l2_id: null,
    recurrence: { kind: "interval_days", interval: 7 },
    start_date: "2026-06-01",
    timezone: "Asia/Tokyo",
    end_kind: "never",
    end_date: null,
    end_amount_cap: null,
    end_repeat_limit: null,
    status: "active",
    pause_reason: null,
    occurrence_count: 0,
    cumulative_amount: 0,
    created_by_line_user_id: "u1",
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
    recurrence_summary: "every 7 days",
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

describe("dailyRemainingAllowance", () => {
  it("returns null without remaining or days", () => {
    expect(dailyRemainingAllowance(null, 10)).toBeNull();
    expect(dailyRemainingAllowance(3000, 0)).toBeNull();
  });

  it("floors remaining across days left", () => {
    expect(dailyRemainingAllowance(10000, 3)).toBe(3333);
  });
});

describe("shouldShowUnbudgeted", () => {
  it("requires a configured budget and positive spend", () => {
    expect(shouldShowUnbudgeted(500, true)).toBe(true);
    expect(shouldShowUnbudgeted(0, true)).toBe(false);
    expect(shouldShowUnbudgeted(500, false)).toBe(false);
  });
});

describe("buildTopMerchants", () => {
  it("aggregates by merchant label and ranks by amount", () => {
    const top = buildTopMerchants(
      [
        { merchant_display: "セブン", amount: 500 },
        { merchant_display: null, amount: 9999 },
        { merchant_display: "セブン", amount: 300 },
        { merchant_display: "スタバ", amount: 1200 },
      ],
      { limit: 5 },
    );
    expect(top.map((row) => row.label)).toEqual(["スタバ", "セブン"]);
    expect(top[1]).toMatchObject({ amount: 800, count: 2 });
  });
});

describe("selectUpcomingPeriodics", () => {
  it("expands remaining runs inside the fiscal period", () => {
    const items = selectUpcomingPeriodics(
      [
        schedule({
          id: "netflix",
          name: "Netflix",
          amount: 1500,
          next_run_date: "2026-06-10",
          recurrence: { kind: "interval_days", interval: 7 },
          start_date: "2026-06-03",
        }),
        schedule({
          id: "paused",
          name: "Paused",
          amount: 100,
          next_run_date: "2026-06-12",
          status: "paused",
        }),
        schedule({
          id: "later",
          name: "Later",
          amount: 200,
          next_run_date: "2026-07-05",
        }),
      ],
      { periodEnd: "2026-06-30", fromDate: "2026-06-10" },
    );
    expect(items).toHaveLength(1);
    expect(items[0]?.id).toBe("netflix");
    expect(items[0]?.dates[0]).toBe("2026-06-10");
    expect(items[0]?.dates.at(-1)).toBe("2026-06-24");
  });
});
