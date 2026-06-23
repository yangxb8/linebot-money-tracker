"use client";

import type { EndKind } from "@/lib/periodic/types";
import { useLanguage } from "@/components/LanguageProvider";

type Props = {
  endKind: EndKind;
  endDate: string;
  endAmountCap: string;
  endRepeatLimit: string;
  onChange: (patch: {
    end_kind?: EndKind;
    end_date?: string;
    end_amount_cap?: string;
    end_repeat_limit?: string;
  }) => void;
};

const END_KINDS: EndKind[] = ["never", "on_date", "amount_cap", "repeat_count"];

export function EndConditionFields({
  endKind,
  endDate,
  endAmountCap,
  endRepeatLimit,
  onChange,
}: Props) {
  const { t } = useLanguage();

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-700">
        {t("periodicEndCondition")}
      </label>
      <select
        className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
        value={endKind}
        onChange={(e) => onChange({ end_kind: e.target.value as EndKind })}
      >
        {END_KINDS.map((kind) => (
          <option key={kind} value={kind}>
            {t(`endKind_${kind}` as never)}
          </option>
        ))}
      </select>

      {endKind === "on_date" ? (
        <div>
          <label className="text-xs text-gray-500">{t("periodicEndDate")}</label>
          <input
            type="date"
            className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
            value={endDate}
            onChange={(e) => onChange({ end_date: e.target.value })}
          />
        </div>
      ) : null}

      {endKind === "amount_cap" ? (
        <div>
          <label className="text-xs text-gray-500">{t("periodicEndAmountCap")}</label>
          <input
            type="number"
            min={1}
            className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
            value={endAmountCap}
            onChange={(e) => onChange({ end_amount_cap: e.target.value })}
          />
        </div>
      ) : null}

      {endKind === "repeat_count" ? (
        <div>
          <label className="text-xs text-gray-500">{t("periodicEndRepeatLimit")}</label>
          <input
            type="number"
            min={1}
            className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
            value={endRepeatLimit}
            onChange={(e) => onChange({ end_repeat_limit: e.target.value })}
          />
        </div>
      ) : null}
    </div>
  );
}
