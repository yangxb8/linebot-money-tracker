"use client";

import { useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import type { CategoryNode } from "@/lib/categories/types";

type Props = {
  target: CategoryNode;
  candidates: CategoryNode[];
  onCancel: () => void;
  onConfirm: (transferToId?: string) => void;
};

export function DeleteCategoryDialog({
  target,
  candidates,
  onCancel,
  onConfirm,
}: Props) {
  const { t } = useLanguage();
  const [transferId, setTransferId] = useState("");
  const needsTransfer = target.expense_count > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
      <div className="w-full max-w-md rounded-xl bg-white p-4 shadow-xl">
        <h3 className="text-base font-semibold text-gray-900">
          {t("deleteCategoryTitle")}
        </h3>
        <p className="mt-2 text-sm text-gray-600">
          {needsTransfer ? (
            <>
              {t("deleteCategoryTransferPrefix")} {target.expense_count}{" "}
              {t("deleteCategoryTransferSuffix")}
            </>
          ) : (
            <>
              {t("deleteCategoryConfirm")} ({target.name_ja})
            </>
          )}
        </p>

        {needsTransfer ? (
          <label className="mt-4 block">
            <span className="text-xs text-gray-500">{t("transferTo")}</span>
            <select
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              value={transferId}
              onChange={(e) => setTransferId(e.target.value)}
            >
              <option value="">{t("selectTransferTarget")}</option>
              {candidates.map((node) => {
                const parent =
                  node.level === 2 && node.parent_id
                    ? candidates.find((c) => c.id === node.parent_id)
                    : null;
                const label = parent
                  ? `${parent.name_ja} > ${node.name_ja}`
                  : node.name_ja;
                return (
                  <option key={node.id} value={node.id}>
                    {label}
                  </option>
                );
              })}
            </select>
          </label>
        ) : null}

        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg px-3 py-2 text-sm text-gray-600"
          >
            {t("cancel")}
          </button>
          <button
            type="button"
            disabled={needsTransfer && !transferId}
            onClick={() =>
              onConfirm(needsTransfer ? transferId : undefined)
            }
            className="rounded-lg bg-red-600 px-3 py-2 text-sm text-white disabled:opacity-50"
          >
            {t("delete")}
          </button>
        </div>
      </div>
    </div>
  );
}
