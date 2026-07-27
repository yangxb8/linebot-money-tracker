"use client";

import { useRef, useState } from "react";
import { CategoryDragOverlay } from "@/components/categories/CategoryDragUI";
import { useLanguage } from "@/components/LanguageProvider";
import { DraggableWishListItem } from "@/components/wish-list/DraggableWishListItem";
import { findWishListDropTarget } from "@/components/categories/useLongPressDrag";
import type {
  WishListItem,
  WishListSort,
} from "@/lib/wish-list/types";

type Props = {
  items: WishListItem[];
  loading: boolean;
  loadError: string | null;
  actionError: string | null;
  busyId: string | null;
  sort: WishListSort;
  onSortChange: (sort: WishListSort) => void;
  onRetry: () => void;
  onCreate: () => void;
  onReorder: (orderedIds: string[]) => void;
  onEdit: (item: WishListItem) => void;
  onDelete: (item: WishListItem) => void;
  onExecute: (item: WishListItem) => void;
};

export function WishListActiveList({
  items,
  loading,
  loadError,
  actionError,
  busyId,
  sort,
  onSortChange,
  onRetry,
  onCreate,
  onReorder,
  onEdit,
  onDelete,
  onExecute,
}: Props) {
  const { t } = useLanguage();
  const [draggingItem, setDraggingItem] = useState<WishListItem | null>(null);
  const [dragPosition, setDragPosition] = useState<{ x: number; y: number } | null>(
    null,
  );
  const [activeDropTargetId, setActiveDropTargetId] = useState<string | null>(null);
  const dragPositionRef = useRef(dragPosition);
  dragPositionRef.current = dragPosition;

  const canDrag = sort === "priority";
  const dragSessionActive = Boolean(draggingItem);

  function updateDropHighlight(position: { x: number; y: number }) {
    dragPositionRef.current = position;
    setDragPosition(position);
    setActiveDropTargetId(findWishListDropTarget(position));
  }

  function clearDrag() {
    setDraggingItem(null);
    setDragPosition(null);
    setActiveDropTargetId(null);
  }

  function handleDragEnd(item: WishListItem, position: { x: number; y: number }) {
    const targetId = findWishListDropTarget(position);
    clearDrag();

    if (!targetId || targetId === item.id) return;

    const fromIndex = items.findIndex((row) => row.id === item.id);
    const toIndex = items.findIndex((row) => row.id === targetId);
    if (fromIndex < 0 || toIndex < 0) return;

    const nextItems = [...items];
    const [moved] = nextItems.splice(fromIndex, 1);
    nextItems.splice(toIndex, 0, moved);
    onReorder(nextItems.map((row) => row.id));
  }

  if (loading) {
    return (
      <p className="py-12 text-center text-sm text-gray-500">{t("loading")}</p>
    );
  }

  if (loadError) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-gray-600">{t("errorGeneric")}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 text-sm font-medium text-gray-900 underline"
        >
          {t("retry")}
        </button>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-200 bg-white p-8 text-center">
        <p className="text-sm text-gray-600">{t("wishListEmpty")}</p>
        <button
          type="button"
          onClick={onCreate}
          className="mt-4 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white"
        >
          {t("wishListAdd")}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {actionError ? (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {t("errorGeneric")}
        </p>
      ) : null}

      <div className="flex items-center justify-between gap-3">
        <label className="text-sm font-medium text-gray-700">
          {t("expenseSortBy")}
        </label>
        <select
          value={sort}
          onChange={(event) => onSortChange(event.target.value as WishListSort)}
          className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700"
        >
          <option value="priority">{t("wishListSortPriority")}</option>
          <option value="created">{t("wishListSortCreated")}</option>
          <option value="price">{t("wishListSortPrice")}</option>
        </select>
      </div>

      {canDrag ? (
        <p className="text-xs text-gray-500">{t("wishListDragHint")}</p>
      ) : null}

      <ul className={`space-y-3 ${dragSessionActive ? "touch-none" : ""}`}>
        {items.map((item) => {
          const busy = busyId === item.id;
          return (
            <DraggableWishListItem
              key={item.id}
              item={item}
              busy={busy}
              canDrag={canDrag}
              isDragging={draggingItem?.id === item.id}
              isDimmed={Boolean(draggingItem && draggingItem.id !== item.id)}
              dragSessionActive={dragSessionActive}
              dropActive={activeDropTargetId === item.id}
              onEdit={() => onEdit(item)}
              onDelete={() => onDelete(item)}
              onExecute={() => onExecute(item)}
              onDragStart={(position) => {
                setDraggingItem(item);
                setDragPosition(position);
              }}
              onDragMove={updateDropHighlight}
              onDragEnd={(position) => handleDragEnd(item, position)}
            />
          );
        })}
      </ul>

      {draggingItem && dragPosition ? (
        <CategoryDragOverlay
          label={draggingItem.name}
          x={dragPosition.x}
          y={dragPosition.y}
        />
      ) : null}
    </div>
  );
}
