import { createClient } from "@/lib/supabase/server";
import {
  assertTenantAccess,
  parseTenantParams,
} from "@/lib/periodic/tenant-access";
import type { TenantSettings } from "@/lib/settings/types";

export { parseTenantParams };

const DEFAULT_SETTINGS: TenantSettings = { fiscal_start_day: 1 };

export async function requireSettingsUser() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    throw new Response("Unauthorized", { status: 401 });
  }
  return supabase;
}

export async function fetchTenantSettings(
  tenantType: string,
  tenantId: string,
): Promise<TenantSettings> {
  const supabase = await requireSettingsUser();
  await assertTenantAccess(supabase, tenantType, tenantId);

  const { data, error } = await supabase
    .from("tenant_settings")
    .select("fiscal_start_day")
    .eq("tenant_type", tenantType)
    .eq("tenant_id", tenantId)
    .maybeSingle();

  if (error) {
    throw new Response(error.message, { status: 400 });
  }

  if (!data) {
    return DEFAULT_SETTINGS;
  }

  return { fiscal_start_day: Number(data.fiscal_start_day) };
}

export async function upsertTenantSettings(
  tenantType: string,
  tenantId: string,
  settings: TenantSettings,
): Promise<TenantSettings> {
  const supabase = await requireSettingsUser();
  await assertTenantAccess(supabase, tenantType, tenantId);

  const fiscalStartDay = settings.fiscal_start_day;
  if (
    !Number.isInteger(fiscalStartDay) ||
    fiscalStartDay < 1 ||
    fiscalStartDay > 28
  ) {
    throw new Response("invalid_fiscal_start_day", { status: 400 });
  }

  const { data, error } = await supabase
    .from("tenant_settings")
    .upsert(
      {
        tenant_type: tenantType,
        tenant_id: tenantId,
        fiscal_start_day: fiscalStartDay,
        updated_at: new Date().toISOString(),
      },
      { onConflict: "tenant_type,tenant_id" },
    )
    .select("fiscal_start_day")
    .single();

  if (error) {
    throw new Response(error.message, { status: 400 });
  }

  return { fiscal_start_day: Number(data.fiscal_start_day) };
}
