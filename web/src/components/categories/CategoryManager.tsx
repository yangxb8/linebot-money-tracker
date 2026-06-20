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
import { DeleteCategoryDialog } from "@/components/categories/DeleteCategoryDialog";

export function CategoryManager() {
  const { t } = useLanguage();
  const { selectedTenant } = useTenant();
  const [nodes, setNodes] = useState<CategoryNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [newL1Name, setNewL1Name] = useState("");
  const [newL2ParentId, setNewL2ParentId] = useState<string | null>(null);
  const [newL2Name, setNewL2Name] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<CategoryNode | null>(null);

  const load = useCallback(async () => {
    if (!selectedTenant) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCategories(selectedTenant);
      setNodes(data.nodes);
    } catch {
      setError(t("errorGeneric"));
    } finally {
      setLoading(false);
    }
  }, [selectedTenant, t]);

  useEffect(() => {
    void load();
  }, [load]);

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

  async function handleRename(node: CategoryNode) {
    const name = editName.trim();
    if (!name || name === node.name_ja) {
      setEditingId(null);
      return;
    }
    await updateCategory(node.id, { name_ja: name });
    setEditingId(null);
    await load();
  }

  async function handleReorder(node: CategoryNode, direction: "up" | "down") {
    const siblings =
      node.level === 1
        ? l1Nodes
        : (childrenByParent.get(node.parent_id ?? "") ?? []);
    const index = siblings.findIndex((s) => s.id === node.id);
    const swapIndex = direction === "up" ? index - 1 : index + 1;
    if (swapIndex < 0 || swapIndex >= siblings.length) return;
    const other = siblings[swapIndex];
    await Promise.all([
      updateCategory(node.id, { sort_order: other.sort_order }),
      updateCategory(other.id, { sort_order: node.sort_order }),
    ]);
    await load();
  }

  async function handleCreateL1() {
    if (!selectedTenant || !newL1Name.trim()) return;
    await createCategory(selectedTenant, {
      level: 1,
      name_ja: newL1Name.trim(),
    });
    setNewL1Name("");
    await load();
  }

  async function handleCreateL2() {
    if (!selectedTenant || !newL2ParentId || !newL2Name.trim()) return;
    await createCategory(selectedTenant, {
      level: 2,
      parent_id: newL2ParentId,
      name_ja: newL2Name.trim(),
    });
    setNewL2Name("");
    setNewL2ParentId(null);
    await load();
  }

  async function handleDelete(transferToId?: string) {
    if (!selectedTenant || !deleteTarget) return;
    await deleteCategory(deleteTarget.id, selectedTenant, transferToId);
    setDeleteTarget(null);
    await load();
  }

  if (!selectedTenant) {
    return (
      <p className="text-center text-sm text-gray-500 py-16">{t("loading")}</p>
    );
  }

  if (loading) {
    return (
      <p className="text-center text-sm text-gray-500 py-16">{t("loading")}</p>
    );
  }

  if (error) {
    return (
      <div className="space-y-3 text-center">
        <p className="text-sm text-red-600">{error}</p>
        <button
          type="button"
          onClick={() => void load()}
          className="text-sm underline text-gray-600"
        >
          {t("retry")}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {l1Nodes.map((l1) => (
        <section
          key={l1.id}
          className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
        >
          <div className="flex items-start gap-2">
            {editingId === l1.id ? (
              <input
                className="flex-1 rounded border border-gray-200 px-2 py-1 text-sm"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void handleRename(l1);
                  if (e.key === "Escape") setEditingId(null);
                }}
                autoFocus
              />
            ) : (
              <h2 className="flex-1 text-base font-semibold text-gray-900">
                {l1.name_ja}
              </h2>
            )}
            <div className="flex shrink-0 gap-1">
              <button
                type="button"
                className="text-xs text-gray-500"
                onClick={() => void handleReorder(l1, "up")}
              >
                ↑
              </button>
              <button
                type="button"
                className="text-xs text-gray-500"
                onClick={() => void handleReorder(l1, "down")}
              >
                ↓
              </button>
              <button
                type="button"
                className="text-xs text-gray-600 underline"
                onClick={() => {
                  setEditingId(l1.id);
                  setEditName(l1.name_ja);
                }}
              >
                {t("edit")}
              </button>
              {l1.deletable ? (
                <button
                  type="button"
                  className="text-xs text-red-600 underline"
                  onClick={() => setDeleteTarget(l1)}
                >
                  {t("delete")}
                </button>
              ) : null}
            </div>
          </div>

          <ul className="mt-3 space-y-2 border-t border-gray-100 pt-3">
            {(childrenByParent.get(l1.id) ?? []).map((l2) => (
              <li key={l2.id} className="flex items-center gap-2 pl-2">
                {editingId === l2.id ? (
                  <input
                    className="flex-1 rounded border border-gray-200 px-2 py-1 text-sm"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void handleRename(l2);
                      if (e.key === "Escape") setEditingId(null);
                    }}
                    autoFocus
                  />
                ) : (
                  <span className="flex-1 text-sm text-gray-700">{l2.name_ja}</span>
                )}
                <div className="flex shrink-0 gap-1">
                  <button
                    type="button"
                    className="text-xs text-gray-500"
                    onClick={() => void handleReorder(l2, "up")}
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    className="text-xs text-gray-500"
                    onClick={() => void handleReorder(l2, "down")}
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    className="text-xs text-gray-600 underline"
                    onClick={() => {
                      setEditingId(l2.id);
                      setEditName(l2.name_ja);
                    }}
                  >
                    {t("edit")}
                  </button>
                  {l2.deletable ? (
                    <button
                      type="button"
                      className="text-xs text-red-600 underline"
                      onClick={() => setDeleteTarget(l2)}
                    >
                      {t("delete")}
                    </button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>

          <button
            type="button"
            className="mt-3 text-xs text-blue-600 underline"
            onClick={() => {
              setNewL2ParentId(l1.id);
              setNewL2Name("");
            }}
          >
            {t("addL2")}
          </button>
        </section>
      ))}

      <div className="rounded-xl border border-dashed border-gray-300 bg-white p-4">
        <p className="text-sm font-medium text-gray-700">{t("addL1")}</p>
        <div className="mt-2 flex gap-2">
          <input
            className="flex-1 rounded border border-gray-200 px-2 py-1.5 text-sm"
            value={newL1Name}
            onChange={(e) => setNewL1Name(e.target.value)}
            placeholder={t("categoryNamePlaceholder")}
          />
          <button
            type="button"
            onClick={() => void handleCreateL1()}
            className="rounded-lg bg-gray-900 px-3 py-1.5 text-sm text-white"
          >
            {t("add")}
          </button>
        </div>
      </div>

      {newL2ParentId ? (
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <p className="text-sm font-medium text-gray-700">{t("addL2")}</p>
          <div className="mt-2 flex gap-2">
            <input
              className="flex-1 rounded border border-gray-200 px-2 py-1.5 text-sm"
              value={newL2Name}
              onChange={(e) => setNewL2Name(e.target.value)}
              placeholder={t("categoryNamePlaceholder")}
            />
            <button
              type="button"
              onClick={() => void handleCreateL2()}
              className="rounded-lg bg-gray-900 px-3 py-1.5 text-sm text-white"
            >
              {t("add")}
            </button>
            <button
              type="button"
              onClick={() => setNewL2ParentId(null)}
              className="text-sm text-gray-500 underline"
            >
              {t("cancel")}
            </button>
          </div>
        </div>
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
