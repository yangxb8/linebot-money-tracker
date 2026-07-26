import type { TenantOption } from "@/lib/dashboard/tenants";
import type {
  CreateWishListPayload,
  ExecuteWishListPayload,
  UpdateWishListPayload,
  WishListItem,
  WishListOrder,
  WishListSort,
  WishListStatus,
} from "@/lib/wish-list/types";

function tenantParams(tenant: TenantOption): URLSearchParams {
  return new URLSearchParams({
    tenant_type: tenant.tenantType,
    tenant_id: tenant.tenantId,
  });
}

async function readError(response: Response, fallback: string): Promise<Error> {
  const data = (await response.json().catch(() => ({}))) as { error?: string };
  return new Error(data.error ?? fallback);
}

export async function fetchWishListItems(
  tenant: TenantOption,
  status: WishListStatus,
  sort: WishListSort,
  order?: WishListOrder,
): Promise<WishListItem[]> {
  const params = tenantParams(tenant);
  params.set("status", status);
  params.set("sort", sort);
  if (order) params.set("order", order);

  const response = await fetch(`/api/wish-list?${params.toString()}`);
  if (!response.ok) {
    throw await readError(response, "fetch_failed");
  }

  const data = (await response.json()) as { items?: WishListItem[] };
  return data.items ?? [];
}

export async function createWishListItem(
  payload: CreateWishListPayload,
): Promise<WishListItem> {
  const response = await fetch("/api/wish-list", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw await readError(response, "create_failed");
  }
  return response.json() as Promise<WishListItem>;
}

export async function updateWishListItem(
  id: string,
  payload: UpdateWishListPayload,
): Promise<WishListItem> {
  const response = await fetch(`/api/wish-list/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw await readError(response, "update_failed");
  }
  return response.json() as Promise<WishListItem>;
}

export async function deleteWishListItem(id: string): Promise<void> {
  const response = await fetch(`/api/wish-list/${id}`, { method: "DELETE" });
  if (!response.ok) {
    throw await readError(response, "delete_failed");
  }
}

export async function reorderWishListItems(
  tenant: TenantOption,
  orderedIds: string[],
): Promise<void> {
  const response = await fetch("/api/wish-list/reorder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tenant_type: tenant.tenantType,
      tenant_id: tenant.tenantId,
      ordered_ids: orderedIds,
    }),
  });
  if (!response.ok) {
    throw await readError(response, "reorder_failed");
  }
}

export async function executeWishListItem(
  id: string,
  payload: ExecuteWishListPayload,
) {
  const response = await fetch(`/api/wish-list/${id}/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw await readError(response, "execute_failed");
  }
  return response.json() as Promise<{ item: WishListItem }>;
}

export function defaultWishListFormValues() {
  return {
    name: "",
    amount: "",
    category_node_id: "",
    product_url: "",
  };
}

export function wishListItemToFormValues(item: WishListItem) {
  return {
    name: item.name,
    amount: String(item.amount),
    category_node_id: item.category_node_id,
    product_url: item.product_url ?? "",
  };
}
