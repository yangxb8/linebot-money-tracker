"use client";

import { useLanguage } from "@/components/LanguageProvider";

type Props = {
  deletable: boolean;
  isUnknown: boolean;
  onDelete?: () => void;
};

export function CategoryRowAction({ deletable, isUnknown, onDelete }: Props) {
  const { t } = useLanguage();

  if (!deletable) {
    return (
      <span
        className="shrink-0 p-1.5 text-gray-300"
        aria-label={t("lockedCategoryAria")}
        title={isUnknown ? t("unknownCategoryLocked") : t("lockedCategoryAria")}
      >
        <LockIcon />
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={onDelete}
      className="shrink-0 rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
      aria-label={t("deleteCategoryAria")}
    >
      <TrashIcon />
    </button>
  );
}

function TrashIcon() {
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
        d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM7.25 7.5a.75.75 0 00-1.5 0v7a.75.75 0 001.5 0v-7zm3.75 0a.75.75 0 00-1.5 0v7a.75.75 0 001.5 0v-7z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function LockIcon() {
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
        d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z"
        clipRule="evenodd"
      />
    </svg>
  );
}
