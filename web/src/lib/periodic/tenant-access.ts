import type { SupabaseClient } from "@supabase/supabase-js";

export async function assertTenantAccess(
  supabase: SupabaseClient,
  tenantType: string,
  tenantId: string,
): Promise<void> {
  const { data: lineUserId, error: idError } = await supabase.rpc(
    "current_line_user_id",
  );

  if (idError || !lineUserId) {
    throw new Response("Unauthorized", { status: 401 });
  }

  if (tenantType === "user") {
    if (tenantId !== lineUserId) {
      throw new Response("Forbidden", { status: 403 });
    }
    return;
  }

  if (tenantType === "group" || tenantType === "room") {
    const { data: member, error } = await supabase
      .from("tenant_chat_members")
      .select("tenant_id")
      .eq("tenant_type", tenantType)
      .eq("tenant_id", tenantId)
      .eq("line_user_id", lineUserId)
      .maybeSingle();

    if (error || !member) {
      throw new Response("Forbidden", { status: 403 });
    }
    return;
  }

  throw new Response("invalid_tenant", { status: 400 });
}

export function parseTenantParams(
  tenantType: string | null,
  tenantId: string | null,
): { tenantType: string; tenantId: string } {
  if (!tenantType || !tenantId) {
    throw new Response("tenant_type and tenant_id required", { status: 400 });
  }
  if (tenantType !== "user" && tenantType !== "group" && tenantType !== "room") {
    throw new Response("invalid tenant_type", { status: 400 });
  }
  return { tenantType, tenantId };
}
