"use client";

import { useEffect, useState } from "react";
import { Modal, ModalBody, ModalHeader } from "@/components/Modal";
import { useLanguage } from "@/components/LanguageProvider";
import { ExpenseSortControls } from "@/components/expenses/ExpenseSortControls";
import { formatYen } from "@/lib/budget/format";
import { fetchExpensesForMonth } from "@/lib/expenses/client";
import type {
  ExpenseSortDir,
  ExpenseSortField,
} from "@/lib/expenses/sort-group";
import type { ExpenseRecord } from "@/lib/expenses/types";
import type { BudgetCategoryNode } from "@/lib/budget/types";
import type { TenantOption } from "@/lib/dashboard/tenants";
import type { Locale } from "@/lib/i18n/messages";

type Props = {
  open: boolean;
  tenant: TenantOption;
  budgetMonth: string;
  node: BudgetCategoryNode | null;
  onClose: () => void;
};

function formatDate(date: string): string {
  return new Date(date).toLocaleDateString("ja-JP", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function BudgetCategoryExpensesModal({
  open,
  tenant,
  budgetMonth,
  node,
  onClose,
}: Props) {
  const { t, locale } = useLanguage();
  const [rows, setRows] = useState<ExpenseRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<ExpenseSortField>("date");
  const [sortDir, setSortDir] = useState<ExpenseSortDir>("desc");
  const fmt = (n: number) => formatYen(n, locale as Locale);

  useEffect(() => {
    if (!open || !node) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setRows([]);
    const filter =
      node.level === 2
        ? { categoryL2Id: node.node_id }
        : { categoryL1Id: node.node_id };
    void fetchExpensesForMonth(tenant, budgetMonth, 0, 200, filter, {
      field: sortField,
      dir: sortDir,
    })
      .then((data) => {
        if (!cancelled) setRows(data);
      })
      .catch(() => {
        if (!cancelled) setError("fetch_failed");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, node, tenant, budgetMonth, sortField, sortDir]);

  if (!open || !node) return null;

  const total = rows.reduce((sum, row) => sum + Number(row.amount), 0);
  const sortLabels = {
    sortBy: t("expenseSortBy"),
    sortDate: t("expenseSortDate"),
    sortAmount: t("expenseSortAmount"),
    dateLateToEarly: t("expenseSortDateLateToEarly"),
    dateEarlyToLate: t("expenseSortDateEarlyToLate"),
    amountLargeToSmall: t("expenseSortAmountLargeToSmall"),
    amountSmallToLarge: t("expenseSortAmountSmallToLarge"),
  };

  return (
    <Modal open={open} onClose={onClose} split>
      <ModalHeader className="border-b border-gray-100">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold">{node.name_ja}</h2>
            <p className="text-xs text-gray-500">
              {t("expenseMonthTotal")}: {fmt(total)}
              {rows.length > 0 ? ` · ${rows.length}` : ""}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-lg px-2 py-1 text-sm text-gray-500 hover:bg-gray-50"
          >
            {t("cancel")}
          </button>
        </div>
      </ModalHeader>

      <ModalBody>
        {loading ? (
          <p className="py-8 text-center text-sm text-gray-500">{t("loading")}</p>
        ) : error ? (
          <p className="py-8 text-center text-sm text-red-600">
            {t("errorGeneric")}
          </p>
        ) : rows.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-500">
            {t("emptyExpensesMonth")}
          </p>
        ) : (
          <div className="space-y-3">
            <div className="rounded-xl border border-gray-100 bg-white px-3 py-2 shadow-sm">
              <ExpenseSortControls
                sortField={sortField}
                sortDir={sortDir}
                labels={sortLabels}
                onSortFieldChange={setSortField}
                onSortDirChange={setSortDir}
              />
            </div>
            <ul className="divide-y divide-gray-100 rounded-lg border border-gray-100">
              {rows.map((row) => (
                <li
                  key={row.id}
                  className="flex items-start justify-between gap-3 px-3 py-2"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-gray-900">
                      {row.description || "—"}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatDate(row.expense_date)}
                      {row.category_l2_name ? ` · ${row.category_l2_name}` : ""}
                    </p>
                  </div>
                  <p className="whitespace-nowrap text-sm font-medium text-gray-900">
                    {fmt(Number(row.amount))}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        )}
      </ModalBody>
    </Modal>
  );
}
