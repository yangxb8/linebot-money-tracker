"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { useTenant } from "@/components/TenantProvider";
import {
  createCategory,
  deleteCategory,
  fetchCategories,
  moveCategory,
  updateCategory,
} from "@/lib/categories/client";
import type { CategoryNode } from "@/lib/categories/types";
import { DeleteCategoryDialog } from "@/components/categories/DeleteCategoryDialog";
import { InlineCategoryDraft } from "@/components/categories/InlineCategoryDraft";
import {
  CategoryDragOverlay,
  CategoryDropZone,
  PromoteDropZone,
} from "@/components/categories/CategoryDragUI";
import { DraggableCategoryRow } from "@/components/categories/DraggableCategoryRow";
import { findDropZone } from "@/components/categories/useLongPressDrag";

const UNKNOWN_CODE = "unknown";
type DraftAdd = { type: "l1" } | { type: "l2"; parentId: string };

function isUnknown(node: CategoryNode) {
  return node.code === UNKNOWN_CODE;
}

function patchNode(
  nodes: CategoryNode[],
  id: string,
  patch: Partial<CategoryNode>,
): CategoryNode[] {
  return nodes.map((node) => (node.id === id ? { ...node, ...patch } : node));
}

function removeNodeAndChildren(nodes: CategoryNode[], id: string): CategoryNode[] {
  return nodes.filter((node) => node.id !== id && node.parent_id !== id);
}

function recomputeDeletable(nodes: CategoryNode[]): CategoryNode[] {
  const l1Count = nodes.filter((n) => n.level === 1).length;
  return nodes.map((node) => ({
    ...node,
    deletable:
      node.code !== UNKNOWN_CODE && !(node.level === 1 && l1Count <= 1),
  }));
}

function canDragNode(
  node: CategoryNode,
  childrenByParent: Map<string, CategoryNode[]>,
): boolean {
  if (isUnknown(node)) return false;
  if (node.level === 1) {
    return (childrenByParent.get(node.id) ?? []).length === 0;
  }
  return true;
}

export function CategoryManager() {
  const { t } = useLanguage();
  const { selectedTenant, isTenantReady } = useTenant();
  const [nodes, setNodes] = useState<CategoryNode[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftAdd, setDraftAdd] = useState<DraftAdd | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CategoryNode | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [draggingNode, setDraggingNode] = useState<CategoryNode | null>(null);
  const [dragPosition, setDragPosition] = useState<{ x: number; y: number } | null>(
    null,
  );
  const [activeDropZone, setActiveDropZone] = useState<string | null>(null);
  const dragPositionRef = useRef(dragPosition);
  dragPositionRef.current = dragPosition;
  const loadSeqRef = useRef(0);

  const loadInitial = useCallback(async () => {
    if (!selectedTenant || !isTenantReady) return;
    const seq = ++loadSeqRef.current;
    setInitialLoading(true);
    setError(null);
    setNodes([]);
    setDraftAdd(null);
    setEditingId(null);
    try {
      const data = await fetchCategories(selectedTenant);
      if (seq !== loadSeqRef.current) return;
      setNodes(data.nodes);
    } catch {
      if (seq !== loadSeqRef.current) return;
      setError(t("errorGeneric"));
    } finally {
      if (seq === loadSeqRef.current) {
        setInitialLoading(false);
      }
    }
  }, [selectedTenant, isTenantReady, t]);

  useEffect(() => {
    void loadInitial();
  }, [loadInitial]);

  useEffect(() => {
    if (!savedId) return;
    const timer = window.setTimeout(() => setSavedId(null), 1000);
    return () => window.clearTimeout(timer);
  }, [savedId]);

  const l1Nodes = useMemo(
    () =>
      nodes
        .filter((n) => n.level === 1)
        .sort((a, b) => a.sort_order - b.sort_order),
    [nodes],
  );

  const childrenByParent = useMemo(() => {
    const map = new Map<string, CategoryNode[]>();
    for (const node of nodes) {
      if (node.level === 2 && node.parent_id) {
        const list = map.get(node.parent_id) ?? [];
        list.push(node);
        map.set(node.parent_id, list);
      }
    }
    for (const [, list] of map) {
      list.sort((a, b) => a.sort_order - b.sort_order);
    }
    return map;
  }, [nodes]);

  function startEdit(id: string) {
    if (draggingNode) return;
    setDraftAdd(null);
    setEditingId(id);
    setActionError(null);
  }

  function cancelEdit() {
    setEditingId(null);
  }

  async function handleRename(node: CategoryNode, name: string) {
    const previous = node.name_ja;
    setEditingId(null);
    setNodes((current) => patchNode(current, node.id, { name_ja: name }));
    setSavingId(node.id);
    setActionError(null);
    try {
      await updateCategory(node.id, { name_ja: name });
      setSavedId(node.id);
    } catch {
      setNodes((current) => patchNode(current, node.id, { name_ja: previous }));
      setActionError(t("saveFailed"));
    } finally {
      setSavingId(null);
    }
  }

  async function handleCreateL1(name: string) {
    if (!selectedTenant) return;
    setDraftAdd(null);
    setSavingId("draft-l1");
    setActionError(null);
    try {
      const created = await createCategory(selectedTenant, { level: 1, name_ja: name });
      setNodes((current) => [...current, created]);
      setSavedId(created.id);
    } catch {
      setActionError(t("saveFailed"));
      setDraftAdd({ type: "l1" });
    } finally {
      setSavingId(null);
    }
  }

  async function handleCreateL2(parentId: string, name: string) {
    if (!selectedTenant) return;
    setDraftAdd(null);
    setSavingId("draft-l2");
    setActionError(null);
    try {
      const created = await createCategory(selectedTenant, {
        level: 2,
        parent_id: parentId,
        name_ja: name,
      });
      setNodes((current) => [...current, created]);
      setSavedId(created.id);
    } catch {
      setActionError(t("saveFailed"));
      setDraftAdd({ type: "l2", parentId });
    } finally {
      setSavingId(null);
    }
  }

  async function handleDelete(transferToId?: string) {
    if (!selectedTenant || !deleteTarget) return;
    const target = deleteTarget;
    const previous = nodes;
    setDeleteTarget(null);
    setNodes((current) => recomputeDeletable(removeNodeAndChildren(current, target.id)));
    setActionError(null);
    try {
      await deleteCategory(target.id, selectedTenant, transferToId);
    } catch {
      setNodes(previous);
      setActionError(t("deleteFailed"));
      setDeleteTarget(target);
    }
  }

  function highlightDropZoneAt(position: { x: number; y: number }) {
    const zone = findDropZone(position);
    if (!zone) {
      setActiveDropZone(null);
      return;
    }
    setActiveDropZone(zone.type === "promote" ? "promote" : `l1:${zone.id}`);
  }

  function updateDropHighlight(position: { x: number; y: number }) {
    dragPositionRef.current = position;
    setDragPosition(position);
    highlightDropZoneAt(position);
  }

  function clearDrag() {
    setDraggingNode(null);
    setDragPosition(null);
    setActiveDropZone(null);
  }

  async function handleDragEnd(node: CategoryNode, position: { x: number; y: number }) {
    const zone = findDropZone(position);
    clearDrag();

    if (!zone) return;

    let moveBody: { level: 1 | 2; parent_id?: string | null } | null = null;

    if (node.level === 2 && zone.type === "promote") {
      moveBody = { level: 1, parent_id: null };
    } else if (node.level === 2 && zone.type === "l1") {
      if (zone.id === node.parent_id) return;
      const targetL1 = nodes.find((n) => n.id === zone.id);
      if (!targetL1 || isUnknown(targetL1)) return;
      moveBody = { level: 2, parent_id: zone.id };
    } else if (node.level === 1 && zone.type === "l1") {
      if (zone.id === node.id) return;
      const targetL1 = nodes.find((n) => n.id === zone.id);
      if (!targetL1 || isUnknown(targetL1)) return;
      if ((childrenByParent.get(node.id) ?? []).length > 0) return;
      moveBody = { level: 2, parent_id: zone.id };
    }

    if (!moveBody) return;

    const previous = nodes;
    const optimistic = recomputeDeletable(
      nodes.map((n) => {
        if (n.id !== node.id) return n;
        return {
          ...n,
          level: moveBody.level,
          parent_id: moveBody.level === 2 ? (moveBody.parent_id ?? null) : null,
        };
      }),
    );
    setNodes(optimistic);
    setSavingId(node.id);
    setActionError(null);

    try {
      await moveCategory(node.id, moveBody);
      setSavedId(node.id);
    } catch {
      setNodes(previous);
      setActionError(t("moveFailed"));
    } finally {
      setSavingId(null);
    }
  }

  const dragSessionActive = Boolean(draggingNode);

  if (!selectedTenant || !isTenantReady) {
    return (
      <p className="text-center text-sm text-gray-500 py-16">{t("loading")}</p>
    );
  }

  if (initialLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        {[1, 2, 3].map((key) => (
          <div key={key} className="h-28 rounded-xl bg-gray-200" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-3 text-center">
        <p className="text-sm text-red-600">{error}</p>
        <button
          type="button"
          onClick={() => void loadInitial()}
          className="text-sm underline text-gray-600"
        >
          {t("retry")}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {actionError ? (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {actionError}
        </p>
      ) : null}

      <p className="text-xs text-gray-500">{t("dragHint")}</p>

      {l1Nodes.map((l1) => {
        const l2Children = childrenByParent.get(l1.id) ?? [];
        const unknown = isUnknown(l1);
        const zoneKey = `l1:${l1.id}`;

        return (
          <CategoryDropZone
            key={l1.id}
            zone={zoneKey}
            active={activeDropZone === zoneKey}
            className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
          >
            <DraggableCategoryRow
              node={l1}
              variant="l1"
              isUnknown={unknown}
              canDrag={canDragNode(l1, childrenByParent)}
              isEditing={editingId === l1.id}
              isSaving={savingId === l1.id}
              showSaved={savedId === l1.id}
              isDragging={draggingNode?.id === l1.id}
              isDimmed={Boolean(draggingNode && draggingNode.id !== l1.id)}
              dragSessionActive={dragSessionActive}
              onStartEdit={() => startEdit(l1.id)}
              onSave={(name) => handleRename(l1, name)}
              onCancelEdit={cancelEdit}
              onDelete={() => setDeleteTarget(l1)}
              onDragStart={(n, position) => {
                setEditingId(null);
                setDraggingNode(n);
                setDragPosition(position);
              }}
              onDragMove={updateDropHighlight}
              onDragEnd={handleDragEnd}
            />

            <div className="mt-3 min-h-[2rem] border-t border-gray-100 pt-3">
              <ul className="space-y-1">
                {l2Children.map((l2) => (
                  <li key={l2.id} className="pl-2">
                    <DraggableCategoryRow
                      node={l2}
                      variant="l2"
                      isUnknown={false}
                      canDrag={canDragNode(l2, childrenByParent)}
                      isEditing={editingId === l2.id}
                      isSaving={savingId === l2.id}
                      showSaved={savedId === l2.id}
                      isDragging={draggingNode?.id === l2.id}
                      isDimmed={Boolean(draggingNode && draggingNode.id !== l2.id)}
                      dragSessionActive={dragSessionActive}
                      onStartEdit={() => startEdit(l2.id)}
                      onSave={(name) => handleRename(l2, name)}
                      onCancelEdit={cancelEdit}
                      onDelete={() => setDeleteTarget(l2)}
                      onDragStart={(n, position) => {
                        setEditingId(null);
                        setDraggingNode(n);
                        setDragPosition(position);
                      }}
                      onDragMove={updateDropHighlight}
                      onDragEnd={handleDragEnd}
                    />
                  </li>
                ))}

                {draftAdd?.type === "l2" && draftAdd.parentId === l1.id ? (
                  <li className="pl-2">
                    <InlineCategoryDraft
                      variant="l2"
                      onCreate={(name) => handleCreateL2(l1.id, name)}
                      onCancel={() => setDraftAdd(null)}
                    />
                  </li>
                ) : null}
              </ul>
            </div>

            {!unknown && draftAdd?.type !== "l2" ? (
              <button
                type="button"
                className="mt-3 text-sm text-blue-600 hover:underline"
                onClick={() => {
                  setEditingId(null);
                  setDraftAdd({ type: "l2", parentId: l1.id });
                }}
              >
                + {t("addL2")}
              </button>
            ) : null}
          </CategoryDropZone>
        );
      })}

      {draggingNode?.level === 2 ? (
        <PromoteDropZone active={activeDropZone === "promote"} />
      ) : null}

      <div className="rounded-xl border border-dashed border-gray-300 bg-white p-4">
        {draftAdd?.type === "l1" ? (
          <InlineCategoryDraft
            variant="l1"
            onCreate={handleCreateL1}
            onCancel={() => setDraftAdd(null)}
          />
        ) : (
          <button
            type="button"
            className="w-full text-left text-sm font-medium text-blue-600 hover:underline"
            onClick={() => {
              setEditingId(null);
              setDraftAdd({ type: "l1" });
            }}
          >
            + {t("addL1")}
          </button>
        )}
      </div>

      {draggingNode && dragPosition ? (
        <CategoryDragOverlay
          label={draggingNode.name_ja}
          x={dragPosition.x}
          y={dragPosition.y}
        />
      ) : null}

      {deleteTarget ? (
        <DeleteCategoryDialog
          target={deleteTarget}
          candidates={nodes.filter((n) => n.id !== deleteTarget.id)}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={(transferId) => void handleDelete(transferId)}
        />
      ) : null}
    </div>
  );
}
