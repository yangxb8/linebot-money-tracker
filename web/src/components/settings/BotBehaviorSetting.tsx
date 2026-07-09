"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { useTenant } from "@/components/TenantProvider";
import {
  fetchTenantSettings,
  saveTenantSettings,
} from "@/lib/settings/client";

type PresetOption = { value: string | null; label: string };

const EMOJI_LEVELS: Array<{ value: number | null; label: string }> = [
  { value: null, label: "Default" },
  { value: 0, label: "Off" },
  { value: 1, label: "Light" },
  { value: 2, label: "Normal" },
];

export function BotBehaviorSetting() {
  const { t, locale } = useLanguage();
  const { selectedTenant } = useTenant();
  const [preset, setPreset] = useState<string | null>(null);
  const [customText, setCustomText] = useState<string>("");
  const [emojiLevel, setEmojiLevel] = useState<number | null>(null);
  const [showItemDetails, setShowItemDetails] = useState(false);
  const [fiscalStartDay, setFiscalStartDay] = useState<number>(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const presets: PresetOption[] = useMemo(() => {
    const judyLabel =
      locale === "ja"
        ? "Judy Hopps（かわいいけどしっかり）"
        : locale === "zh"
          ? "Judy Hopps（可爱但坚定）"
          : "Judy Hopps (cute but firm)";
    return [
      { value: null, label: locale === "ja" ? "デフォルト" : locale === "zh" ? "默认" : "Default" },
      { value: "judy_hopps_cute_firm", label: judyLabel },
    ];
  }, [locale]);

  const load = useCallback(async () => {
    if (!selectedTenant) return;
    setLoading(true);
    setError(null);
    try {
      const settings = await fetchTenantSettings(selectedTenant);
      setFiscalStartDay(settings.fiscal_start_day);
      setPreset(settings.bot_persona_preset ?? null);
      setCustomText(settings.bot_persona_custom_text ?? "");
      setEmojiLevel(
        settings.bot_persona_emoji_level === undefined
          ? null
          : (settings.bot_persona_emoji_level ?? null),
      );
      setShowItemDetails(Boolean(settings.confirmation_show_item_details));
    } catch {
      setError("load_failed");
    } finally {
      setLoading(false);
    }
  }, [selectedTenant]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSave(next: {
    preset: string | null;
    customText: string;
    emojiLevel: number | null;
    showItemDetails: boolean;
  }) {
    if (!selectedTenant) return;
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const settings = await saveTenantSettings(selectedTenant, {
        fiscal_start_day: fiscalStartDay,
        bot_persona_preset: next.preset,
        bot_persona_custom_text: next.customText,
        bot_persona_emoji_level: next.emojiLevel,
        confirmation_show_item_details: next.showItemDetails,
      });
      setFiscalStartDay(settings.fiscal_start_day);
      setPreset(settings.bot_persona_preset ?? null);
      setCustomText(settings.bot_persona_custom_text ?? "");
      setEmojiLevel(settings.bot_persona_emoji_level ?? null);
      setShowItemDetails(Boolean(settings.confirmation_show_item_details));
      setSaved(true);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "save_failed";
      setError(msg || "save_failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    await handleSave({ preset: null, customText: "", emojiLevel: null, showItemDetails: false });
  }

  if (!selectedTenant) return null;

  if (loading) {
    return <p className="text-sm text-gray-500">{t("loading")}</p>;
  }

  return (
    <div className="space-y-4 rounded-xl border border-gray-200 bg-white p-4">
      <div className="space-y-1">
        <p className="text-sm font-medium text-gray-900">{t("botPersonaTitle")}</p>
        <p className="text-xs text-gray-500">{t("botPersonaDescription")}</p>
      </div>

      <div className="space-y-1">
        <label htmlFor="persona-preset" className="text-sm font-medium text-gray-900">
          {t("botPersonaPresetLabel")}
        </label>
        <select
          id="persona-preset"
          value={preset ?? ""}
          onChange={(event) => {
            const value = event.target.value || null;
            setPreset(value);
            setSaved(false);
          }}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900"
        >
          {presets.map((opt) => (
            <option key={opt.value ?? "default"} value={opt.value ?? ""}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-1">
        <label htmlFor="persona-emoji" className="text-sm font-medium text-gray-900">
          {t("botPersonaEmojiLabel")}
        </label>
        <select
          id="persona-emoji"
          value={emojiLevel === null ? "" : String(emojiLevel)}
          onChange={(event) => {
            setEmojiLevel(event.target.value === "" ? null : Number(event.target.value));
            setSaved(false);
          }}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900"
        >
          {EMOJI_LEVELS.map((opt) => (
            <option key={String(opt.value)} value={opt.value === null ? "" : String(opt.value)}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-1">
        <label htmlFor="persona-custom" className="text-sm font-medium text-gray-900">
          {t("botPersonaCustomTextLabel")}
        </label>
        <textarea
          id="persona-custom"
          value={customText}
          onChange={(event) => {
            setCustomText(event.target.value);
            setSaved(false);
          }}
          rows={3}
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900"
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="confirmation-item-details" className="text-sm font-medium text-gray-900">
          {t("confirmationShowItemDetailsLabel")}
        </label>
        <p className="text-xs text-gray-500">{t("confirmationShowItemDetailsHint")}</p>
        <input
          id="confirmation-item-details"
          type="checkbox"
          checked={showItemDetails}
          onChange={(event) => {
            setShowItemDetails(event.target.checked);
            setSaved(false);
          }}
          className="h-4 w-4 rounded border-gray-300"
        />
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() =>
            void handleSave({ preset, customText, emojiLevel, showItemDetails })
          }
          disabled={saving}
          className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {saving ? t("saving") : t("budgetSave")}
        </button>
        <button
          type="button"
          onClick={() => void handleReset()}
          disabled={saving}
          className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-900 disabled:opacity-60"
        >
          {t("botPersonaReset")}
        </button>
        {saved ? <span className="text-sm text-green-700">{t("saved")}</span> : null}
      </div>

      {error ? (
        <p className="text-sm text-red-600">
          {error === "load_failed" ? t("errorGeneric") : error}
        </p>
      ) : null}
    </div>
  );
}

