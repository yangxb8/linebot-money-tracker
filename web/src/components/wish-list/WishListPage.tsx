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
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<WishListItem | null>(null);
  const [executing, setExecuting] = useState<WishListItem | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!selectedTenant) return;
    setLoading(true);
    setError(null);
    try {
      const rows = await fetchWishListItems(selectedTenant, filter, sort);
      setItems(rows);
    } catch {
      setError("fetch_failed");
    } finally {
      setLoading(false);
    }
  }, [filter, selectedTenant, sort]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleDelete(item: WishListItem) {
    if (!window.confirm(t("wishListDeleteConfirm"))) return;
    setBusyId(item.id);
    try {
      await deleteWishListItem(item.id);
      await load();
    } catch {
      setError("action_failed");
    } finally {
      setBusyId(null);
    }
  }

  async function handleMove(item: WishListItem, direction: "up" | "down") {
    if (!selectedTenant || sort !== "priority") return;
    const index = items.findIndex((candidate) => candidate.id === item.id);
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (index < 0 || targetIndex < 0 || targetIndex >= items.length) return;

    const nextItems = [...items];
    [nextItems[index], nextItems[targetIndex]] = [
      nextItems[targetIndex],
      nextItems[index],
    ];
    setItems(nextItems);
    setBusyId(item.id);
    try {
      await reorderWishListItems(
        selectedTenant,
        nextItems.map((row) => row.id),
      );
      await load();
    } catch {
      setError("action_failed");
      await load();
    } finally {
      setBusyId(null);
    }
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
          error={error}
          busyId={busyId}
          sort={sort}
          onSortChange={setSort}
          onRetry={() => void load()}
          onCreate={() => {
            setEditing(null);
            setFormOpen(true);
          }}
          onMove={(item, direction) => void handleMove(item, direction)}
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
          error={error}
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
          onSaved={() => void load()}
        />
      ) : null}

      {executing ? (
        <WishListExecuteDialog
          tenant={selectedTenant}
          item={executing}
          onClose={() => setExecuting(null)}
          onExecuted={() => void load()}
        />
      ) : null}
    </div>
  );
}
