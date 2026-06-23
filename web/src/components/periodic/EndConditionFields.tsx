"use client";

import type { EndKind } from "@/lib/periodic/types";
import { useLanguage } from "@/components/LanguageProvider";
import { IsoDateInput } from "@/components/IsoDateInput";

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
  endDateInvalid?: boolean;
  endAmountCapInvalid?: boolean;
  endRepeatLimitInvalid?: boolean;
};

const END_KINDS: EndKind[] = ["never", "on_date", "amount_cap", "repeat_count"];

function fieldClass(invalid?: boolean) {
  return `mt-1 w-full rounded-lg border px-3 py-2 text-sm ${
    invalid
      ? "border-red-500 focus:border-red-500 focus:outline-none focus:ring-2 focus:ring-red-200"
      : "border-gray-200"
  }`;
}

export function EndConditionFields({
  endKind,
  endDate,
  endAmountCap,
  endRepeatLimit,
  onChange,
  endDateInvalid = false,
  endAmountCapInvalid = false,
  endRepeatLimitInvalid = false,
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
          <IsoDateInput
            className="mt-1"
            value={endDate}
            invalid={endDateInvalid}
            onChange={(value) => onChange({ end_date: value })}
          />
        </div>
      ) : null}

      {endKind === "amount_cap" ? (
        <div>
          <label className="text-xs text-gray-500">{t("periodicEndAmountCap")}</label>
          <input
            type="text"
            inputMode="numeric"
            className={fieldClass(endAmountCapInvalid)}
            value={endAmountCap}
            onChange={(e) => onChange({ end_amount_cap: e.target.value })}
          />
        </div>
      ) : null}

      {endKind === "repeat_count" ? (
        <div>
          <label className="text-xs text-gray-500">{t("periodicEndRepeatLimit")}</label>
          <input
            type="text"
            inputMode="numeric"
            className={fieldClass(endRepeatLimitInvalid)}
            value={endRepeatLimit}
            onChange={(e) => onChange({ end_repeat_limit: e.target.value })}
          />
        </div>
      ) : null}
    </div>
  );
}
