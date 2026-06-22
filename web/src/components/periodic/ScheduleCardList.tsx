"use client";

import { useLanguage } from "@/components/LanguageProvider";
import type { PeriodicScheduleResponse } from "@/lib/periodic/types";
import { ScheduleCard } from "@/components/periodic/ScheduleCard";

type Props = {
  schedules: PeriodicScheduleResponse[];
  loading: boolean;
  error: string | null;
  busyId: string | null;
  onRetry: () => void;
  onCreate: () => void;
  onEdit: (schedule: PeriodicScheduleResponse) => void;
  onPause: (schedule: PeriodicScheduleResponse) => void;
  onRestart: (schedule: PeriodicScheduleResponse) => void;
  onDelete: (schedule: PeriodicScheduleResponse) => void;
};

export function ScheduleCardList({
  schedules,
  loading,
  error,
  busyId,
  onRetry,
  onCreate,
  onEdit,
  onPause,
  onRestart,
  onDelete,
}: Props) {
  const { t } = useLanguage();

  if (loading) {
    return (
      <p className="py-12 text-center text-sm text-gray-500">{t("loading")}</p>
    );
  }

  if (error) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-gray-600">{t("errorGeneric")}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 text-sm font-medium text-gray-900 underline"
        >
          {t("retry")}
        </button>
      </div>
    );
  }

  if (schedules.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-200 bg-white p-8 text-center">
        <p className="text-sm text-gray-600">{t("periodicEmpty")}</p>
        <button
          type="button"
          onClick={onCreate}
          className="mt-4 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white"
        >
          {t("periodicCreateTitle")}
        </button>
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {schedules.map((schedule) => (
        <li key={schedule.id}>
          <ScheduleCard
            schedule={schedule}
            busy={busyId === schedule.id}
            onEdit={() => onEdit(schedule)}
            onPause={() => onPause(schedule)}
            onRestart={() => onRestart(schedule)}
            onDelete={() => onDelete(schedule)}
          />
        </li>
      ))}
    </ul>
  );
}
