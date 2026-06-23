import type { User } from "@supabase/supabase-js";
import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";
import { lineSyntheticEmail } from "@/lib/line/oauth";
import type { LineProfile } from "@/lib/line/verify-id-token";

function isDuplicateEmailError(error: { message?: string } | null): boolean {
  const message = error?.message?.toLowerCase() ?? "";
  return message.includes("already been registered") || message.includes("already exists");
}

async function findAuthUserIdByLineUserId(
  lineUserId: string,
): Promise<string | null> {
  const admin = createAdminClient();
  const { data, error } = await admin
    .from("line_auth_identities")
    .select("auth_user_id")
    .eq("line_user_id", lineUserId)
    .maybeSingle();

  if (error) {
    throw error;
  }

  return data?.auth_user_id ?? null;
}

async function findAuthUserByEmail(email: string): Promise<User | null> {
  const admin = createAdminClient();
  let page = 1;

  while (true) {
    const { data, error } = await admin.auth.admin.listUsers({
      page,
      perPage: 1000,
    });
    if (error) {
      throw error;
    }

    const existing = data.users.find((user) => user.email === email);
    if (existing) {
      return existing;
    }

    if (data.users.length < 1000) {
      break;
    }
    page += 1;
  }

  return null;
}

async function getOrCreateAuthUserId(
  lineUserId: string,
  profile: LineProfile,
): Promise<string> {
  const admin = createAdminClient();
  const email = lineSyntheticEmail(lineUserId);

  const linkedAuthUserId = await findAuthUserIdByLineUserId(lineUserId);
  if (linkedAuthUserId) {
    return linkedAuthUserId;
  }

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

  if (isDuplicateEmailError(createError)) {
    const existing = await findAuthUserByEmail(email);
    if (existing) {
      return existing.id;
    }
  }

  throw createError ?? new Error("Failed to resolve Supabase auth user");
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
