"use client";

import type { CategoryNode } from "@/lib/categories/types";
import { EditableCategoryName } from "@/components/categories/EditableCategoryName";
import { CategoryRowAction } from "@/components/categories/CategoryRowAction";
import { useLongPressDrag } from "@/components/categories/useLongPressDrag";
import { useLanguage } from "@/components/LanguageProvider";

type Props = {
  node: CategoryNode;
  variant: "l1" | "l2";
  isUnknown: boolean;
  canDrag: boolean;
  isEditing: boolean;
  isSaving: boolean;
  showSaved: boolean;
  isDragging: boolean;
  isDimmed: boolean;
  dragSessionActive: boolean;
  onStartEdit: () => void;
  onSave: (name: string) => Promise<void>;
  onCancelEdit: () => void;
  onDelete: () => void;
  onTogglePaceWarning: (enabled: boolean) => void;
  onDragStart: (node: CategoryNode, position: { x: number; y: number }) => void;
  onDragMove: (position: { x: number; y: number }) => void;
  onDragEnd: (node: CategoryNode, position: { x: number; y: number }) => void;
};

export function DraggableCategoryRow({
  node,
  variant,
  isUnknown,
  canDrag,
  isEditing,
  isSaving,
  showSaved,
  isDragging,
  isDimmed,
  dragSessionActive,
  onStartEdit,
  onSave,
  onCancelEdit,
  onDelete,
  onTogglePaceWarning,
  onDragStart,
  onDragMove,
  onDragEnd,
}: Props) {
  const { t } = useLanguage();
  const { dragHandlers } = useLongPressDrag({
    enabled: canDrag && !isEditing,
    onTap: onStartEdit,
    onDragStart: (position) => onDragStart(node, position),
    onDragMove,
    onDragEnd: (position) => onDragEnd(node, position),
  });

  const checkboxId = `pace-warning-${node.id}`;

  return (
    <div
      className={`flex items-center gap-2 select-none ${
        dragSessionActive ? "touch-none" : canDrag && !isEditing ? "touch-pan-y" : ""
      } ${isDimmed ? "opacity-40" : ""} ${isDragging ? "opacity-60" : ""}`}
    >
      <div
        className="min-w-0 flex-1"
        {...(canDrag && !isEditing ? dragHandlers : {})}
      >
        <EditableCategoryName
          name={node.name_ja}
          variant={variant}
          isEditing={isEditing}
          isSaving={isSaving}
          showSaved={showSaved}
          onStartEdit={onStartEdit}
          onSave={onSave}
          onCancel={onCancelEdit}
          tapToEdit={!canDrag}
        />
      </div>
      <label
        htmlFor={checkboxId}
        className="flex shrink-0 items-center gap-1.5 rounded-md border border-amber-200 bg-amber-50 px-1.5 py-1 text-xs text-amber-900"
        title={t("paceWarningHint")}
        onPointerDown={(event) => event.stopPropagation()}
      >
        <input
          id={checkboxId}
          type="checkbox"
          checked={node.pace_warning_enabled}
          onChange={(event) => onTogglePaceWarning(event.target.checked)}
          className="h-3.5 w-3.5 rounded border-amber-400"
          aria-label={t("paceWarningLabel")}
        />
        <span className="whitespace-nowrap font-medium">{t("paceWarningShort")}</span>
      </label>
      <CategoryRowAction
        deletable={node.deletable}
        isUnknown={isUnknown}
        onDelete={onDelete}
      />
    </div>
  );
}
