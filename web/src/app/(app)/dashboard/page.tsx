"use client";

import { ExpenseList } from "@/components/ExpenseList";
import { useAppAuth } from "@/components/AppAuthProvider";
import { useTenant } from "@/components/TenantProvider";
import { useLanguage } from "@/components/LanguageProvider";

export default function DashboardPage() {
  const { t } = useLanguage();
  const { sharedTenants } = useAppAuth();
  const { selectedTenant } = useTenant();

  if (!selectedTenant) {
    return (
      <p className="text-center text-sm text-gray-500 py-16">{t("loading")}</p>
    );
  }

  return (
    <ExpenseList
      tenant={selectedTenant}
      isNewUser={sharedTenants.length === 0}
    />
  );
}
