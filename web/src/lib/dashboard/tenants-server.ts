import { createClient } from "@/lib/supabase/server";

export async function fetchUserLocaleServer(): Promise<string | null> {
  const supabase = await createClient();
  const { data } = await supabase
    .from("user_language_preferences")
    .select("reply_language")
    .maybeSingle();
  return data?.reply_language ?? null;
}
