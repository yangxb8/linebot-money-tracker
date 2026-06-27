"use client";

import { useEffect, useRef, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { CategoryNodeSelect } from "@/components/expenses/CategoryNodeSelect";
import { categoryLabel } from "@/lib/dashboard/format";
import type { CategoryNode } from "@/lib/categories/types";
import { updateExpense } from "@/lib/expenses/client";
import type { ExpenseRecord } from "@/lib/expenses/types";

type Props = {
  expense: ExpenseRecord;
  categories: CategoryNode[];
  disabled?: boolean;
  onUpdated: (expense: ExpenseRecord) => void;
  onError: () => void;
};

export function ExpenseCategoryTag({
  expense,
  categories,
  disabled,
  onUpdated,
  onError,
}: Props) {
  const { t } = useLanguage();
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const selectRef = useRef<HTMLSelectElement>(null);

  useEffect(() => {
    if (!editing) return;

    function handlePointerDown(event: PointerEvent) {
      if (selectRef.current?.contains(event.target as Node)) return;
      setEditing(false);
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [editing]);

  async function handleChange(categoryNodeId: string) {
    if (!categoryNodeId || categoryNodeId === expense.category_node_id) {
      setEditing(false);
      return;
    }

    setSaving(true);
    try {
      const updated = await updateExpense(expense.id, {
        category_node_id: categoryNodeId,
      });
      setEditing(false);
      onUpdated(updated);
    } catch {
      onError();
    } finally {
      setSaving(false);
    }
  }

  if (editing) {
    return (
      <div onClick={(event) => event.stopPropagation()}>
        <CategoryNodeSelect
          ref={selectRef}
          categories={categories}
          value={expense.category_node_id}
          disabled={saving}
          autoFocus
          onChange={(categoryNodeId) => void handleChange(categoryNodeId)}
          className="max-w-full rounded-full border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-700 disabled:opacity-60"
        />
      </div>
    );
  }

  return (
    <button
      type="button"
      disabled={disabled || saving}
      onClick={(event) => {
        event.stopPropagation();
        setEditing(true);
      }}
      className="inline-block max-w-full truncate rounded-full bg-gray-100 px-2 py-0.5 text-left text-xs text-gray-600 hover:bg-gray-200 disabled:opacity-60"
      title={t("periodicCategory")}
    >
      {categoryLabel(expense)}
    </button>
  );
}
