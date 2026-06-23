"use client";

import { useCallback, useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { useTenant } from "@/components/TenantProvider";
import {
  deletePeriodicSchedule,
  fetchPeriodicSchedules,
  pausePeriodicSchedule,
  restartPeriodicSchedule,
} from "@/lib/periodic/client";
import type { PeriodicScheduleResponse } from "@/lib/periodic/types";
import { ScheduleCardList } from "@/components/periodic/ScheduleCardList";
import { ScheduleForm } from "@/components/periodic/ScheduleForm";

export function PeriodicExpensesManager() {
  const { t } = useLanguage();
  const { selectedTenant } = useTenant();
  const [schedules, setSchedules] = useState<PeriodicScheduleResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<PeriodicScheduleResponse | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!selectedTenant) return;
    setLoading(true);
    setError(null);
    try {
      const rows = await fetchPeriodicSchedules(selectedTenant);
      setSchedules(rows);
    } catch {
      setError("fetch_failed");
    } finally {
      setLoading(false);
    }
  }, [selectedTenant]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handlePause(schedule: PeriodicScheduleResponse) {
    setBusyId(schedule.id);
    try {
      await pausePeriodicSchedule(schedule.id);
      await load();
    } catch {
      setError("action_failed");
    } finally {
      setBusyId(null);
    }
  }

  async function handleRestart(schedule: PeriodicScheduleResponse) {
    setBusyId(schedule.id);
    try {
      await restartPeriodicSchedule(schedule.id);
      await load();
    } catch {
      setError("action_failed");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(schedule: PeriodicScheduleResponse) {
    if (!window.confirm(t("periodicDeleteConfirm"))) return;
    setBusyId(schedule.id);
    try {
      await deletePeriodicSchedule(schedule.id);
      await load();
    } catch {
      setError("action_failed");
    } finally {
      setBusyId(null);
    }
  }

  if (!selectedTenant) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">{t("periodicSubtitle")}</p>
        <button
          type="button"
          onClick={() => {
            setEditing(null);
            setFormOpen(true);
          }}
          className="rounded-lg bg-gray-900 px-3 py-2 text-sm font-medium text-white"
        >
          {t("add")}
        </button>
      </div>

      <ScheduleCardList
        schedules={schedules}
        loading={loading}
        error={error}
        busyId={busyId}
        onRetry={() => void load()}
        onCreate={() => {
          setEditing(null);
          setFormOpen(true);
        }}
        onEdit={(schedule) => {
          setEditing(schedule);
          setFormOpen(true);
        }}
        onPause={(schedule) => void handlePause(schedule)}
        onRestart={(schedule) => void handleRestart(schedule)}
        onDelete={(schedule) => void handleDelete(schedule)}
      />

      {formOpen ? (
        <ScheduleForm
          tenant={selectedTenant}
          schedule={editing}
          onClose={() => {
            setFormOpen(false);
            setEditing(null);
          }}
          onSaved={() => void load()}
        />
      ) : null}
    </div>
  );
}
