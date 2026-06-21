"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { useTenant } from "@/components/TenantProvider";
import {
  createCategory,
  deleteCategory,
  fetchCategories,
  updateCategory,
} from "@/lib/categories/client";
import type { CategoryNode } from "@/lib/categories/types";
import { CategoryRowAction } from "@/components/categories/CategoryRowAction";
import { DeleteCategoryDialog } from "@/components/categories/DeleteCategoryDialog";
import { EditableCategoryName } from "@/components/categories/EditableCategoryName";
import { InlineCategoryDraft } from "@/components/categories/InlineCategoryDraft";

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

export function CategoryManager() {
  const { t } = useLanguage();
  const { selectedTenant } = useTenant();
  const [nodes, setNodes] = useState<CategoryNode[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftAdd, setDraftAdd] = useState<DraftAdd | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CategoryNode | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadInitial = useCallback(async () => {
    if (!selectedTenant) return;
    setInitialLoading(true);
    setError(null);
    try {
      const data = await fetchCategories(selectedTenant);
      setNodes(data.nodes);
    } catch {
      setError(t("errorGeneric"));
    } finally {
      setInitialLoading(false);
    }
  }, [selectedTenant, t]);

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
    setNodes((current) => removeNodeAndChildren(current, target.id));
    setActionError(null);
    try {
      await deleteCategory(target.id, selectedTenant, transferToId);
    } catch {
      setNodes(previous);
      setActionError(t("deleteFailed"));
      setDeleteTarget(target);
    }
  }

  if (!selectedTenant) {
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

      {l1Nodes.map((l1) => {
        const l2Children = childrenByParent.get(l1.id) ?? [];
        const unknown = isUnknown(l1);

        return (
          <section
            key={l1.id}
            className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
          >
            <div className="flex items-center gap-2">
              <EditableCategoryName
                name={l1.name_ja}
                variant="l1"
                isEditing={editingId === l1.id}
                isSaving={savingId === l1.id}
                showSaved={savedId === l1.id}
                onStartEdit={() => startEdit(l1.id)}
                onSave={(name) => handleRename(l1, name)}
                onCancel={cancelEdit}
              />
              <CategoryRowAction
                deletable={l1.deletable}
                isUnknown={unknown}
                onDelete={() => setDeleteTarget(l1)}
              />
            </div>

            <ul className="mt-3 space-y-1 border-t border-gray-100 pt-3">
              {l2Children.map((l2) => (
                <li key={l2.id} className="flex items-center gap-2 pl-2">
                  <EditableCategoryName
                    name={l2.name_ja}
                    variant="l2"
                    isEditing={editingId === l2.id}
                    isSaving={savingId === l2.id}
                    showSaved={savedId === l2.id}
                    onStartEdit={() => startEdit(l2.id)}
                    onSave={(name) => handleRename(l2, name)}
                    onCancel={cancelEdit}
                  />
                  <CategoryRowAction
                    deletable={l2.deletable}
                    isUnknown={false}
                    onDelete={() => setDeleteTarget(l2)}
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
          </section>
        );
      })}

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
