import { describe, expect, it } from "vitest";
import {
  computeFirstRunDate,
  computeNextRunDate,
} from "@/lib/periodic/recurrence";

describe("interval_days", () => {
  it("runs every 20 days from start", () => {
    const rule = { kind: "interval_days" as const, interval: 20 };
    expect(computeFirstRunDate(rule, "2026-06-01", "Asia/Tokyo")).toBe(
      "2026-06-01",
    );
    expect(
      computeNextRunDate(rule, "2026-06-01", "2026-06-01"),
    ).toBe("2026-06-21");
  });
});

describe("monthly_days", () => {
  it("handles 1st and 15th", () => {
    const rule = { kind: "monthly_days" as const, days: [1, 15] };
    expect(computeFirstRunDate(rule, "2026-06-10", "Asia/Tokyo")).toBe(
      "2026-06-15",
    );
    expect(
      computeNextRunDate(rule, "2026-06-10", "2026-06-15"),
    ).toBe("2026-07-01");
  });

  it("uses last day when day 31 missing in February", () => {
    const rule = { kind: "monthly_days" as const, days: [31] };
    expect(computeFirstRunDate(rule, "2026-01-31", "Asia/Tokyo")).toBe(
      "2026-01-31",
    );
    expect(
      computeNextRunDate(rule, "2026-01-31", "2026-01-31"),
    ).toBe("2026-02-28");
  });
});

describe("monthly_boundary", () => {
  it("first and last of month", () => {
    const first = { kind: "monthly_boundary" as const, boundary: "first" as const };
    expect(computeFirstRunDate(first, "2026-06-15", "Asia/Tokyo")).toBe(
      "2026-07-01",
    );

    const last = { kind: "monthly_boundary" as const, boundary: "last" as const };
    expect(computeFirstRunDate(last, "2026-06-15", "Asia/Tokyo")).toBe(
      "2026-06-30",
    );
  });
});

describe("every_n_months", () => {
  it("every 3 months on 10th from January", () => {
    const rule = { kind: "every_n_months" as const, interval: 3, day: 10 };
    expect(computeFirstRunDate(rule, "2026-01-05", "Asia/Tokyo")).toBe(
      "2026-01-10",
    );
    expect(
      computeNextRunDate(rule, "2026-01-05", "2026-01-10"),
    ).toBe("2026-04-10");
  });
});

describe("every_n_weeks", () => {
  it("every 3 weeks on Wednesday", () => {
    const rule = { kind: "every_n_weeks" as const, interval: 3, weekdays: [3] };
    const start = "2026-06-10"; // Wed
    const first = computeFirstRunDate(rule, start, "Asia/Tokyo");
    expect(first).toBe("2026-06-10");
    const second = computeNextRunDate(rule, start, first);
    expect(second).toBe("2026-07-01");
  });
});
