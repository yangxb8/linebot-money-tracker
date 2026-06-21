"use client";

import { useEffect, useRef, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";

type Props = {
  onCreate: (name: string) => Promise<void>;
  onCancel: () => void;
  variant: "l1" | "l2";
};

export function InlineCategoryDraft({ onCreate, onCancel, variant }: Props) {
  const { t } = useLanguage();
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const busyRef = useRef(false);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function commit() {
    if (busyRef.current) return;
    const trimmed = draft.trim();
    if (!trimmed) {
      onCancel();
      return;
    }
    busyRef.current = true;
    try {
      await onCreate(trimmed);
    } catch {
      busyRef.current = false;
    }
  }

  return (
    <input
      ref={inputRef}
      className={`w-full rounded-lg border border-dashed border-gray-300 bg-gray-50 px-2 py-1.5 outline-none ring-green-500 focus:border-gray-400 focus:bg-white focus:ring-2 ${
        variant === "l1" ? "text-sm" : "text-sm"
      }`}
      value={draft}
      placeholder={t("categoryNamePlaceholder")}
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
    />
  );
}
