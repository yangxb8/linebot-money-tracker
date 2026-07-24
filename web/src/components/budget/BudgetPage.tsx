"use client";

import { useCallback, useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { useTenant } from "@/components/TenantProvider";
import { BudgetCategoryExpensesModal } from "@/components/budget/BudgetCategoryExpensesModal";
import { BudgetCategoryTree } from "@/components/budget/BudgetCategoryTree";
import { BudgetEditor } from "@/components/budget/BudgetEditor";
import { BudgetEmptyState } from "@/components/budget/BudgetEmptyState";
import { BudgetTotalCard } from "@/components/budget/BudgetTotalCard";
import {
  copyBudgetsFromPrevious,
  fetchBudgetSummary,
  saveBudgets,
} from "@/lib/budget/client";
import type {
  BudgetCategoryNode,
  BudgetSummary,
  BudgetClearItem,
  BudgetUpsertItem,
} from "@/lib/budget/types";
import {
  currentBudgetMonthJst,
  formatBudgetPeriodLabel,
  isCurrentBudgetMonth,
  shiftBudgetMonth,
} from "@/lib/budget/format";
import { formatYen } from "@/lib/budget/format";
import type { Locale } from "@/lib/i18n/messages";
import { fetchTenantSettings } from "@/lib/settings/client";

export function BudgetPage() {
  const { t, locale } = useLanguage();
  const { selectedTenant } = useTenant();
  const [summary, setSummary] = useState<BudgetSummary | null>(null);
  const [fiscalStartDay, setFiscalStartDay] = useState(1);
  const [budgetMonth, setBudgetMonth] = useState(() => currentBudgetMonthJst());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [focusNode, setFocusNode] = useState<BudgetCategoryNode | null>(null);
  const [copyDraft, setCopyDraft] = useState<BudgetUpsertItem[] | undefined>();
  const [expensesNode, setExpensesNode] = useState<BudgetCategoryNode | null>(
    null,
  );

  const editable = isCurrentBudgetMonth(budgetMonth, fiscalStartDay);
  const currentMonth = currentBudgetMonthJst(fiscalStartDay);
  const fmt = (n: number) => formatYen(n, locale as Locale);

  useEffect(() => {
    if (!selectedTenant) return;
    let cancelled = false;
    void fetchTenantSettings(selectedTenant)
      .then((settings) => {
        if (cancelled) return;
        setFiscalStartDay(settings.fiscal_start_day);
        setBudgetMonth(currentBudgetMonthJst(settings.fiscal_start_day));
      })
      .catch(() => {
        if (!cancelled) {
          setFiscalStartDay(1);
          setBudgetMonth(currentBudgetMonthJst());
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedTenant]);

  const load = useCallback(async () => {
    if (!selectedTenant) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchBudgetSummary(selectedTenant, budgetMonth);
      setSummary(data);
      if (data.fiscal_start_day) {
        setFiscalStartDay(data.fiscal_start_day);
      }
    } catch {
      setError("fetch_failed");
    } finally {
      setLoading(false);
    }
  }, [selectedTenant, budgetMonth]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSave(
    items: BudgetUpsertItem[],
    clear: BudgetClearItem[],
  ) {
    if (!selectedTenant || !summary) return;
    await saveBudgets({
      tenant_type: selectedTenant.tenantType,
      tenant_id: selectedTenant.tenantId,
      budget_month: summary.budget_month,
      currency: "JPY",
      budgets: items,
      clear_levels: clear.map((c) => ({
        budget_level: c.budget_level,
        category_node_id: c.category_node_id,
      })),
    });
    await load();
  }

  async function handleCopyFromPrevious() {
    if (!selectedTenant || !summary) return;
    try {
      const result = await copyBudgetsFromPrevious(
        selectedTenant,
        summary.budget_month,
      );
      if (!result.available || !result.budgets?.length) return;
      setCopyDraft(result.budgets);
      setEditorOpen(true);
    } catch {
      setError("copy_failed");
    }
  }

  if (!selectedTenant) return null;

  if (loading && !summary) {
    return <p className="text-sm text-gray-500">{t("loading")}</p>;
  }

  if (error && !summary) {
    return (
      <div className="space-y-2 text-center">
        <p className="text-sm text-red-600">{t("errorGeneric")}</p>
        <button type="button" onClick={() => void load()} className="text-sm underline">
          {t("retry")}
        </button>
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-label="Previous month"
            className="rounded border border-gray-200 px-2 py-1 text-sm"
            onClick={() => setBudgetMonth((m) => shiftBudgetMonth(m, -1))}
          >
            ‹
          </button>
          <span className="text-sm font-medium text-gray-800">
            {formatBudgetPeriodLabel(
              summary.budget_month,
              summary.fiscal_period_end,
              fiscalStartDay,
            )}
          </span>
          <button
            type="button"
            aria-label="Next month"
            className="rounded border border-gray-200 px-2 py-1 text-sm"
            disabled={budgetMonth >= currentMonth}
            onClick={() => setBudgetMonth((m) => shiftBudgetMonth(m, 1))}
          >
            ›
          </button>
        </div>
        {editable ? (
          <button
            type="button"
            onClick={() => void handleCopyFromPrevious()}
            className="text-xs text-gray-600 underline"
          >
            {t("budgetCopyPrevious")}
          </button>
        ) : null}
      </div>

      {!summary.has_any_limit ? (
        <BudgetEmptyState
          onStart={() => {
            setFocusNode(null);
            setCopyDraft(undefined);
            setEditorOpen(true);
          }}
        />
      ) : null}

      {summary.lazy_copied_from_previous ? (
        <p className="rounded-lg bg-sky-50 px-3 py-2 text-sm text-sky-800">
          {t("budgetLazyCopiedNotice")}
        </p>
      ) : null}

      <BudgetTotalCard
        total={summary.total}
        elapsedDays={summary.elapsed_days}
        daysInMonth={summary.days_in_month}
        hasAnyLimit={summary.has_any_limit}
        onEdit={
          editable
            ? () => {
                setFocusNode(null);
                setCopyDraft(undefined);
                setEditorOpen(true);
              }
            : undefined
        }
      />

      {summary.unbudgeted_spent > 0 ? (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {t("budgetUnbudgetedCallout")}: {fmt(summary.unbudgeted_spent)}
        </p>
      ) : null}

      <BudgetCategoryTree
        categories={summary.categories}
        elapsedDays={summary.elapsed_days}
        daysInMonth={summary.days_in_month}
        editable={editable}
        onEditNode={(node) => {
          setFocusNode(node);
          setCopyDraft(undefined);
          setEditorOpen(true);
        }}
        onSelectNode={(node) => setExpensesNode(node)}
      />

      <BudgetCategoryExpensesModal
        open={expensesNode !== null}
        tenant={selectedTenant}
        budgetMonth={summary.budget_month}
        node={expensesNode}
        onClose={() => setExpensesNode(null)}
      />

      <BudgetEditor
        open={editorOpen}
        summary={summary}
        tenant={selectedTenant}
        focusNode={focusNode}
        initialDraft={copyDraft}
        editable={editable}
        onClose={() => {
          setEditorOpen(false);
          setCopyDraft(undefined);
        }}
        onSave={handleSave}
      />
    </div>
  );
}
