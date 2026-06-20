import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";
import { lineSyntheticEmail } from "@/lib/line/oauth";
import type { LineProfile } from "@/lib/line/verify-id-token";

async function getOrCreateAuthUserId(
  lineUserId: string,
  profile: LineProfile,
): Promise<string> {
  const admin = createAdminClient();
  const email = lineSyntheticEmail(lineUserId);

  const { data: created, error: createError } =
    await admin.auth.admin.createUser({
      email,
      email_confirm: true,
      user_metadata: {
        line_user_id: lineUserId,
        display_name: profile.name,
        picture_url: profile.picture,
      },
    });

  if (!createError && created.user) {
    return created.user.id;
  }

  const { data: listed, error: listError } =
    await admin.auth.admin.listUsers({ page: 1, perPage: 1000 });
  if (listError) {
    throw listError;
  }

  const existing = listed.users.find((user) => user.email === email);
  if (!existing) {
    throw createError ?? new Error("Failed to resolve Supabase auth user");
  }

  return existing.id;
}

export async function linkLineUserAndCreateSession(
  profile: LineProfile,
): Promise<void> {
  // profile.sub comes from the LINE Login channel (LIFF/OAuth).
  // It matches Messaging API webhook userId when both channels share the same provider.
  const lineUserId = profile.sub;
  const authUserId = await getOrCreateAuthUserId(lineUserId, profile);
  const admin = createAdminClient();
  const email = lineSyntheticEmail(lineUserId);

  const { error: identityError } = await admin.from("line_auth_identities").upsert(
    {
      auth_user_id: authUserId,
      line_user_id: lineUserId,
      display_name: profile.name ?? null,
      picture_url: profile.picture ?? null,
      updated_at: new Date().toISOString(),
    },
    { onConflict: "auth_user_id" },
  );

  if (identityError) {
    throw identityError;
  }

  const { data: linkData, error: linkError } =
    await admin.auth.admin.generateLink({
      type: "magiclink",
      email,
    });

  if (linkError || !linkData.properties?.hashed_token) {
    throw linkError ?? new Error("Failed to generate Supabase session link");
  }

  const supabase = await createClient();
  const { error: sessionError } = await supabase.auth.verifyOtp({
    token_hash: linkData.properties.hashed_token,
    type: "email",
  });

  if (sessionError) {
    throw sessionError;
  }
}
