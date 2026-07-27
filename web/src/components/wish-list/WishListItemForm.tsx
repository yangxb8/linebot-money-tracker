"use client";

import { useEffect, useState } from "react";
import { Modal, ModalBody, ModalHeader } from "@/components/Modal";
import { CategoryNodeSelect } from "@/components/expenses/CategoryNodeSelect";
import { useLanguage } from "@/components/LanguageProvider";
import { fetchCategories } from "@/lib/categories/client";
import type { CategoryNode } from "@/lib/categories/types";
import type { TenantOption } from "@/lib/dashboard/tenants";
import {
  createWishListItem,
  defaultWishListFormValues,
  updateWishListItem,
  wishListItemToFormValues,
} from "@/lib/wish-list/client";
import type { WishListFormValues, WishListItem } from "@/lib/wish-list/types";
import { isValidProductUrl } from "@/lib/wish-list/validation";

type Props = {
  tenant: TenantOption;
  item?: WishListItem | null;
  onClose: () => void;
  onSaved: (item: WishListItem) => void;
};

type FieldErrors = {
  name?: boolean;
  amount?: boolean;
  category?: boolean;
  product_url?: boolean;
};

function fieldClass(invalid?: boolean) {
  return `mt-1 w-full rounded-lg border px-3 py-2 text-sm ${
    invalid
      ? "border-red-500 focus:border-red-500 focus:outline-none focus:ring-2 focus:ring-red-200"
      : "border-gray-200"
  }`;
}

export function WishListItemForm({ tenant, item, onClose, onSaved }: Props) {
  const { t } = useLanguage();
  const [values, setValues] = useState<WishListFormValues>(() =>
    item ? wishListItemToFormValues(item) : defaultWishListFormValues(),
  );
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
    if (!isValidProductUrl(values.product_url)) nextErrors.product_url = true;
    setFieldErrors(nextErrors);

    if (nextErrors.name) return t("wishListErrorName");
    if (nextErrors.amount) return t("wishListErrorAmount");
    if (nextErrors.category) return t("wishListErrorCategory");
    if (nextErrors.product_url) return t("wishListErrorUrl");
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
      const payload = {
        name: values.name.trim(),
        amount: Number(values.amount),
        category_node_id: values.category_node_id,
        product_url: values.product_url.trim() || null,
      };
      const saved = item
        ? await updateWishListItem(item.id, payload)
        : await createWishListItem({
            tenant_type: tenant.tenantType,
            tenant_id: tenant.tenantId,
            ...payload,
          });
      onSaved(saved);
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
            {item ? t("wishListEdit") : t("wishListAdd")}
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
              placeholder="0"
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
              {t("wishListLink")}
            </label>
            <input
              value={values.product_url}
              onChange={(event) =>
                setValues((prev) => ({ ...prev, product_url: event.target.value }))
              }
              className={fieldClass(fieldErrors.product_url)}
              placeholder="https://example.com"
            />
          </div>

          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          <button
            type="submit"
            disabled={saving}
            className="w-full rounded-lg bg-gray-900 py-2.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? t("saving") : t("budgetSave")}
          </button>
        </div>
      </ModalBody>
    </Modal>
  );
}
