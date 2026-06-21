"use client";

import { useLanguage } from "@/components/LanguageProvider";

type Props = {
  label: string;
  x: number;
  y: number;
};

export function CategoryDragOverlay({ label, x, y }: Props) {
  return (
    <div
      className="pointer-events-none fixed z-50 -translate-x-1/2 -translate-y-1/2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-900 shadow-lg"
      style={{ left: x, top: y }}
    >
      {label}
    </div>
  );
}

type DropZoneProps = {
  zone: string;
  active: boolean;
  children: React.ReactNode;
  className?: string;
};

export function CategoryDropZone({
  zone,
  active,
  children,
  className = "",
}: DropZoneProps) {
  return (
    <div
      data-drop-zone={zone}
      className={`transition-colors ${active ? "rounded-lg bg-blue-50 ring-2 ring-blue-400 ring-inset" : ""} ${className}`}
    >
      {children}
    </div>
  );
}

export function PromoteDropZone({ active }: { active: boolean }) {
  const { t } = useLanguage();
  return (
    <CategoryDropZone
      zone="promote"
      active={active}
      className="rounded-xl border border-dashed border-gray-300 bg-white px-4 py-3 text-center text-sm text-gray-500"
    >
      {t("promoteDropZone")}
    </CategoryDropZone>
  );
}
