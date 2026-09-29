import { describe, expect, it } from "vitest";
import {
  computeBudgetHealth,
  computeDisplayBudgetHealth,
  resolveDisplayBudgetHealth,
} from "@/lib/budget/health";

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

describe("resolveDisplayBudgetHealth / computeDisplayBudgetHealth", () => {
  it("suppresses pace-ahead when opt-in is off", () => {
    const raw = computeBudgetHealth(35000, 50000, 7, 30);
    expect(raw.tone).toBe("bad");
    const display = resolveDisplayBudgetHealth(raw, {
      spent: 35000,
      limit: 50000,
      paceWarningEnabled: false,
    });
    expect(display.tone).toBe("good");
    expect(display.labelKey).toBe("budgetPaceOnTrack");
  });

  it("keeps pace-ahead when opt-in is on", () => {
    const display = computeDisplayBudgetHealth(35000, 50000, 7, 30, true);
    expect(display.tone).toBe("bad");
    expect(display.labelKey).toBe("budgetPaceOver");
  });

  it("always keeps overspend alert even when opt-in is off", () => {
    const display = computeDisplayBudgetHealth(60000, 50000, 20, 30, false);
    expect(display.tone).toBe("bad");
    expect(display.spentPct).toBeGreaterThan(1);
  });

  it("treats total (no opt-in) pace-ahead as on-track", () => {
    const display = computeDisplayBudgetHealth(35000, 50000, 7, 30, false);
    expect(display.tone).toBe("good");
  });
});
