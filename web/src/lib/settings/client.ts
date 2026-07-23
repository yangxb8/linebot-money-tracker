import type { TenantOption } from "@/lib/dashboard/tenants";
import type { TenantSettings } from "@/lib/settings/types";

function tenantQuery(tenant: TenantOption): string {
  return `tenant_type=${encodeURIComponent(tenant.tenantType)}&tenant_id=${encodeURIComponent(tenant.tenantId)}`;
}

export async function fetchTenantSettings(
  tenant: TenantOption,
): Promise<TenantSettings> {
  const response = await fetch(`/api/settings?${tenantQuery(tenant)}`);
  if (!response.ok) {
    throw new Error("Failed to load settings");
  }
  return response.json() as Promise<TenantSettings>;
}

export async function saveTenantSettings(
  tenant: TenantOption,
  settings: TenantSettings,
): Promise<TenantSettings> {
  const response = await fetch("/api/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tenant_type: tenant.tenantType,
      tenant_id: tenant.tenantId,
      fiscal_start_day: settings.fiscal_start_day,
      bot_persona_preset: settings.bot_persona_preset ?? null,
      bot_persona_custom_text: settings.bot_persona_custom_text ?? null,
      bot_persona_emoji_level: settings.bot_persona_emoji_level ?? null,
      confirmation_show_item_details: settings.confirmation_show_item_details ?? false,
      reply_language: settings.reply_language ?? null,
    }),
  });
  if (!response.ok) {
    const data = (await response.json().catch(() => ({}))) as {
      error?: string;
    };
    throw new Error(data.error ?? "Failed to save settings");
  }
  return response.json() as Promise<TenantSettings>;
}
