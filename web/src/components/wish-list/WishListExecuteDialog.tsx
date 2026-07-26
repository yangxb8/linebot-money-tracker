"use client";

import { useEffect, useState } from "react";
import { IsoDateInput } from "@/components/IsoDateInput";
import { useLanguage } from "@/components/LanguageProvider";
import { Modal, ModalBody, ModalHeader } from "@/components/Modal";
import { CategoryNodeSelect } from "@/components/expenses/CategoryNodeSelect";
import { fetchCategories } from "@/lib/categories/client";
import type { CategoryNode } from "@/lib/categories/types";
import type { TenantOption } from "@/lib/dashboard/tenants";
import { executeWishListItem } from "@/lib/wish-list/client";
import type { WishListItem } from "@/lib/wish-list/types";

type Props = {
  tenant: TenantOption;
  item: WishListItem;
  onClose: () => void;
  onExecuted: () => void;
};

type FieldErrors = {
  name?: boolean;
  amount?: boolean;
  category?: boolean;
  expense_date?: boolean;
};

function todayIso() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function fieldClass(invalid?: boolean) {
  return `mt-1 w-full rounded-lg border px-3 py-2 text-sm ${
    invalid
      ? "border-red-500 focus:border-red-500 focus:outline-none focus:ring-2 focus:ring-red-200"
      : "border-gray-200"
  }`;
}

export function WishListExecuteDialog({
  tenant,
  item,
  onClose,
  onExecuted,
}: Props) {
  const { t } = useLanguage();
  const [values, setValues] = useState({
    name: item.name,
    amount: String(item.amount),
    category_node_id: item.category_node_id,
    expense_date: todayIso(),
  });
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [error, setError] = useState<string | null>(null);
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

  function validateClient(): string | null {
    const nextErrors: FieldErrors = {};
    const amount = Number(values.amount);
    if (!values.name.trim()) nextErrors.name = true;
    if (!Number.isFinite(amount) || amount <= 0) nextErrors.amount = true;
    if (!values.category_node_id) nextErrors.category = true;
    if (!values.expense_date) nextErrors.expense_date = true;
    setFieldErrors(nextErrors);

    if (nextErrors.name) return t("wishListErrorName");
    if (nextErrors.amount) return t("wishListErrorAmount");
    if (nextErrors.category) return t("wishListErrorCategory");
    if (nextErrors.expense_date) return t("expenseErrorDate");
    return null;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const validationError = validateClient();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await executeWishListItem(item.id, {
        tenant_type: tenant.tenantType,
        tenant_id: tenant.tenantId,
        name: values.name.trim(),
        amount: Number(values.amount),
        category_node_id: values.category_node_id,
        expense_date: values.expense_date,
      });
      onExecuted();
      onClose();
    } catch {
      setError(t("saveFailed"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      as="form"
      onClose={onClose}
      split
      formProps={{ onSubmit: (event) => void handleSubmit(event) }}
    >
      <ModalHeader>
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-gray-900">
            {t("wishListExecuteTitle")}
          </h2>
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
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-700">
              {t("wishListName")}
            </label>
            <input
              value={values.name}
              onChange={(event) =>
                setValues((prev) => ({ ...prev, name: event.target.value }))
              }
              className={fieldClass(fieldErrors.name)}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">
              {t("wishListAmount")}
            </label>
            <input
              inputMode="numeric"
              value={values.amount}
              onChange={(event) =>
                setValues((prev) => ({ ...prev, amount: event.target.value }))
              }
              className={fieldClass(fieldErrors.amount)}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">
              {t("periodicCategory")}
            </label>
            <CategoryNodeSelect
              categories={categories}
              value={values.category_node_id}
              placeholder={t("selectTransferTarget")}
              onChange={(category_node_id) =>
                setValues((prev) => ({ ...prev, category_node_id }))
              }
              className={fieldClass(fieldErrors.category)}
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
              className="mt-1"
            />
          </div>

          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          <button
            type="submit"
            disabled={saving}
            className="w-full rounded-lg bg-gray-900 py-2.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? t("saving") : t("wishListConfirmExecute")}
          </button>
        </div>
      </ModalBody>
    </Modal>
  );
}
