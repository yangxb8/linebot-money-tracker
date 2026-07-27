import type { WishListItem, WishListSort } from "@/lib/wish-list/types";

export function compareWishListItems(
  a: WishListItem,
  b: WishListItem,
  sort: WishListSort,
): number {
  if (sort === "created") {
    const byCreated = b.created_at.localeCompare(a.created_at);
    if (byCreated !== 0) return byCreated;
    return a.sort_order - b.sort_order;
  }

  if (sort === "price") {
    const byAmount = b.amount - a.amount;
    if (byAmount !== 0) return byAmount;
    return a.sort_order - b.sort_order;
  }

  const byPriority = a.sort_order - b.sort_order;
  if (byPriority !== 0) return byPriority;
  return a.created_at.localeCompare(b.created_at);
}

export function sortWishListItems(
  items: WishListItem[],
  sort: WishListSort,
): WishListItem[] {
  return [...items].sort((a, b) => compareWishListItems(a, b, sort));
}

export function upsertWishListItem(
  items: WishListItem[],
  item: WishListItem,
  sort: WishListSort,
): WishListItem[] {
  const next = [...items.filter((row) => row.id !== item.id), item];
  return sortWishListItems(next, sort);
}

export function removeWishListItem(
  items: WishListItem[],
  id: string,
): WishListItem[] {
  return items.filter((row) => row.id !== id);
}

export function reorderWishListItemIds(
  items: WishListItem[],
  orderedIds: string[],
): WishListItem[] {
  const byId = new Map(items.map((row) => [row.id, row]));
  return orderedIds
    .map((id, sortOrder) => {
      const item = byId.get(id);
      return item ? { ...item, sort_order: sortOrder } : null;
    })
    .filter((row): row is WishListItem => Boolean(row));
}
