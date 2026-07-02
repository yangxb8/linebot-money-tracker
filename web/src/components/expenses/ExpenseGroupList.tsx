"use client";

import { useState } from "react";
import { ExpenseRowItem } from "@/components/expenses/ExpenseRowItem";
import type { CategoryNode } from "@/lib/categories/types";
import type { ExpenseL1Group } from "@/lib/expenses/sort-group";
import type { ExpenseRecord } from "@/lib/expenses/types";

type Props = {
  groups: ExpenseL1Group[];
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

type RowProps = Pick<
  Props,
  | "categories"
  | "busyId"
  | "formatAmount"
  | "formatDate"
  | "deleteLabel"
  | "onEdit"
  | "onDelete"
  | "onUpdated"
  | "onError"
>;

function ExpenseRows({
  items,
  categories,
  busyId,
  formatAmount,
  formatDate,
  deleteLabel,
  onEdit,
  onDelete,
  onUpdated,
  onError,
}: RowProps & { items: ExpenseRecord[] }) {
  if (items.length === 0) return null;

  return (
    <ul className="divide-y divide-gray-100 border-t border-gray-100">
      {items.map((row) => (
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
  );
}

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
  const [expandedL1, setExpandedL1] = useState<Record<string, boolean>>({});
  const [expandedL2, setExpandedL2] = useState<Record<string, boolean>>({});

  const rowProps = {
    categories,
    busyId,
    formatAmount,
    formatDate,
    deleteLabel,
    onEdit,
    onDelete,
    onUpdated,
    onError,
  };

  return (
    <div className="space-y-3">
      {groups.map((group) => {
        const l1Open = expandedL1[group.key] ?? false;
        return (
          <section
            key={group.key}
            className="overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm"
          >
            <button
              type="button"
              aria-expanded={l1Open}
              onClick={() =>
                setExpandedL1((prev) => ({
                  ...prev,
                  [group.key]: !l1Open,
                }))
              }
              className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-gray-50"
            >
              <span className="text-gray-500">{l1Open ? "▼" : "▶"}</span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {group.label}
                </p>
                <p className="text-xs text-gray-500">
                  {itemCountLabel(group.itemCount)}
                </p>
              </div>
              <p className="text-sm font-semibold text-gray-900 shrink-0">
                {formatAmount(group.total)}
              </p>
            </button>
            {l1Open ? (
              <div className="border-t border-gray-100">
                {group.l2Groups.map((l2Group) => {
                  const l2Key = `${group.key}:${l2Group.key}`;
                  const l2Open = expandedL2[l2Key] ?? false;
                  return (
                    <section key={l2Key} className="border-b border-gray-50 last:border-b-0">
                      <button
                        type="button"
                        aria-expanded={l2Open}
                        onClick={() =>
                          setExpandedL2((prev) => ({
                            ...prev,
                            [l2Key]: !l2Open,
                          }))
                        }
                        className="flex w-full items-center gap-3 px-4 py-2.5 pl-8 text-left hover:bg-gray-50"
                      >
                        <span className="text-gray-400 text-xs">
                          {l2Open ? "▼" : "▶"}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm text-gray-800 truncate">
                            {l2Group.label}
                          </p>
                          <p className="text-xs text-gray-500">
                            {itemCountLabel(l2Group.items.length)}
                          </p>
                        </div>
                        <p className="text-sm font-medium text-gray-800 shrink-0">
                          {formatAmount(l2Group.total)}
                        </p>
                      </button>
                      {l2Open ? (
                        <ExpenseRows items={l2Group.items} {...rowProps} />
                      ) : null}
                    </section>
                  );
                })}
                <ExpenseRows items={group.directItems} {...rowProps} />
              </div>
            ) : null}
          </section>
        );
      })}
    </div>
  );
}
