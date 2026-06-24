import { describe, expect, it } from "vitest";
import {
  currentBudgetMonthJst,
  fiscalPeriodEnd,
  fiscalPeriodStartForDate,
  formatBudgetPeriodLabel,
  isCurrentBudgetMonth,
  shiftBudgetMonth,
} from "@/lib/budget/format";

describe("fiscalPeriodStartForDate", () => {
  it("uses calendar month when fiscal start is 1", () => {
    expect(fiscalPeriodStartForDate(2026, 6, 15, 1)).toBe("2026-06-01");
    expect(fiscalPeriodStartForDate(2026, 6, 1, 1)).toBe("2026-06-01");
  });

  it("rolls back to previous month before fiscal start day", () => {
    expect(fiscalPeriodStartForDate(2026, 6, 24, 25)).toBe("2026-05-25");
    expect(fiscalPeriodStartForDate(2026, 6, 25, 25)).toBe("2026-06-25");
  });
});

describe("fiscalPeriodEnd", () => {
  it("ends the day before the next period starts", () => {
    expect(fiscalPeriodEnd("2026-05-25")).toBe("2026-06-24");
    expect(fiscalPeriodEnd("2026-06-01")).toBe("2026-06-30");
  });
});

describe("shiftBudgetMonth", () => {
  it("shifts fiscal period anchors by whole months", () => {
    expect(shiftBudgetMonth("2026-05-25", 1)).toBe("2026-06-25");
    expect(shiftBudgetMonth("2026-06-01", -1)).toBe("2026-05-01");
  });
});

describe("formatBudgetPeriodLabel", () => {
  it("shows YYYY-MM for calendar months", () => {
    expect(formatBudgetPeriodLabel("2026-06-01", "2026-06-30", 1)).toBe(
      "2026-06",
    );
  });

  it("shows day range for custom fiscal starts", () => {
    expect(formatBudgetPeriodLabel("2026-05-25", "2026-06-24", 25)).toBe(
      "5/25 – 6/24",
    );
  });
});

describe("isCurrentBudgetMonth", () => {
  it("matches the active fiscal period for the configured start day", () => {
    const active = currentBudgetMonthJst(25);
    expect(isCurrentBudgetMonth(active, 25)).toBe(true);
    expect(isCurrentBudgetMonth(shiftBudgetMonth(active, -1), 25)).toBe(false);
  });
});
