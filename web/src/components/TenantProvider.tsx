"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { TenantOption } from "@/lib/dashboard/tenants";

const STORAGE_KEY = "expense_selected_tenant";

type TenantContextValue = {
  selectedTenant: TenantOption | null;
  setSelectedTenant: (tenant: TenantOption) => void;
  isTenantReady: boolean;
};

const TenantContext = createContext<TenantContextValue | null>(null);

function parseStoredTenant(raw: string | null): TenantOption | null {
  if (!raw) return null;
  const [tenantType, ...rest] = raw.split(":");
  const tenantId = rest.join(":");
  if (!tenantType || !tenantId) return null;
  if (tenantType !== "user" && tenantType !== "group" && tenantType !== "room") {
    return null;
  }
  return { tenantType, tenantId };
}

export function TenantProvider({
  personalTenantId,
  children,
}: {
  personalTenantId: string;
  children: ReactNode;
}) {
  const [selectedTenant, setSelectedTenantState] = useState<TenantOption>(() => ({
    tenantType: "user",
    tenantId: personalTenantId,
  }));
  const [isTenantReady, setIsTenantReady] = useState(false);

  useEffect(() => {
    const stored = parseStoredTenant(localStorage.getItem(STORAGE_KEY));
    if (
      stored &&
      (stored.tenantType !== "user" || stored.tenantId === personalTenantId)
    ) {
      setSelectedTenantState(stored);
    } else {
      setSelectedTenantState({
        tenantType: "user",
        tenantId: personalTenantId,
      });
    }
    setIsTenantReady(true);
  }, [personalTenantId]);

  const setSelectedTenant = useCallback((tenant: TenantOption) => {
    setSelectedTenantState(tenant);
    localStorage.setItem(STORAGE_KEY, `${tenant.tenantType}:${tenant.tenantId}`);
  }, []);

  const value = useMemo(
    () => ({ selectedTenant, setSelectedTenant, isTenantReady }),
    [selectedTenant, setSelectedTenant, isTenantReady],
  );

  return (
    <TenantContext.Provider value={value}>{children}</TenantContext.Provider>
  );
}

export function useTenant() {
  const context = useContext(TenantContext);
  if (!context) {
    throw new Error("useTenant must be used within TenantProvider");
  }
  return context;
}
