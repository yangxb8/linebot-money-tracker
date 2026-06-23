"use client";

import { useLanguage } from "@/components/LanguageProvider";

type Props = {
  onStart: () => void;
};

export function BudgetEmptyState({ onStart }: Props) {
  const { t } = useLanguage();

  return (
    <div className="rounded-xl border border-dashed border-gray-200 bg-white p-6 text-center">
      <p className="text-sm text-gray-600">{t("budgetEmptyHint")}</p>
      <button
        type="button"
        onClick={onStart}
        className="mt-4 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white"
      >
        {t("budgetStartSetup")}
      </button>
    </div>
  );
}
