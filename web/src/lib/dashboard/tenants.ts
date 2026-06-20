import { createClient } from "@/lib/supabase/client";

export type TenantOption = {
  tenantType: "user" | "group" | "room";
  tenantId: string;
};

export async function fetchLineUserId(): Promise<string | null> {
  const supabase = createClient();
  const { data } = await supabase
    .from("line_auth_identities")
    .select("line_user_id")
    .maybeSingle();
  return data?.line_user_id ?? null;
}

export async function fetchSharedTenants(): Promise<TenantOption[]> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from("tenant_chat_members")
    .select("tenant_type, tenant_id, last_seen_at")
    .order("last_seen_at", { ascending: false });

  if (error || !data) {
    return [];
  }

  return data.map((row) => ({
    tenantType: row.tenant_type as TenantOption["tenantType"],
    tenantId: row.tenant_id,
  }));
}

export async function fetchUserLocale(): Promise<string | null> {
  const supabase = createClient();
  const { data } = await supabase
    .from("user_language_preferences")
    .select("reply_language")
    .maybeSingle();
  return data?.reply_language ?? null;
}
