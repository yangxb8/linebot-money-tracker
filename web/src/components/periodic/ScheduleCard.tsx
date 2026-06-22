"use client";

import { useLanguage } from "@/components/LanguageProvider";
import { formatYen } from "@/lib/periodic/format";
import type { PeriodicScheduleResponse } from "@/lib/periodic/types";

type Props = {
  schedule: PeriodicScheduleResponse;
  onEdit: () => void;
  onPause: () => void;
  onRestart: () => void;
  onDelete: () => void;
  busy?: boolean;
};

export function ScheduleCard({
  schedule,
  onEdit,
  onPause,
  onRestart,
  onDelete,
  busy,
}: Props) {
  const { t } = useLanguage();

  const categoryPath = schedule.category_l2_name
    ? `${schedule.category_l1_name ?? ""} › ${schedule.category_l2_name}`
    : (schedule.category_l1_name ?? "");

  const statusBadge =
    schedule.status === "active"
      ? null
      : schedule.status === "paused"
        ? t("periodicStatusPaused")
        : t("periodicStatusEnded");

  return (
    <article className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-gray-900">{schedule.name}</p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-gray-900">
            {formatYen(schedule.amount)}
          </p>
        </div>
        {statusBadge ? (
          <span
            className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
              schedule.status === "paused"
                ? "bg-amber-50 text-amber-800"
                : "bg-gray-100 text-gray-600"
            }`}
          >
            {statusBadge}
          </span>
        ) : null}
      </div>

      <div className="mt-3 space-y-1 text-sm text-gray-600">
        <p>{schedule.recurrence_summary}</p>
        <p className="truncate">{categoryPath}</p>
        {schedule.status === "active" && schedule.next_run_date ? (
          <p className="text-gray-500">
            {t("periodicNextRun")}: {schedule.next_run_date}
          </p>
        ) : null}
        {schedule.pause_reason === "category_missing" ? (
          <p className="text-amber-700">{t("periodicCategoryMissing")}</p>
        ) : null}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={onEdit}
          className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700"
        >
          {t("edit")}
        </button>
        {schedule.status === "active" ? (
          <button
            type="button"
            disabled={busy}
            onClick={onPause}
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700"
          >
            {t("periodicPause")}
          </button>
        ) : null}
        {schedule.status === "paused" ? (
          <button
            type="button"
            disabled={busy || schedule.pause_reason === "category_missing"}
            onClick={onRestart}
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700 disabled:opacity-40"
          >
            {t("periodicRestart")}
          </button>
        ) : null}
        <button
          type="button"
          disabled={busy}
          onClick={onDelete}
          className="rounded-lg border border-red-100 px-3 py-1.5 text-xs font-medium text-red-600"
        >
          {t("delete")}
        </button>
      </div>
    </article>
  );
}
