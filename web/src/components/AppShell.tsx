"use client";

import { useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { useAppAuth } from "@/components/AppAuthProvider";
import { useLanguage } from "@/components/LanguageProvider";
import { SideDrawer } from "@/components/SideDrawer";
import { TenantSwitcher } from "@/components/TenantSwitcher";
import { useTenant } from "@/components/TenantProvider";
import type { MessageKey } from "@/lib/i18n/messages";

function pageTitleKey(pathname: string): MessageKey {
  if (pathname === "/settings/categories") return "navCategories";
  if (pathname === "/settings/fiscal-month") return "settingsFiscalMonth";
  if (pathname.startsWith("/settings")) return "navSettings";
  if (pathname === "/periodic-expenses") return "navPeriodicExpenses";
  if (pathname === "/budget") return "navBudget";
  return "navExpenses";
}

export function AppShell({ children }: { children: ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const pathname = usePathname();
  const { t } = useLanguage();
  const { lineUserId, sharedTenants, signOut } = useAppAuth();
  const { selectedTenant, setSelectedTenant } = useTenant();

  const title = t(pageTitleKey(pathname));

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="sticky top-0 z-30 border-b border-gray-100 bg-white">
        <div className="mx-auto flex max-w-lg items-center gap-3 px-4 py-3">
          <button
            type="button"
            aria-label={t("openMenu")}
            onClick={() => setDrawerOpen(true)}
            className="rounded-lg border border-gray-200 px-2.5 py-1.5 text-lg leading-none text-gray-700"
          >
            ☰
          </button>
          <h1 className="flex-1 text-lg font-semibold text-gray-900">{title}</h1>
        </div>
        {selectedTenant ? (
          <div className="mx-auto max-w-lg px-4 pb-3">
            <TenantSwitcher
              personalTenantId={lineUserId}
              sharedTenants={sharedTenants}
              selected={selectedTenant}
              onChange={setSelectedTenant}
            />
          </div>
        ) : null}
      </header>

      <SideDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onSignOut={signOut}
      />

      <main className="mx-auto max-w-lg px-4 py-4">{children}</main>
    </div>
  );
}
