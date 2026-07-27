"use client";

import { useCallback, useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { useTenant } from "@/components/TenantProvider";
import { WishListActiveList } from "@/components/wish-list/WishListActiveList";
import { WishListExecutedList } from "@/components/wish-list/WishListExecutedList";
import { WishListExecuteDialog } from "@/components/wish-list/WishListExecuteDialog";
import { WishListItemForm } from "@/components/wish-list/WishListItemForm";
import {
  deleteWishListItem,
  fetchWishListItems,
  reorderWishListItems,
} from "@/lib/wish-list/client";
import {
  removeWishListItem,
  reorderWishListItemIds,
  upsertWishListItem,
} from "@/lib/wish-list/list-mutations";
import type {
  WishListItem,
  WishListSort,
  WishListStatus,
} from "@/lib/wish-list/types";

export function WishListPage() {
  const { t } = useLanguage();
  const { selectedTenant } = useTenant();
  const [items, setItems] = useState<WishListItem[]>([]);
  const [filter, setFilter] = useState<WishListStatus>("active");
  const [sort, setSort] = useState<WishListSort>("priority");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<WishListItem | null>(null);
  const [executing, setExecuting] = useState<WishListItem | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!selectedTenant) return;
    setLoading(true);
    setLoadError(null);
    try {
      const rows = await fetchWishListItems(selectedTenant, filter, sort);
      setItems(rows);
    } catch {
      setLoadError("fetch_failed");
    } finally {
      setLoading(false);
    }
  }, [filter, selectedTenant, sort]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleDelete(item: WishListItem) {
    if (!window.confirm(t("wishListDeleteConfirm"))) return;

    const previous = items;
    setItems(removeWishListItem(items, item.id));
    setBusyId(item.id);
    setActionError(null);
    try {
      await deleteWishListItem(item.id);
    } catch {
      setItems(previous);
      setActionError("action_failed");
    } finally {
      setBusyId(null);
    }
  }

  async function handleReorder(orderedIds: string[]) {
    if (!selectedTenant || sort !== "priority") return;

    const currentIds = items.map((row) => row.id).join(",");
    const nextIds = orderedIds.join(",");
    if (currentIds === nextIds) return;

    const previous = items;
    const nextItems = reorderWishListItemIds(items, orderedIds);
    setItems(nextItems);
    setActionError(null);
    try {
      await reorderWishListItems(selectedTenant, orderedIds);
    } catch {
      setItems(previous);
      setActionError("action_failed");
    }
  }

  function handleSaved(saved: WishListItem) {
    setItems((current) => upsertWishListItem(current, saved, sort));
    setActionError(null);
  }

  function handleExecuted(executed: WishListItem) {
    if (filter === "active") {
      setItems((current) => removeWishListItem(current, executed.id));
    } else {
      setItems((current) => upsertWishListItem(current, executed, sort));
    }
    setActionError(null);
  }

  if (!selectedTenant) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="inline-flex rounded-lg border border-gray-200 bg-white p-1">
          <button
            type="button"
            onClick={() => setFilter("active")}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              filter === "active"
                ? "bg-gray-900 text-white"
                : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            {t("wishListFilterActive")}
          </button>
          <button
            type="button"
            onClick={() => setFilter("executed")}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              filter === "executed"
                ? "bg-gray-900 text-white"
                : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            {t("wishListFilterExecuted")}
          </button>
        </div>

        <button
          type="button"
          onClick={() => {
            setEditing(null);
            setFormOpen(true);
          }}
          className="rounded-lg bg-gray-900 px-3 py-2 text-sm font-medium text-white"
        >
          {t("wishListAdd")}
        </button>
      </div>

      {filter === "active" ? (
        <WishListActiveList
          items={items}
          loading={loading}
          loadError={loadError}
          actionError={actionError}
          busyId={busyId}
          sort={sort}
          onSortChange={setSort}
          onRetry={() => void load()}
          onCreate={() => {
            setEditing(null);
            setFormOpen(true);
          }}
          onReorder={(orderedIds) => void handleReorder(orderedIds)}
          onEdit={(item) => {
            setEditing(item);
            setFormOpen(true);
          }}
          onDelete={(item) => void handleDelete(item)}
          onExecute={(item) => setExecuting(item)}
        />
      ) : (
        <WishListExecutedList
          items={items}
          loading={loading}
          loadError={loadError}
          onRetry={() => void load()}
        />
      )}

      {formOpen ? (
        <WishListItemForm
          tenant={selectedTenant}
          item={editing}
          onClose={() => {
            setFormOpen(false);
            setEditing(null);
          }}
          onSaved={handleSaved}
        />
      ) : null}

      {executing ? (
        <WishListExecuteDialog
          tenant={selectedTenant}
          item={executing}
          onClose={() => setExecuting(null)}
          onExecuted={handleExecuted}
        />
      ) : null}
    </div>
  );
}
