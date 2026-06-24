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
