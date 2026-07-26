import { describe, expect, it } from "vitest";
import {
  isValidProductUrl,
  validateCreatePayload,
  validateReorderPayload,
  validateUpdatePayload,
} from "@/lib/wish-list/validation";

const validCreatePayload = {
  name: "Headphones",
  amount: 15000,
  category_node_id: "category-1",
  product_url: "https://example.com/item",
};

describe("wish-list validation", () => {
  it("accepts a valid create payload", () => {
    expect(validateCreatePayload(validCreatePayload)).toEqual({ ok: true });
  });

  it("requires a non-empty name", () => {
    expect(validateCreatePayload({ ...validCreatePayload, name: " " })).toEqual({
      ok: false,
      error: "name_required",
    });
  });

  it("requires a positive numeric amount", () => {
    expect(validateCreatePayload({ ...validCreatePayload, amount: 0 })).toEqual({
      ok: false,
      error: "invalid_amount",
    });
    expect(validateCreatePayload({ ...validCreatePayload, amount: "abc" })).toEqual({
      ok: false,
      error: "invalid_amount",
    });
  });

  it("requires a category", () => {
    expect(
      validateCreatePayload({ ...validCreatePayload, category_node_id: "" }),
    ).toEqual({
      ok: false,
      error: "category_required",
    });
  });

  it("allows blank, http, and https product URLs only", () => {
    expect(isValidProductUrl("")).toBe(true);
    expect(isValidProductUrl("http://example.com/item")).toBe(true);
    expect(isValidProductUrl("https://example.com/item")).toBe(true);
    expect(isValidProductUrl("ftp://example.com/item")).toBe(false);
    expect(isValidProductUrl("not a url")).toBe(false);
  });

  it("validates product URLs on update", () => {
    expect(validateUpdatePayload({ product_url: "https://example.com" })).toEqual({
      ok: true,
    });
    expect(validateUpdatePayload({ product_url: "ftp://example.com" })).toEqual({
      ok: false,
      error: "invalid_product_url",
    });
  });

  it("requires reorder ordered_ids to be a non-empty array of strings", () => {
    expect(validateReorderPayload({ ordered_ids: ["a", "b"] })).toEqual({
      ok: true,
    });
    expect(validateReorderPayload({ ordered_ids: [] })).toEqual({
      ok: false,
      error: "ordered_ids_required",
    });
    expect(validateReorderPayload({ ordered_ids: ["a", 2] })).toEqual({
      ok: false,
      error: "invalid_ordered_ids",
    });
  });
});
