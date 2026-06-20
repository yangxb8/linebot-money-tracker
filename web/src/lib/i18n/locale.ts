import type { Locale } from "@/lib/i18n/messages";

export function normalizeLocale(value: string | null | undefined): Locale {
  if (value === "en" || value === "zh" || value === "ja") {
    return value;
  }
  return "ja";
}

export function shortTenantId(tenantId: string): string {
  if (tenantId.length <= 6) return tenantId;
  return tenantId.slice(-6);
}
