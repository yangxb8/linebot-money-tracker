"use client";

import Link from "next/link";
import { useLanguage } from "@/components/LanguageProvider";

type SettingsItem = {
  href: string;
  labelKey: "navCategories" | "settingsFiscalMonth" | "settingsBotBehavior";
  descriptionKey:
    | "settingsCategoriesHint"
    | "settingsFiscalMonthHint"
    | "settingsBotBehaviorHint";
};

const SETTINGS_ITEMS: SettingsItem[] = [
  {
    href: "/settings/categories",
    labelKey: "navCategories",
    descriptionKey: "settingsCategoriesHint",
  },
  {
    href: "/settings/fiscal-month",
    labelKey: "settingsFiscalMonth",
    descriptionKey: "settingsFiscalMonthHint",
  },
  {
    href: "/settings/bot-behavior",
    labelKey: "settingsBotBehavior",
    descriptionKey: "settingsBotBehaviorHint",
  },
];

export function SettingsMenu() {
  const { t } = useLanguage();

  return (
    <div className="divide-y divide-gray-100 overflow-hidden rounded-xl border border-gray-200 bg-white">
      {SETTINGS_ITEMS.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-gray-50"
        >
          <div>
            <p className="text-sm font-medium text-gray-900">{t(item.labelKey)}</p>
            <p className="text-xs text-gray-500">{t(item.descriptionKey)}</p>
          </div>
          <span className="text-gray-400" aria-hidden>
            ›
          </span>
        </Link>
      ))}
    </div>
  );
}
