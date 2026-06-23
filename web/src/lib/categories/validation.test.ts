import { describe, expect, it } from "vitest";
import { isDuplicateCategoryName } from "@/lib/categories/validation";

describe("isDuplicateCategoryName", () => {
  const nodes = [
    { id: "1", name_ja: "食費" },
    { id: "2", name_ja: "食料品" },
    { id: "3", name_ja: "交通" },
  ];

  it("detects duplicate across levels", () => {
    expect(isDuplicateCategoryName(nodes, "食費")).toBe(true);
    expect(isDuplicateCategoryName(nodes, "交通")).toBe(true);
  });

  it("ignores the excluded node when renaming", () => {
    expect(isDuplicateCategoryName(nodes, "食費", "1")).toBe(false);
  });

  it("trims whitespace before comparing", () => {
    expect(isDuplicateCategoryName(nodes, " 食費 ")).toBe(true);
    expect(isDuplicateCategoryName(nodes, " 新規 ")).toBe(false);
  });
});
