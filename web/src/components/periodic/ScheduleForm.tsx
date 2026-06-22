"use client";

import { useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { fetchCategories } from "@/lib/categories/client";
import type { CategoryNode } from "@/lib/categories/types";
import type { TenantOption } from "@/lib/dashboard/tenants";
import {
  createPeriodicSchedule,
  defaultFormValues,
  previewNextRun,
  scheduleToFormValues,
  updatePeriodicSchedule,
  type ScheduleFormValues,
} from "@/lib/periodic/client";
import type { PeriodicScheduleResponse } from "@/lib/periodic/types";
import { EndConditionFields } from "@/components/periodic/EndConditionFields";
import { RecurrenceFields } from "@/components/periodic/RecurrenceFields";

type Props = {
  tenant: TenantOption;
  schedule?: PeriodicScheduleResponse | null;
  onClose: () => void;
  onSaved: () => void;
};

export function ScheduleForm({ tenant, schedule, onClose, onSaved }: Props) {
  const { t } = useLanguage();
  const [values, setValues] = useState<ScheduleFormValues>(() =>
    schedule ? scheduleToFormValues(schedule) : defaultFormValues(),
  );
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [nextPreview, setNextPreview] = useState<string | null>(null);

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

  useEffect(() => {
    let cancelled = false;
    void previewNextRun({
      recurrence: values.recurrence,
      start_date: values.start_date,
      timezone: values.timezone,
      after: values.start_date,
    })
      .then((data) => {
        if (!cancelled) setNextPreview(data.next_run_date);
      })
      .catch(() => {
        if (!cancelled) setNextPreview(null);
      });
    return () => {
      cancelled = true;
    };
  }, [values.recurrence, values.start_date, values.timezone]);

  function validateClient(): string | null {
    if (!values.name.trim()) return t("periodicErrorName");
    const amount = Number(values.amount);
    if (!Number.isFinite(amount) || amount <= 0) return t("periodicErrorAmount");
    if (!values.category_node_id) return t("periodicErrorCategory");
    if (values.end_kind === "on_date" && !values.end_date) {
      return t("periodicErrorEndDate");
    }
    if (values.end_kind === "amount_cap" && !Number(values.end_amount_cap)) {
      return t("periodicErrorEndAmount");
    }
    if (values.end_kind === "repeat_count" && !Number(values.end_repeat_limit)) {
      return t("periodicErrorEndRepeat");
    }
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const clientError = validateClient();
    if (clientError) {
      setError(clientError);
      return;
    }

    setSaving(true);
    setError(null);

    const payload: Record<string, unknown> = {
      tenant_type: tenant.tenantType,
      tenant_id: tenant.tenantId,
      name: values.name.trim(),
      amount: Number(values.amount),
      assigned_level: values.assigned_level,
      category_node_id: values.category_node_id,
      recurrence: values.recurrence,
      start_date: values.start_date,
      timezone: values.timezone,
      end_kind: values.end_kind,
      end_date: values.end_kind === "on_date" ? values.end_date : null,
      end_amount_cap:
        values.end_kind === "amount_cap" ? Number(values.end_amount_cap) : null,
      end_repeat_limit:
        values.end_kind === "repeat_count"
          ? Number(values.end_repeat_limit)
          : null,
    };

    try {
      if (schedule) {
        await updatePeriodicSchedule(schedule.id, payload);
      } else {
        await createPeriodicSchedule(payload);
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setSaving(false);
    }
  }

  const l1Nodes = categories.filter((n) => n.level === 1);
  const l2Nodes = categories.filter((n) => n.level === 2);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center">
      <form
        onSubmit={handleSubmit}
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-white p-4 shadow-xl sm:rounded-2xl"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            {schedule ? t("periodicEditTitle") : t("periodicCreateTitle")}
          </h2>
          <button type="button" onClick={onClose} className="text-sm text-gray-500">
            {t("cancel")}
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-700">{t("periodicName")}</label>
            <input
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              value={values.name}
              onChange={(e) => setValues({ ...values, name: e.target.value })}
              placeholder={t("periodicNamePlaceholder")}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">{t("periodicAmount")}</label>
            <input
              type="number"
              min={1}
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              value={values.amount}
              onChange={(e) => setValues({ ...values, amount: e.target.value })}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">{t("periodicCategory")}</label>
            <select
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              value={values.category_node_id}
              onChange={(e) => {
                const id = e.target.value;
                const node = categories.find((n) => n.id === id);
                setValues({
                  ...values,
                  category_node_id: id,
                  assigned_level: node?.level === 1 ? 1 : 2,
                });
              }}
            >
              <option value="">{t("selectTransferTarget")}</option>
              {l1Nodes.map((l1) => (
                <optgroup key={l1.id} label={l1.name_ja}>
                  <option value={l1.id}>{l1.name_ja} (L1)</option>
                  {l2Nodes
                    .filter((l2) => l2.parent_id === l1.id)
                    .map((l2) => (
                      <option key={l2.id} value={l2.id}>
                        {l2.name_ja}
                      </option>
                    ))}
                </optgroup>
              ))}
            </select>
          </div>

          <RecurrenceFields
            value={values.recurrence}
            onChange={(recurrence) => setValues({ ...values, recurrence })}
          />

          <div>
            <label className="text-sm font-medium text-gray-700">{t("periodicStartDate")}</label>
            <input
              type="date"
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              value={values.start_date}
              onChange={(e) => setValues({ ...values, start_date: e.target.value })}
            />
          </div>

          <EndConditionFields
            endKind={values.end_kind}
            endDate={values.end_date}
            endAmountCap={values.end_amount_cap}
            endRepeatLimit={values.end_repeat_limit}
            onChange={(patch) => setValues({ ...values, ...patch })}
          />

          {nextPreview ? (
            <p className="text-xs text-gray-500">
              {t("periodicNextPreview")}: {nextPreview}
            </p>
          ) : null}

          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          <button
            type="submit"
            disabled={saving}
            className="w-full rounded-lg bg-gray-900 py-2.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? t("saving") : t("periodicSave")}
          </button>
        </div>
      </form>
    </div>
  );
}
