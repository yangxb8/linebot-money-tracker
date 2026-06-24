"use client";

import { useCallback, useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { useTenant } from "@/components/TenantProvider";
import {
  fetchTenantSettings,
  saveTenantSettings,
} from "@/lib/settings/client";
import type { Locale } from "@/lib/i18n/messages";

const FISCAL_START_DAYS = Array.from({ length: 28 }, (_, i) => i + 1);

function fiscalDayLabel(day: number, locale: Locale): string {
  if (locale === "en") return `Day ${day}`;
  if (locale === "zh") return `每月${day}日`;
  return `毎月${day}日`;
}

export function FiscalMonthSetting() {
  const { t, locale } = useLanguage();
  const { selectedTenant } = useTenant();
  const [fiscalStartDay, setFiscalStartDay] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!selectedTenant) return;
    setLoading(true);
    setError(null);
    try {
      const settings = await fetchTenantSettings(selectedTenant);
      setFiscalStartDay(settings.fiscal_start_day);
    } catch {
      setError("load_failed");
    } finally {
      setLoading(false);
    }
  }, [selectedTenant]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSave() {
    if (!selectedTenant) return;
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const settings = await saveTenantSettings(selectedTenant, {
        fiscal_start_day: fiscalStartDay,
      });
      setFiscalStartDay(settings.fiscal_start_day);
      setSaved(true);
    } catch {
      setError("save_failed");
    } finally {
      setSaving(false);
    }
  }

  if (!selectedTenant) return null;

  if (loading) {
    return <p className="text-sm text-gray-500">{t("loading")}</p>;
  }

  return (
    <div className="space-y-4 rounded-xl border border-gray-200 bg-white p-4">
      <div className="space-y-1">
        <label htmlFor="fiscal-start-day" className="text-sm font-medium text-gray-900">
          {t("settingsFiscalStartDay")}
        </label>
        <p className="text-xs text-gray-500">{t("settingsFiscalMonthDescription")}</p>
      </div>

      <select
        id="fiscal-start-day"
        value={fiscalStartDay}
        onChange={(event) => {
          setFiscalStartDay(Number(event.target.value));
          setSaved(false);
        }}
        className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900"
      >
        {FISCAL_START_DAYS.map((day) => (
          <option key={day} value={day}>
            {fiscalDayLabel(day, locale)}
          </option>
        ))}
      </select>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => void handleSave()}
          disabled={saving}
          className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {saving ? t("saving") : t("budgetSave")}
        </button>
        {saved ? <span className="text-sm text-green-700">{t("saved")}</span> : null}
      </div>

      {error ? (
        <p className="text-sm text-red-600">
          {error === "save_failed" ? t("saveFailed") : t("errorGeneric")}
        </p>
      ) : null}
    </div>
  );
}
