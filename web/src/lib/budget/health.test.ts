import { describe, expect, it } from "vitest";
import { computeBudgetHealth } from "@/lib/budget/health";

describe("computeBudgetHealth", () => {
  it("returns neutral when no limit", () => {
    const h = computeBudgetHealth(5000, null, 10, 30);
    expect(h.tone).toBe("neutral");
    expect(h.spentPct).toBeNull();
  });

  it("returns good on day 1 when spend is within one-day allotment", () => {
    const h = computeBudgetHealth(1000, 50000, 1, 30);
    expect(h.tone).toBe("good");
    expect(h.labelKey).toBe("budgetPaceOnTrack");
    expect(h.paceRatio).not.toBeNull();
    expect(h.timePct).toBeCloseTo(1 / 30);
  });

  it("returns bad on day 1 when front-loaded spend exceeds pace", () => {
    // Fixed costs often post on fiscal start day (e.g. 94% of category budget).
    const h = computeBudgetHealth(169516, 180000, 1, 31);
    expect(h.tone).toBe("bad");
    expect(h.labelKey).toBe("budgetPaceOver");
    expect(h.paceRatio).toBeGreaterThan(1.25);
  });

  it("returns neutral before the period starts", () => {
    const h = computeBudgetHealth(5000, 50000, 0, 30);
    expect(h.tone).toBe("neutral");
    expect(h.paceRatio).toBeNull();
  });

  it("returns good when under pace", () => {
    const h = computeBudgetHealth(10000, 50000, 15, 30);
    expect(h.tone).toBe("good");
    expect(h.labelKey).toBe("budgetPaceOnTrack");
  });

  it("returns bad when far over pace", () => {
    const h = computeBudgetHealth(35000, 50000, 7, 30);
    expect(h.tone).toBe("bad");
    expect(h.labelKey).toBe("budgetPaceOver");
  });

  it("handles over 100% spent", () => {
    const h = computeBudgetHealth(60000, 50000, 20, 30);
    expect(h.spentPct).toBeGreaterThan(1);
    expect(h.tone).toBe("bad");
  });
});
