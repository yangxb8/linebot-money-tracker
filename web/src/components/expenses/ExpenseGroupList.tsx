"use client";

import { useState } from "react";
import { ExpenseRowItem } from "@/components/expenses/ExpenseRowItem";
import type { CategoryNode } from "@/lib/categories/types";
import type { ExpenseGroup } from "@/lib/expenses/sort-group";
import type { ExpenseRecord } from "@/lib/expenses/types";

type Props = {
  groups: ExpenseGroup[];
  categories: CategoryNode[];
  busyId: string | null;
  formatAmount: (amount: number) => string;
  formatDate: (date: string) => string;
  deleteLabel: string;
  itemCountLabel: (count: number) => string;
  onEdit: (expense: ExpenseRecord) => void;
  onDelete: (expense: ExpenseRecord) => void;
  onUpdated: (expense: ExpenseRecord) => void;
  onError: () => void;
};

export function ExpenseGroupList({
  groups,
  categories,
  busyId,
  formatAmount,
  formatDate,
  deleteLabel,
  itemCountLabel,
  onEdit,
  onDelete,
  onUpdated,
  onError,
}: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  return (
    <div className="space-y-3">
      {groups.map((group) => {
        const open = expanded[group.key] ?? false;
        return (
          <section
            key={group.key}
            className="overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm"
          >
            <button
              type="button"
              aria-expanded={open}
              onClick={() =>
                setExpanded((prev) => ({
                  ...prev,
                  [group.key]: !open,
                }))
              }
              className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-gray-50"
            >
              <span className="text-gray-500">{open ? "▼" : "▶"}</span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {group.label}
                </p>
                <p className="text-xs text-gray-500">
                  {itemCountLabel(group.items.length)}
                </p>
              </div>
              <p className="text-sm font-semibold text-gray-900 shrink-0">
                {formatAmount(group.total)}
              </p>
            </button>
            {open ? (
              <ul className="divide-y divide-gray-100 border-t border-gray-100">
                {group.items.map((row) => (
                  <ExpenseRowItem
                    key={row.id}
                    row={row}
                    categories={categories}
                    busyId={busyId}
                    formatAmount={formatAmount}
                    formatDate={formatDate}
                    deleteLabel={deleteLabel}
                    onEdit={onEdit}
                    onDelete={onDelete}
                    onUpdated={onUpdated}
                    onError={onError}
                  />
                ))}
              </ul>
            ) : null}
          </section>
        );
      })}
    </div>
  );
}
