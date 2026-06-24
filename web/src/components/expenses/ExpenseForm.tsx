"use client";

import { useEffect, useState } from "react";
import { IsoDateInput } from "@/components/IsoDateInput";
import { useLanguage } from "@/components/LanguageProvider";
import { fetchCategories } from "@/lib/categories/client";
import type { CategoryNode } from "@/lib/categories/types";
import type { TenantOption } from "@/lib/dashboard/tenants";
import {
  createExpense,
  defaultExpenseFormValues,
  expenseToFormValues,
  updateExpense,
} from "@/lib/expenses/client";
import type { ExpenseFormValues, ExpenseRecord } from "@/lib/expenses/types";

type Props = {
  tenant: TenantOption;
  expense?: ExpenseRecord | null;
  defaultDate: string;
  onClose: () => void;
  onSaved: () => void;
};

type FieldErrors = {
  description?: boolean;
  amount?: boolean;
  expense_date?: boolean;
  category?: boolean;
};

function fieldClass(invalid?: boolean) {
  return `mt-1 w-full rounded-lg border px-3 py-2 text-sm ${
    invalid
      ? "border-red-500 focus:border-red-500 focus:outline-none focus:ring-2 focus:ring-red-200"
      : "border-gray-200"
  }`;
}

export function ExpenseForm({
  tenant,
  expense,
  defaultDate,
  onClose,
  onSaved,
}: Props) {
  const { t } = useLanguage();
  const [values, setValues] = useState<ExpenseFormValues>(() =>
    expense ? expenseToFormValues(expense) : defaultExpenseFormValues(defaultDate),
  );
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void fetchCategories(tenant)
      .then((data) => {
        if (!cancelled) setCategories(data.nodes);
      })
      .catch(() => {
        if (!cancelled) setError(t("errorGeneric"));
      });
    return () => {
      cancelled = true;
    };
  }, [tenant, t]);

  function validate(): string | null {
    const nextErrors: FieldErrors = {};
    if (!values.description.trim()) nextErrors.description = true;
    const amount = Number(values.amount);
    if (!Number.isFinite(amount) || amount <= 0) nextErrors.amount = true;
    if (!values.expense_date) nextErrors.expense_date = true;
    if (!values.category_node_id) nextErrors.category = true;
    setFieldErrors(nextErrors);
    if (nextErrors.description) return t("expenseErrorDescription");
    if (nextErrors.amount) return t("expenseErrorAmount");
    if (nextErrors.expense_date) return t("expenseErrorDate");
    if (nextErrors.category) return t("expenseErrorCategory");
    return null;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const payload = {
        description: values.description.trim(),
        amount: Number(values.amount),
        expense_date: values.expense_date,
        category_node_id: values.category_node_id,
      };

      if (expense) {
        await updateExpense(expense.id, payload);
      } else {
        await createExpense({
          tenant_type: tenant.tenantType,
          tenant_id: tenant.tenantId,
          ...payload,
        });
      }
      onSaved();
      onClose();
    } catch {
      setError(t("saveFailed"));
    } finally {
      setSaving(false);
    }
  }

  const l1Nodes = categories.filter((node) => node.level === 1);
  const l2Nodes = categories.filter((node) => node.level === 2);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
      <form
        onSubmit={(event) => void handleSubmit(event)}
        className="w-full max-w-lg rounded-2xl bg-white p-4 shadow-xl"
      >
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-gray-900">
            {expense ? t("expenseEditTitle") : t("expenseCreateTitle")}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-sm text-gray-500 underline"
          >
            {t("cancel")}
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium text-gray-700">
              {t("expenseDescription")}
            </label>
            <input
              value={values.description}
              onChange={(event) =>
                setValues((prev) => ({ ...prev, description: event.target.value }))
              }
              className={fieldClass(fieldErrors.description)}
              placeholder={t("expenseDescriptionPlaceholder")}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">
              {t("expenseAmount")}
            </label>
            <input
              inputMode="numeric"
              value={values.amount}
              onChange={(event) =>
                setValues((prev) => ({ ...prev, amount: event.target.value }))
              }
              className={fieldClass(fieldErrors.amount)}
              placeholder="0"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">
              {t("expenseDate")}
            </label>
            <IsoDateInput
              value={values.expense_date}
              invalid={fieldErrors.expense_date}
              onChange={(expense_date) =>
                setValues((prev) => ({ ...prev, expense_date }))
              }
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">
              {t("periodicCategory")}
            </label>
            <select
              value={values.category_node_id}
              onChange={(event) =>
                setValues((prev) => ({
                  ...prev,
                  category_node_id: event.target.value,
                }))
              }
              className={fieldClass(fieldErrors.category)}
            >
              <option value="">{t("selectTransferTarget")}</option>
              {l1Nodes.map((l1) => (
                <optgroup key={l1.id} label={l1.name_ja}>
                  <option value={l1.id}>{l1.name_ja}</option>
                  {l2Nodes
                    .filter((l2) => l2.parent_id === l1.id)
                    .map((l2) => (
                      <option key={l2.id} value={l2.id}>
                        {l2.name_ja}
                      </option>
                    ))}
                </optgroup>
              ))}
            </select>
          </div>
        </div>

        {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}

        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-gray-200 px-4 py-2 text-sm"
          >
            {t("cancel")}
          </button>
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {saving ? t("saving") : t("budgetSave")}
          </button>
        </div>
      </form>
    </div>
  );
}
