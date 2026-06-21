import type { CategoryNode, CategoryTreeResponse } from "@/lib/categories/types";
import type { TenantOption } from "@/lib/dashboard/tenants";

function tenantQuery(tenant: TenantOption): string {
  return `tenant_type=${encodeURIComponent(tenant.tenantType)}&tenant_id=${encodeURIComponent(tenant.tenantId)}`;
}

export async function fetchCategories(
  tenant: TenantOption,
): Promise<CategoryTreeResponse> {
  const response = await fetch(`/api/categories?${tenantQuery(tenant)}`);
  if (!response.ok) {
    throw new Error("Failed to load categories");
  }
  return response.json() as Promise<CategoryTreeResponse>;
}

export async function createCategory(
  tenant: TenantOption,
  body: {
    level: 1 | 2;
    parent_id?: string;
    name_ja: string;
  },
): Promise<CategoryNode> {
  const response = await fetch("/api/categories", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tenant_type: tenant.tenantType,
      tenant_id: tenant.tenantId,
      ...body,
    }),
  });
  if (!response.ok) {
    const data = (await response.json().catch(() => ({}))) as { message?: string };
    throw new Error(data.message ?? "Failed to create category");
  }
  return response.json() as Promise<CategoryNode>;
}

export async function updateCategory(
  id: string,
  body: { name_ja?: string; sort_order?: number },
): Promise<CategoryNode> {
  const response = await fetch(`/api/categories/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error("Failed to update category");
  }
  return response.json() as Promise<CategoryNode>;
}

export async function moveCategory(
  id: string,
  body: { level: 1 | 2; parent_id?: string | null },
): Promise<{ id: string; level: number; parent_id: string | null }> {
  const response = await fetch(`/api/categories/${id}/move`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const data = (await response.json().catch(() => ({}))) as { error?: string };
    throw new Error(data.error ?? "Failed to move category");
  }
  return response.json() as Promise<{
    id: string;
    level: number;
    parent_id: string | null;
  }>;
}

export async function deleteCategory(
  id: string,
  tenant: TenantOption,
  transferToId?: string,
): Promise<{ transferred_expenses: number }> {
  const response = await fetch(`/api/categories/${id}/delete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tenant_type: tenant.tenantType,
      tenant_id: tenant.tenantId,
      transfer_to_id: transferToId,
    }),
  });
  if (!response.ok) {
    const data = (await response.json().catch(() => ({}))) as {
      error?: string;
      message?: string;
    };
    const err = new Error(data.message ?? "Failed to delete category") as Error & {
      code?: string;
    };
    err.code = data.error;
    throw err;
  }
  return response.json() as Promise<{ transferred_expenses: number }>;
}
