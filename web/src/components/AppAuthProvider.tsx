"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import liff from "@line/liff";
import { createClient } from "@/lib/supabase/client";
import { LanguageProvider, useLanguage } from "@/components/LanguageProvider";
import { TenantProvider } from "@/components/TenantProvider";
import {
  fetchLineUserId,
  fetchSharedTenants,
  fetchUserLocale,
  type TenantOption,
} from "@/lib/dashboard/tenants";
import { normalizeLocale } from "@/lib/i18n/locale";

type AuthPhase = "checking" | "liff" | "ready" | "unauthenticated";

type AppAuthContextValue = {
  lineUserId: string;
  sharedTenants: TenantOption[];
  signOut: () => Promise<void>;
};

const AppAuthContext = createContext<AppAuthContextValue | null>(null);

function AppAuthBootstrap({ children }: { children: ReactNode }) {
  const { setLocale } = useLanguage();
  const [phase, setPhase] = useState<AuthPhase>("checking");
  const [lineUserId, setLineUserId] = useState<string | null>(null);
  const [sharedTenants, setSharedTenants] = useState<TenantOption[]>([]);

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
  }, [setLocale]);

  async function signOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    await fetch("/api/auth/signout", { method: "POST" });
    window.location.href = "/login";
  }

  const { t } = useLanguage();

  if (phase === "checking" || phase === "liff") {
    return (
      <p className="text-center text-sm text-gray-500 py-16">{t("loading")}</p>
    );
  }

  if (phase === "unauthenticated") {
    window.location.href = "/login?error=auth_failed";
    return null;
  }

  if (!lineUserId) {
    return (
      <p className="text-center text-sm text-gray-500 py-16">{t("loading")}</p>
    );
  }

  return (
    <AppAuthContext.Provider value={{ lineUserId, sharedTenants, signOut }}>
      <TenantProvider personalTenantId={lineUserId}>{children}</TenantProvider>
    </AppAuthContext.Provider>
  );
}

export function AppAuthProvider({
  children,
  initialLocale,
}: {
  children: ReactNode;
  initialLocale?: string | null;
}) {
  return (
    <LanguageProvider initialLocale={initialLocale}>
      <AppAuthBootstrap>{children}</AppAuthBootstrap>
    </LanguageProvider>
  );
}

export function useAppAuth() {
  const context = useContext(AppAuthContext);
  if (!context) {
    throw new Error("useAppAuth must be used within AppAuthProvider");
  }
  return context;
}
