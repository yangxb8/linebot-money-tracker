"use client";

import { useLanguage } from "@/components/LanguageProvider";
import { shortTenantId } from "@/lib/i18n/locale";
import type { TenantOption } from "@/lib/dashboard/tenants";

type Props = {
  personalTenantId: string;
  sharedTenants: TenantOption[];
  selected: TenantOption;
  onChange: (tenant: TenantOption) => void;
};

export function TenantSwitcher({
  personalTenantId,
  sharedTenants,
  selected,
  onChange,
}: Props) {
  const { t } = useLanguage();

  const options: TenantOption[] = [
    { tenantType: "user", tenantId: personalTenantId },
    ...sharedTenants,
  ];

  if (options.length <= 1) {
    return (
      <div className="text-sm font-medium text-gray-700 px-1">
        {t("personalLedger")}
      </div>
    );
  }

  function label(option: TenantOption): string {
    if (option.tenantType === "user") return t("personalLedger");
    const prefix =
      option.tenantType === "group" ? t("groupLedger") : t("roomLedger");
    return `${prefix} …${shortTenantId(option.tenantId)}`;
  }

  return (
    <label className="flex flex-col gap-1 w-full">
      <span className="text-xs text-gray-500">{t("selectTenant")}</span>
      <select
        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm shadow-sm"
        value={`${selected.tenantType}:${selected.tenantId}`}
        onChange={(event) => {
          const [tenantType, tenantId] = event.target.value.split(":");
          onChange({
            tenantType: tenantType as TenantOption["tenantType"],
            tenantId,
          });
        }}
      >
        {options.map((option) => (
          <option
            key={`${option.tenantType}:${option.tenantId}`}
            value={`${option.tenantType}:${option.tenantId}`}
          >
            {label(option)}
          </option>
        ))}
      </select>
    </label>
  );
}
