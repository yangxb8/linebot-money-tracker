"use client";

import { useState } from "react";
import { BudgetRow } from "@/components/budget/BudgetRow";
import type { BudgetCategoryNode } from "@/lib/budget/types";

type Props = {
  categories: BudgetCategoryNode[];
  elapsedDays: number;
  daysInMonth: number;
  editable: boolean;
  onEditNode: (node: BudgetCategoryNode) => void;
};

export function BudgetCategoryTree({
  categories,
  elapsedDays,
  daysInMonth,
  editable,
  onEditNode,
}: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  return (
    <div className="space-y-2">
      {categories.map((l1) => {
        const open = expanded[l1.node_id] ?? false;
        return (
          <div key={l1.node_id} className="space-y-2">
            <div className="flex gap-2">
              {(l1.children?.length ?? 0) > 0 ? (
                <button
                  type="button"
                  aria-expanded={open}
                  onClick={() =>
                    setExpanded((prev) => ({
                      ...prev,
                      [l1.node_id]: !open,
                    }))
                  }
                  className="mt-3 text-gray-500"
                >
                  {open ? "▼" : "▶"}
                </button>
              ) : (
                <span className="w-4" />
              )}
              <div className="flex-1">
                <BudgetRow
                  node={l1}
                  elapsedDays={elapsedDays}
                  daysInMonth={daysInMonth}
                  onEdit={editable ? () => onEditNode(l1) : undefined}
                />
              </div>
            </div>
            {open && l1.children
              ? l1.children.map((l2) => (
                  <div key={l2.node_id} className="ml-6">
                    <BudgetRow
                      node={l2}
                      elapsedDays={elapsedDays}
                      daysInMonth={daysInMonth}
                      onEdit={editable ? () => onEditNode(l2) : undefined}
                    />
                  </div>
                ))
              : null}
          </div>
        );
      })}
    </div>
  );
}
