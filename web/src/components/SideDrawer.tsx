"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLanguage } from "@/components/LanguageProvider";

type NavItem = {
  href: string;
  labelKey: "navExpenses" | "navCategories" | "navPeriodicExpenses";
};

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", labelKey: "navExpenses" },
  { href: "/periodic-expenses", labelKey: "navPeriodicExpenses" },
  { href: "/categories", labelKey: "navCategories" },
];

type Props = {
  open: boolean;
  onClose: () => void;
  onSignOut: () => void;
};

export function SideDrawer({ open, onClose, onSignOut }: Props) {
  const pathname = usePathname();
  const { t } = useLanguage();

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-black/40 transition-opacity ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
        aria-hidden={!open}
      />
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] bg-white shadow-xl transition-transform ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-hidden={!open}
      >
        <div className="flex h-full flex-col">
          <div className="border-b border-gray-100 px-4 py-4">
            <p className="text-lg font-semibold text-gray-900">{t("appTitle")}</p>
          </div>
          <nav className="flex-1 px-2 py-3">
            {NAV_ITEMS.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onClose}
                  className={`block rounded-lg px-3 py-2.5 text-sm font-medium ${
                    active
                      ? "bg-gray-100 text-gray-900"
                      : "text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  {t(item.labelKey)}
                </Link>
              );
            })}
          </nav>
          <div className="border-t border-gray-100 p-4">
            <button
              type="button"
              onClick={() => {
                onClose();
                void onSignOut();
              }}
              className="text-sm text-gray-500 underline"
            >
              {t("signOut")}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
