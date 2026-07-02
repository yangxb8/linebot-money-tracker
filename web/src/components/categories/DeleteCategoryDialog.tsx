"use client";

import { useMemo, useState } from "react";
import { Modal, ModalBody, ModalHeader } from "@/components/Modal";
import { useLanguage } from "@/components/LanguageProvider";
import type { CategoryNode } from "@/lib/categories/types";

type Props = {
  target: CategoryNode;
  nodes: CategoryNode[];
  onCancel: () => void;
  onConfirm: (transferToId?: string) => void;
};

function buildTransferTree(nodes: CategoryNode[], target: CategoryNode) {
  const excludeIds = new Set([target.id]);
  if (target.level === 1) {
    for (const node of nodes) {
      if (node.parent_id === target.id) {
        excludeIds.add(node.id);
      }
    }
  }

  const candidates = nodes.filter((node) => !excludeIds.has(node.id));
  const l1Nodes = candidates
    .filter((node) => node.level === 1)
    .sort((a, b) => a.sort_order - b.sort_order);

  const childrenByParent = new Map<string, CategoryNode[]>();
  for (const node of candidates) {
    if (node.level === 2 && node.parent_id) {
      const list = childrenByParent.get(node.parent_id) ?? [];
      list.push(node);
      childrenByParent.set(node.parent_id, list);
    }
  }
  for (const [, list] of childrenByParent) {
    list.sort((a, b) => a.sort_order - b.sort_order);
  }

  return { l1Nodes, childrenByParent };
}

function optionClass(selected: boolean) {
  return `w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
    selected
      ? "bg-blue-50 font-medium text-blue-700 ring-1 ring-blue-200"
      : "text-gray-800 hover:bg-gray-50"
  }`;
}

export function DeleteCategoryDialog({
  target,
  nodes,
  onCancel,
  onConfirm,
}: Props) {
  const { t } = useLanguage();
  const [transferId, setTransferId] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const needsTransfer = target.expense_count > 0;

  const { l1Nodes, childrenByParent } = useMemo(
    () => buildTransferTree(nodes, target),
    [nodes, target],
  );

  return (
    <Modal onClose={onCancel} panelClassName="max-w-md" split>
      <ModalHeader className="border-none pb-0">
        <h3 className="text-base font-semibold text-gray-900">
          {t("deleteCategoryTitle")}
        </h3>
      </ModalHeader>

      <ModalBody className="pt-2">
        <p className="text-sm text-gray-600">
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
          <div className="mt-4">
            <p className="text-xs text-gray-500">{t("transferTo")}</p>
            <div className="mt-1 max-h-60 overflow-y-auto rounded-lg border border-gray-200">
              <ul className="divide-y divide-gray-100 p-1">
                {l1Nodes.map((l1) => {
                  const children = childrenByParent.get(l1.id) ?? [];
                  const hasChildren = children.length > 0;
                  const open = expanded[l1.id] ?? false;
                  const l1Selected = transferId === l1.id;

                  return (
                    <li key={l1.id}>
                      <div className="flex items-stretch gap-1">
                        {hasChildren ? (
                          <button
                            type="button"
                            aria-expanded={open}
                            aria-label={l1.name_ja}
                            onClick={() =>
                              setExpanded((prev) => ({
                                ...prev,
                                [l1.id]: !open,
                              }))
                            }
                            className="flex w-8 shrink-0 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-50"
                          >
                            {open ? "▼" : "▶"}
                          </button>
                        ) : (
                          <span className="w-8 shrink-0" aria-hidden />
                        )}
                        <button
                          type="button"
                          onClick={() => setTransferId(l1.id)}
                          className={optionClass(l1Selected)}
                        >
                          {l1.name_ja}
                        </button>
                      </div>

                      {open && hasChildren ? (
                        <ul className="ml-8 mt-1 space-y-1 pb-1">
                          {children.map((l2) => {
                            const l2Selected = transferId === l2.id;
                            return (
                              <li key={l2.id}>
                                <button
                                  type="button"
                                  onClick={() => setTransferId(l2.id)}
                                  className={optionClass(l2Selected)}
                                >
                                  {l2.name_ja}
                                </button>
                              </li>
                            );
                          })}
                        </ul>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
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
      </ModalBody>
    </Modal>
  );
}
