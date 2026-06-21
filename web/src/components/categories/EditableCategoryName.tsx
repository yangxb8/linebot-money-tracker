"use client";

import { useEffect, useRef, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";

type Props = {
  name: string;
  isEditing: boolean;
  isSaving?: boolean;
  showSaved?: boolean;
  onStartEdit: () => void;
  onSave: (name: string) => Promise<void>;
  onCancel: () => void;
  variant: "l1" | "l2";
  placeholder?: string;
};

export function EditableCategoryName({
  name,
  isEditing,
  isSaving,
  showSaved,
  onStartEdit,
  onSave,
  onCancel,
  variant,
  placeholder,
}: Props) {
  const { t } = useLanguage();
  const [draft, setDraft] = useState(name);
  const inputRef = useRef<HTMLInputElement>(null);
  const savingRef = useRef(false);

  useEffect(() => {
    if (isEditing) {
      setDraft(name);
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing, name]);

  async function commit() {
    if (savingRef.current) return;
    const trimmed = draft.trim();
    if (!trimmed) {
      onCancel();
      return;
    }
    if (trimmed === name) {
      onCancel();
      return;
    }
    savingRef.current = true;
    try {
      await onSave(trimmed);
    } finally {
      savingRef.current = false;
    }
  }

  if (isEditing) {
    return (
      <input
        ref={inputRef}
        className={`flex-1 rounded-lg border border-gray-300 bg-white px-2 py-1 outline-none ring-green-500 focus:ring-2 ${
          variant === "l1" ? "text-base font-semibold" : "text-sm"
        }`}
        value={draft}
        placeholder={placeholder ?? t("categoryNamePlaceholder")}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => void commit()}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            void commit();
          }
          if (e.key === "Escape") {
            e.preventDefault();
            onCancel();
          }
        }}
        disabled={isSaving}
      />
    );
  }

  return (
    <button
      type="button"
      onClick={onStartEdit}
      className={`group flex min-w-0 flex-1 items-center gap-2 text-left ${
        variant === "l1"
          ? "text-base font-semibold text-gray-900"
          : "text-sm text-gray-700"
      }`}
    >
      <span className="truncate">{name}</span>
      {showSaved ? (
        <span
          className="shrink-0 text-green-600"
          aria-label={t("saved")}
        >
          <CheckIcon />
        </span>
      ) : null}
      {isSaving ? (
        <span className="shrink-0 text-xs text-gray-400">{t("saving")}</span>
      ) : null}
    </button>
  );
}

function CheckIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
      aria-hidden
    >
      <path
        fillRule="evenodd"
        d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
        clipRule="evenodd"
      />
    </svg>
  );
}
