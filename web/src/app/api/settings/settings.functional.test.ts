/**
 * web.api.settings_bot_behavior
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const store = {
  fiscal_start_day: 1,
  bot_persona_preset: "default",
  bot_persona_custom_text: null as string | null,
  bot_persona_emoji_level: 1 as number | null,
  confirmation_show_item_details: true,
  reply_language: "en" as string | null,
};

const fetchTenantSettings = vi.fn(async () => ({ ...store }));
const upsertTenantSettings = vi.fn(
  async (_t: string, _id: string, patch: Record<string, unknown>) => {
    Object.assign(store, patch);
    return { ...store };
  },
);
const parseTenantParams = vi.fn((tenantType: string | null, tenantId: string | null) => {
  if (!tenantType || !tenantId) {
    throw new Response("tenant_type and tenant_id required", { status: 400 });
  }
  return { tenantType, tenantId };
});

vi.mock("@/lib/settings/server", () => ({
  fetchTenantSettings: (...args: unknown[]) => fetchTenantSettings(...args),
  upsertTenantSettings: (...args: unknown[]) => upsertTenantSettings(...args),
  parseTenantParams: (a: string | null, b: string | null) => parseTenantParams(a, b),
}));

import { GET, PUT } from "@/app/api/settings/route";

describe("settings API functional", () => {
  beforeEach(() => {
    store.bot_persona_preset = "default";
    store.reply_language = "en";
    fetchTenantSettings.mockClear();
    upsertTenantSettings.mockClear();
  });

  it("web.api.settings_bot_behavior — save then reload", async () => {
    const putRes = await PUT(
      new Request("http://localhost/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant_type: "user",
          tenant_id: "U1",
          fiscal_start_day: 1,
          bot_persona_preset: "genki",
          bot_persona_custom_text: null,
          bot_persona_emoji_level: 2,
          confirmation_show_item_details: true,
          reply_language: "ja",
        }),
      }),
    );
    expect(putRes.status).toBe(200);
    const saved = await putRes.json();
    expect(saved.bot_persona_preset).toBe("genki");
    expect(saved.reply_language).toBe("ja");

    const getRes = await GET(
      new Request("http://localhost/api/settings?tenant_type=user&tenant_id=U1"),
    );
    expect(getRes.status).toBe(200);
    const loaded = await getRes.json();
    expect(loaded.bot_persona_preset).toBe("genki");
    expect(loaded.reply_language).toBe("ja");
  });
});
