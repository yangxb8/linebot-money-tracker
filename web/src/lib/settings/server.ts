import { createClient } from "@/lib/supabase/server";
import {
  assertTenantAccess,
  parseTenantParams,
} from "@/lib/periodic/tenant-access";
import type { TenantSettings } from "@/lib/settings/types";

export { parseTenantParams };

const DEFAULT_SETTINGS: TenantSettings = {
  fiscal_start_day: 1,
  bot_persona_preset: null,
  bot_persona_custom_text: null,
  bot_persona_emoji_level: null,
  confirmation_show_item_details: false,
};

const PERSONA_PRESETS = new Set(["judy_hopps_cute_firm"]);

function normalizePersonaPreset(value: unknown): string | null {
  const preset = String(value ?? "").trim();
  if (!preset) return null;
  if (!PERSONA_PRESETS.has(preset)) {
    throw new Response("invalid_bot_persona_preset", { status: 400 });
  }
  return preset;
}

function normalizePersonaCustomText(value: unknown): string | null {
  const text = String(value ?? "").trim();
  if (!text) return null;
  // Keep short to prevent broken UX and reduce risk.
  if (text.length > 200) {
    throw new Response("invalid_bot_persona_custom_text", { status: 400 });
  }
  return text;
}

function normalizeConfirmationShowItemDetails(value: unknown): boolean {
  return Boolean(value);
}

function normalizeEmojiLevel(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const level = Number(value);
  if (!Number.isInteger(level) || level < 0 || level > 2) {
    throw new Response("invalid_bot_persona_emoji_level", { status: 400 });
  }
  return level;
}

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
    .select(
      "fiscal_start_day,bot_persona_preset,bot_persona_custom_text,bot_persona_emoji_level,confirmation_show_item_details",
    )
    .eq("tenant_type", tenantType)
    .eq("tenant_id", tenantId)
    .maybeSingle();

  if (error) {
    throw new Response(error.message, { status: 400 });
  }

  if (!data) {
    return DEFAULT_SETTINGS;
  }

  return {
    fiscal_start_day: Number(data.fiscal_start_day),
    bot_persona_preset: data.bot_persona_preset ?? null,
    bot_persona_custom_text: data.bot_persona_custom_text ?? null,
    bot_persona_emoji_level:
      data.bot_persona_emoji_level === null || data.bot_persona_emoji_level === undefined
        ? null
        : Number(data.bot_persona_emoji_level),
    confirmation_show_item_details: Boolean(data.confirmation_show_item_details),
  };
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

  const botPersonaPreset = normalizePersonaPreset(settings.bot_persona_preset);
  const botPersonaCustomText = normalizePersonaCustomText(
    settings.bot_persona_custom_text,
  );
  const botPersonaEmojiLevel = normalizeEmojiLevel(settings.bot_persona_emoji_level);
  const confirmationShowItemDetails = normalizeConfirmationShowItemDetails(
    settings.confirmation_show_item_details,
  );

  const { data, error } = await supabase
    .from("tenant_settings")
    .upsert(
      {
        tenant_type: tenantType,
        tenant_id: tenantId,
        fiscal_start_day: fiscalStartDay,
        bot_persona_preset: botPersonaPreset,
        bot_persona_custom_text: botPersonaCustomText,
        bot_persona_emoji_level: botPersonaEmojiLevel,
        confirmation_show_item_details: confirmationShowItemDetails,
        updated_at: new Date().toISOString(),
        bot_persona_updated_at: new Date().toISOString(),
      },
      { onConflict: "tenant_type,tenant_id" },
    )
    .select(
      "fiscal_start_day,bot_persona_preset,bot_persona_custom_text,bot_persona_emoji_level,confirmation_show_item_details",
    )
    .single();

  if (error) {
    throw new Response(error.message, { status: 400 });
  }

  return {
    fiscal_start_day: Number(data.fiscal_start_day),
    bot_persona_preset: data.bot_persona_preset ?? null,
    bot_persona_custom_text: data.bot_persona_custom_text ?? null,
    bot_persona_emoji_level:
      data.bot_persona_emoji_level === null || data.bot_persona_emoji_level === undefined
        ? null
        : Number(data.bot_persona_emoji_level),
    confirmation_show_item_details: Boolean(data.confirmation_show_item_details),
  };
}
