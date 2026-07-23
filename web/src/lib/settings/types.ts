export type ReplyLanguage = "en" | "ja" | "zh";

export type TenantSettings = {
  fiscal_start_day: number;
  bot_persona_preset?: string | null;
  bot_persona_custom_text?: string | null;
  bot_persona_emoji_level?: number | null;
  confirmation_show_item_details?: boolean | null;
  /** null = Default (system / LINE profile language) */
  reply_language?: ReplyLanguage | null;
};
