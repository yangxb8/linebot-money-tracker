/**
 * web.api.categories
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

type Row = {
  id: string;
  name_ja: string;
  level: number;
  parent_id: string | null;
  code: string;
  sort_order: number;
  pace_warning_enabled?: boolean;
  expense_count?: number;
  deletable?: boolean;
};

const nodes: Row[] = [
  {
    id: "cat-1",
    name_ja: "食費",
    level: 1,
    parent_id: null,
    code: "food",
    sort_order: 0,
    pace_warning_enabled: false,
    expense_count: 0,
    deletable: true,
  },
];

function chainable(terminal: unknown = { data: [], error: null }) {
  const handler: ProxyHandler<object> = {
    get(_target, prop) {
      if (prop === "then") {
        return (resolve: (v: unknown) => unknown) =>
          Promise.resolve(terminal).then(resolve);
      }
      return () => new Proxy({}, handler);
    },
  };
  return new Proxy({}, handler);
}

const requireUser = vi.fn(async () => ({
  from: () => chainable({ data: nodes, error: null }),
}));

const ensureTenantTaxonomy = vi.fn(async () => ({
  from: (table: string) => {
    if (table !== "category_nodes") return chainable();
    return {
      select: () => chainable({ data: [{ sort_order: 0 }], error: null }),
      insert: () => ({
        select: () => ({
          single: async () => ({
            data: {
              id: "cat-new",
              code: "custom_test",
              name_ja: "テスト",
              level: 1,
              parent_id: null,
              sort_order: 1,
              pace_warning_enabled: false,
            },
            error: null,
          }),
        }),
      }),
    };
  },
}));

const loadCategoryNodes = vi.fn(async () => nodes);
const hasCategoryNameConflict = vi.fn(async () => false);
const generateCustomCode = vi.fn(() => "custom_test");
const assertTenantL1Parent = vi.fn(async () => undefined);

vi.mock("@/lib/categories/server", () => ({
  requireUser: (...args: unknown[]) => requireUser(...args),
  ensureTenantTaxonomy: (...args: unknown[]) => ensureTenantTaxonomy(...args),
  loadCategoryNodes: (...args: unknown[]) => loadCategoryNodes(...args),
  hasCategoryNameConflict: (...args: unknown[]) => hasCategoryNameConflict(...args),
  generateCustomCode: (...args: unknown[]) => generateCustomCode(...args),
  assertTenantL1Parent: (...args: unknown[]) => assertTenantL1Parent(...args),
}));

import { GET, POST } from "@/app/api/categories/route";
import { PATCH } from "@/app/api/categories/[id]/route";

describe("categories API functional", () => {
  beforeEach(() => {
    loadCategoryNodes.mockResolvedValue([...nodes]);
    hasCategoryNameConflict.mockResolvedValue(false);
    requireUser.mockImplementation(async () => ({
      from: () => chainable({ data: nodes, error: null }),
    }));
  });

  it("web.api.categories — create then read reflects item", async () => {
    const postRes = await POST(
      new Request("http://localhost/api/categories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant_type: "user",
          tenant_id: "U1",
          level: 1,
          name_ja: "テスト",
        }),
      }),
    );
    expect(postRes.status).toBe(201);
    const created = await postRes.json();
    expect(created.name_ja).toBe("テスト");
    expect(created.pace_warning_enabled).toBe(false);

    loadCategoryNodes.mockResolvedValue([
      ...nodes,
      {
        id: "cat-new",
        name_ja: "テスト",
        level: 1,
        parent_id: null,
        code: "custom_test",
        sort_order: 1,
        pace_warning_enabled: false,
        expense_count: 0,
        deletable: true,
      },
    ]);

    const getRes = await GET(
      new Request("http://localhost/api/categories?tenant_type=user&tenant_id=U1"),
    );
    expect(getRes.status).toBe(200);
    const body = await getRes.json();
    expect(body.nodes.some((n: { name_ja: string }) => n.name_ja === "テスト")).toBe(
      true,
    );
  });

  it("web.api.categories — patch enables pace warning", async () => {
    requireUser.mockImplementation(async () => ({
      from: () => ({
        update: () => ({
          eq: () => ({
            select: () => ({
              single: async () => ({
                data: {
                  id: "cat-1",
                  code: "food",
                  name_ja: "食費",
                  level: 1,
                  parent_id: null,
                  sort_order: 0,
                  pace_warning_enabled: true,
                },
                error: null,
              }),
            }),
          }),
        }),
      }),
    }));

    const res = await PATCH(
      new Request("http://localhost/api/categories/cat-1", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pace_warning_enabled: true }),
      }),
      { params: Promise.resolve({ id: "cat-1" }) },
    );
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.pace_warning_enabled).toBe(true);
  });
});
