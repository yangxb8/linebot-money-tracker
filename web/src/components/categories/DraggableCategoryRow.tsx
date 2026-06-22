"use client";

import type { CategoryNode } from "@/lib/categories/types";
import { EditableCategoryName } from "@/components/categories/EditableCategoryName";
import { CategoryRowAction } from "@/components/categories/CategoryRowAction";
import { useLongPressDrag } from "@/components/categories/useLongPressDrag";

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
  onDragStart,
  onDragMove,
  onDragEnd,
}: Props) {
  const { dragHandlers } = useLongPressDrag({
    enabled: canDrag && !isEditing,
    onTap: onStartEdit,
    onDragStart: (position) => onDragStart(node, position),
    onDragMove,
    onDragEnd: (position) => onDragEnd(node, position),
  });

  return (
    <div
      className={`flex items-center gap-2 select-none ${
        dragSessionActive ? "touch-none" : canDrag && !isEditing ? "touch-pan-y" : ""
      } ${isDimmed ? "opacity-40" : ""} ${isDragging ? "opacity-60" : ""}`}
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
      <CategoryRowAction
        deletable={node.deletable}
        isUnknown={isUnknown}
        onDelete={onDelete}
      />
    </div>
  );
}
