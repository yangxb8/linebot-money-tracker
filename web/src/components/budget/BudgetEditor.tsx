"use client";

import { useEffect, useMemo, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { fetchBudgetSuggestions } from "@/lib/budget/client";
import type {
  BudgetCategoryNode,
  BudgetSummary,
  BudgetClearItem,
  BudgetUpsertItem,
} from "@/lib/budget/types";
import type { TenantOption } from "@/lib/dashboard/tenants";

type Draft = {
  total: string;
  l1: Record<string, string>;
  l2: Record<string, string>;
  clearTotal: boolean;
  clearL1: Set<string>;
  clearL2: Set<string>;
};

type Props = {
  open: boolean;
  summary: BudgetSummary;
  tenant: TenantOption;
  focusNode?: BudgetCategoryNode | null;
  initialDraft?: BudgetUpsertItem[];
  editable: boolean;
  onClose: () => void;
  onSave: (items: BudgetUpsertItem[], clear: BudgetClearItem[]) => Promise<void>;
};

function initDraft(summary: BudgetSummary): Draft {
  const l1: Record<string, string> = {};
  const l2: Record<string, string> = {};
  for (const c of summary.categories) {
    if (c.has_limit && c.limit != null) l1[c.node_id] = String(c.limit);
    for (const child of c.children ?? []) {
      if (child.has_limit && child.limit != null) {
        l2[child.node_id] = String(child.limit);
      }
    }
  }
  return {
    total:
      summary.total.has_limit && summary.total.limit != null
        ? String(summary.total.limit)
        : "",
    l1,
    l2,
    clearTotal: false,
    clearL1: new Set(),
    clearL2: new Set(),
  };
}

export function BudgetEditor({
  open,
  summary,
  tenant,
  focusNode: _focusNode,
  initialDraft,
  editable,
  onClose,
  onSave,
}: Props) {
  const { t } = useLanguage();
  const [draft, setDraft] = useState<Draft>(() => initDraft(summary));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      if (initialDraft?.length) {
        const next = initDraft(summary);
        for (const item of initialDraft) {
          if (item.budget_level === "total") next.total = String(item.amount);
          if (item.budget_level === "l1" && item.category_node_id) {
            next.l1[item.category_node_id] = String(item.amount);
          }
          if (item.budget_level === "l2" && item.category_node_id) {
            next.l2[item.category_node_id] = String(item.amount);
          }
        }
        setDraft(next);
      } else {
        setDraft(initDraft(summary));
      }
    }
  }, [open, summary, initialDraft]);

  const l1Suggested = useMemo(() => {
    const out: Record<string, number> = {};
    for (const c of summary.categories) {
      const sum = (c.children ?? []).reduce(
        (s, ch) => s + (Number(draft.l2[ch.node_id]) || 0),
        0,
      );
      if (sum > 0) out[c.node_id] = sum;
    }
    return out;
  }, [summary.categories, draft.l2]);

  const totalSuggested = useMemo(
    () =>
      Object.values(draft.l1).reduce((s, v) => s + (Number(v) || 0), 0),
    [draft.l1],
  );

  if (!open) return null;

  async function suggestFor(nodeId: string) {
    try {
      const rows = await fetchBudgetSuggestions(
        tenant,
        summary.budget_month,
        nodeId,
      );
      const row = rows[0];
      if (!row || row.months_sampled === 0) return;
      const node = summary.categories
        .flatMap((c) => [c, ...(c.children ?? [])])
        .find((n) => n.node_id === nodeId);
      if (!node) return;
      if (node.level === 1) {
        setDraft((d) => ({
          ...d,
          l1: { ...d.l1, [nodeId]: String(row.average_monthly_spent) },
        }));
      } else {
        setDraft((d) => ({
          ...d,
          l2: { ...d.l2, [nodeId]: String(row.average_monthly_spent) },
        }));
      }
    } catch {
      setError("suggest_failed");
    }
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    const items: BudgetUpsertItem[] = [];
    const clear: BudgetClearItem[] = [];

    if (draft.total.trim()) {
      const amount = Number(draft.total);
      if (!Number.isFinite(amount) || amount <= 0) {
        setError("invalid_amount");
        setSaving(false);
        return;
      }
      items.push({ budget_level: "total", amount: Math.round(amount) });
    } else if (summary.total.has_limit) {
      clear.push({ budget_level: "total" });
    }

    for (const c of summary.categories) {
      const v = draft.l1[c.node_id]?.trim();
      if (v) {
        const amount = Number(v);
        if (amount <= 0) {
          setError("invalid_amount");
          setSaving(false);
          return;
        }
        items.push({
          budget_level: "l1",
          category_node_id: c.node_id,
          amount: Math.round(amount),
        });
      } else if (c.has_limit) {
        clear.push({ budget_level: "l1", category_node_id: c.node_id });
      }
      for (const child of c.children ?? []) {
        const cv = draft.l2[child.node_id]?.trim();
        if (cv) {
          const amount = Number(cv);
          if (amount <= 0) {
            setError("invalid_amount");
            setSaving(false);
            return;
          }
          items.push({
            budget_level: "l2",
            category_node_id: child.node_id,
            amount: Math.round(amount),
          });
        } else if (child.has_limit) {
          clear.push({ budget_level: "l2", category_node_id: child.node_id });
        }
      }
    }

    try {
      await onSave(items, clear);
      onClose();
    } catch {
      setError("save_failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-white p-4 shadow-xl sm:rounded-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{t("budgetEditTitle")}</h2>
          <button type="button" onClick={onClose} className="text-sm text-gray-500">
            {t("cancel")}
          </button>
        </div>

        {!editable ? (
          <p className="text-sm text-gray-600">{t("budgetReadOnlyMonth")}</p>
        ) : (
          <div className="space-y-4">
            <label className="block text-sm">
              <span className="text-gray-600">{t("budgetTotalTitle")}</span>
              <input
                type="number"
                className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2"
                value={draft.total}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, total: e.target.value }))
                }
                placeholder={
                  totalSuggested > 0
                    ? String(totalSuggested)
                    : t("budgetOptionalPlaceholder")
                }
              />
              {totalSuggested > 0 ? (
                <span className="text-xs text-gray-400">
                  {t("budgetSuggestedSum")}: {totalSuggested}
                </span>
              ) : null}
            </label>

            {summary.categories.map((c) => (
              <div key={c.node_id} className="space-y-2 border-t border-gray-100 pt-3">
                <label className="block text-sm">
                  <span className="font-medium">{c.name_ja}</span>
                  <div className="mt-1 flex gap-2">
                    <input
                      type="number"
                      className="flex-1 rounded-lg border border-gray-200 px-3 py-2"
                      value={draft.l1[c.node_id] ?? ""}
                      onChange={(e) =>
                        setDraft((d) => ({
                          ...d,
                          l1: { ...d.l1, [c.node_id]: e.target.value },
                        }))
                      }
                      placeholder={
                        l1Suggested[c.node_id]
                          ? String(l1Suggested[c.node_id])
                          : t("budgetOptionalPlaceholder")
                      }
                    />
                    <button
                      type="button"
                      className="text-xs text-gray-500 underline"
                      onClick={() => void suggestFor(c.node_id)}
                    >
                      {t("budgetSuggest")}
                    </button>
                  </div>
                </label>
                {(c.children ?? []).map((child) => (
                  <label key={child.node_id} className="ml-4 block text-sm">
                    <span className="text-gray-600">{child.name_ja}</span>
                    <div className="mt-1 flex gap-2">
                      <input
                        type="number"
                        className="flex-1 rounded-lg border border-gray-200 px-3 py-2"
                        value={draft.l2[child.node_id] ?? ""}
                        onChange={(e) =>
                          setDraft((d) => ({
                            ...d,
                            l2: { ...d.l2, [child.node_id]: e.target.value },
                          }))
                        }
                        placeholder={t("budgetOptionalPlaceholder")}
                      />
                      <button
                        type="button"
                        className="text-xs text-gray-500 underline"
                        onClick={() => void suggestFor(child.node_id)}
                      >
                        {t("budgetSuggest")}
                      </button>
                    </div>
                  </label>
                ))}
              </div>
            ))}
          </div>
        )}

        {error ? (
          <p className="mt-3 text-sm text-red-600">
            {error === "invalid_amount"
              ? t("budgetErrorAmount")
              : t("saveFailed")}
          </p>
        ) : null}

        {editable ? (
          <button
            type="button"
            disabled={saving}
            onClick={() => void handleSave()}
            className="mt-4 w-full rounded-lg bg-gray-900 py-2.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? t("saving") : t("budgetSave")}
          </button>
        ) : null}
      </div>
    </div>
  );
}
