import { createClient } from "@/lib/supabase/client";

export type TenantOption = {
  tenantType: "user" | "group" | "room";
  tenantId: string;
  displayName?: string | null;
};

export async function fetchLineUserId(): Promise<string | null> {
  const supabase = createClient();
  const { data } = await supabase
    .from("line_auth_identities")
    .select("line_user_id")
    .maybeSingle();
  return data?.line_user_id ?? null;
}

type SharedTenantRow = {
  tenant_type: string;
  tenant_id: string;
  last_seen_at: string;
  tenant_chats: { display_name: string | null } | { display_name: string | null }[] | null;
};

export async function fetchSharedTenants(): Promise<TenantOption[]> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from("tenant_chat_members")
    .select("tenant_type, tenant_id, last_seen_at, tenant_chats(display_name)")
    .order("last_seen_at", { ascending: false });

  if (error || !data) {
    return [];
  }

  return (data as SharedTenantRow[]).map((row) => {
    const chatMeta = row.tenant_chats;
    const displayName = Array.isArray(chatMeta)
      ? chatMeta[0]?.display_name
      : chatMeta?.display_name;

    return {
      tenantType: row.tenant_type as TenantOption["tenantType"],
      tenantId: row.tenant_id,
      displayName: displayName ?? null,
    };
  });
}

export async function fetchUserLocale(): Promise<string | null> {
  const supabase = createClient();
  const { data } = await supabase
    .from("user_language_preferences")
    .select("reply_language")
    .maybeSingle();
  return data?.reply_language ?? null;
}
