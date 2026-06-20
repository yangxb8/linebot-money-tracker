"use client";

import { useEffect, useState } from "react";
import liff from "@line/liff";
import { createClient } from "@/lib/supabase/client";
import { LanguageProvider, useLanguage } from "@/components/LanguageProvider";
import { ExpenseList } from "@/components/ExpenseList";
import { TenantSwitcher } from "@/components/TenantSwitcher";
import {
  fetchLineUserId,
  fetchSharedTenants,
  fetchUserLocale,
  type TenantOption,
} from "@/lib/dashboard/tenants";
import { normalizeLocale } from "@/lib/i18n/locale";

type AuthPhase = "checking" | "liff" | "ready" | "unauthenticated";

function DashboardContent() {
  const { t, setLocale } = useLanguage();
  const [phase, setPhase] = useState<AuthPhase>("checking");
  const [lineUserId, setLineUserId] = useState<string | null>(null);
  const [sharedTenants, setSharedTenants] = useState<TenantOption[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<TenantOption | null>(
    null,
  );

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const supabase = createClient();
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (user) {
        const id = await fetchLineUserId();
        const shared = await fetchSharedTenants();
        const locale = await fetchUserLocale();
        if (!cancelled && id) {
          if (locale) setLocale(normalizeLocale(locale));
          setLineUserId(id);
          setSharedTenants(shared);
          setSelectedTenant({ tenantType: "user", tenantId: id });
          setPhase("ready");
        }
        return;
      }

      const liffId = process.env.NEXT_PUBLIC_LINE_LIFF_ID;
      const params = new URLSearchParams(window.location.search);
      const fromLine =
        params.get("source") === "line" || window.location.href.includes("liff");

      if (liffId && (fromLine || typeof liff.isInClient === "function")) {
        setPhase("liff");
        try {
          await liff.init({ liffId });
          if (!liff.isLoggedIn()) {
            liff.login({ redirectUri: window.location.href });
            return;
          }
          const idToken = liff.getIDToken();
          if (!idToken) {
            setPhase("unauthenticated");
            return;
          }
          const response = await fetch("/api/auth/line/liff", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ idToken }),
          });
          if (!response.ok) {
            setPhase("unauthenticated");
            return;
          }
          const id = await fetchLineUserId();
          const shared = await fetchSharedTenants();
          const locale = await fetchUserLocale();
          if (!cancelled && id) {
            if (locale) setLocale(normalizeLocale(locale));
            setLineUserId(id);
            setSharedTenants(shared);
            setSelectedTenant({ tenantType: "user", tenantId: id });
            setPhase("ready");
          }
        } catch {
          if (!cancelled) setPhase("unauthenticated");
        }
        return;
      }

      if (!cancelled) setPhase("unauthenticated");
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    await fetch("/api/auth/signout", { method: "POST" });
    window.location.href = "/login";
  }

  if (phase === "checking" || phase === "liff") {
    return (
      <p className="text-center text-sm text-gray-500 py-16">{t("loading")}</p>
    );
  }

  if (phase === "unauthenticated") {
    window.location.href = "/login?error=auth_failed";
    return null;
  }

  if (!lineUserId || !selectedTenant) {
    return (
      <p className="text-center text-sm text-gray-500 py-16">{t("loading")}</p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <TenantSwitcher
          personalTenantId={lineUserId}
          sharedTenants={sharedTenants}
          selected={selectedTenant}
          onChange={setSelectedTenant}
        />
        <button
          type="button"
          onClick={() => void handleSignOut()}
          className="shrink-0 text-xs text-gray-500 underline"
        >
          {t("signOut")}
        </button>
      </div>
      <ExpenseList tenant={selectedTenant} isNewUser={sharedTenants.length === 0} />
    </div>
  );
}

export function DashboardClient({
  initialLocale,
}: {
  initialLocale?: string | null;
}) {
  return (
    <LanguageProvider initialLocale={initialLocale}>
      <DashboardContent />
    </LanguageProvider>
  );
}
