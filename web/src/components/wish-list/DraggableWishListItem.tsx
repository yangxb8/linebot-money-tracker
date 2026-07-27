"use client";

import { useLanguage } from "@/components/LanguageProvider";
import type { WishListItem } from "@/lib/wish-list/types";
import { useLongPressDrag } from "@/components/categories/useLongPressDrag";

type Props = {
  item: WishListItem;
  busy: boolean;
  canDrag: boolean;
  isDragging: boolean;
  isDimmed: boolean;
  dragSessionActive: boolean;
  dropActive: boolean;
  onEdit: () => void;
  onDelete: () => void;
  onExecute: () => void;
  onDragStart: (position: { x: number; y: number }) => void;
  onDragMove: (position: { x: number; y: number }) => void;
  onDragEnd: (position: { x: number; y: number }) => void;
};

function formatAmount(amount: number) {
  return new Intl.NumberFormat("ja-JP", {
    style: "currency",
    currency: "JPY",
    maximumFractionDigits: 0,
  }).format(amount);
}

function stopPointerPropagation(event: React.PointerEvent | React.MouseEvent) {
  event.stopPropagation();
}

export function DraggableWishListItem({
  item,
  busy,
  canDrag,
  isDragging,
  isDimmed,
  dragSessionActive,
  dropActive,
  onEdit,
  onDelete,
  onExecute,
  onDragStart,
  onDragMove,
  onDragEnd,
}: Props) {
  const { t } = useLanguage();

  const { dragHandlers } = useLongPressDrag({
    enabled: canDrag && !busy,
    onTap: onEdit,
    onDragStart,
    onDragMove,
    onDragEnd,
  });

  return (
    <li
      data-drop-zone={`wish:${item.id}`}
      className={`rounded-xl border border-gray-100 bg-white shadow-sm transition-colors ${
        dropActive ? "ring-2 ring-blue-400 ring-inset bg-blue-50" : ""
      } ${isDimmed ? "opacity-40" : ""} ${isDragging ? "opacity-60" : ""}`}
    >
      <div
        role="button"
        tabIndex={busy ? -1 : 0}
        onKeyDown={(event) => {
          if (busy) return;
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onEdit();
          }
        }}
        onClick={canDrag || busy ? undefined : onEdit}
        className={`p-4 text-left outline-none ${
          dragSessionActive
            ? "touch-none"
            : canDrag && !busy
              ? "touch-pan-y cursor-pointer"
              : "cursor-pointer"
        }`}
        {...(canDrag && !busy ? dragHandlers : {})}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="break-words text-sm font-semibold text-gray-900">
              {item.name}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              {item.category_name ?? t("periodicCategory")}
            </p>
          </div>
          <p className="shrink-0 text-sm font-semibold text-gray-900">
            {formatAmount(item.amount)}
          </p>
        </div>

        {item.product_url ? (
          <a
            href={item.product_url}
            target="_blank"
            rel="noreferrer"
            onPointerDown={stopPointerPropagation}
            onClick={stopPointerPropagation}
            className="mt-2 inline-block max-w-full truncate text-xs text-gray-600 underline"
          >
            {item.product_url}
          </a>
        ) : null}
      </div>

      <div className="flex items-center justify-end gap-2 border-t border-gray-100 px-4 py-3">
        <button
          type="button"
          disabled={busy}
          onPointerDown={stopPointerPropagation}
          onClick={(event) => {
            stopPointerPropagation(event);
            onDelete();
          }}
          className="text-xs text-red-600 underline disabled:opacity-40"
        >
          {t("delete")}
        </button>
        <button
          type="button"
          disabled={busy}
          onPointerDown={stopPointerPropagation}
          onClick={(event) => {
            stopPointerPropagation(event);
            onExecute();
          }}
          className="rounded-lg bg-gray-900 px-3 py-1 text-xs font-medium text-white disabled:opacity-40"
        >
          {t("wishListExecute")}
        </button>
      </div>
    </li>
  );
}
