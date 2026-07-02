"use client";

import { useEffect, useState } from "react";
import { Modal, ModalBody, ModalHeader } from "@/components/Modal";
import { useLanguage } from "@/components/LanguageProvider";
import { IsoDateInput } from "@/components/IsoDateInput";
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
import {
  parseRecurrenceForm,
  type RecurrenceFormErrors,
} from "@/lib/periodic/form";
import type { PeriodicScheduleResponse } from "@/lib/periodic/types";
import { EndConditionFields } from "@/components/periodic/EndConditionFields";
import { RecurrenceFields } from "@/components/periodic/RecurrenceFields";

type Props = {
  tenant: TenantOption;
  schedule?: PeriodicScheduleResponse | null;
  onClose: () => void;
  onSaved: () => void;
};

type FieldErrors = {
  name?: boolean;
  amount?: boolean;
  category?: boolean;
  start_date?: boolean;
  end_date?: boolean;
  end_amount_cap?: boolean;
  end_repeat_limit?: boolean;
  recurrence?: RecurrenceFormErrors;
};

function fieldClass(invalid?: boolean) {
  return `mt-1 w-full rounded-lg border px-3 py-2 text-sm ${
    invalid
      ? "border-red-500 focus:border-red-500 focus:outline-none focus:ring-2 focus:ring-red-200"
      : "border-gray-200"
  }`;
}

export function ScheduleForm({ tenant, schedule, onClose, onSaved }: Props) {
  const { t } = useLanguage();
  const [values, setValues] = useState<ScheduleFormValues>(() =>
    schedule ? scheduleToFormValues(schedule) : defaultFormValues(),
  );
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
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
    const parsed = parseRecurrenceForm(values.recurrence);
    if (!parsed.ok || !values.start_date) {
      setNextPreview(null);
      return () => {
        cancelled = true;
      };
    }

    void previewNextRun({
      recurrence: parsed.rule,
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
    const nextErrors: FieldErrors = {};

    if (!values.name.trim()) nextErrors.name = true;
    const amount = Number(values.amount);
    if (!Number.isFinite(amount) || amount <= 0) nextErrors.amount = true;
    if (!values.category_node_id) nextErrors.category = true;
    if (!values.start_date) nextErrors.start_date = true;

    if (values.end_kind === "on_date" && !values.end_date) {
      nextErrors.end_date = true;
    }
    if (values.end_kind === "amount_cap" && !Number(values.end_amount_cap)) {
      nextErrors.end_amount_cap = true;
    }
    if (values.end_kind === "repeat_count" && !Number(values.end_repeat_limit)) {
      nextErrors.end_repeat_limit = true;
    }

    const parsedRecurrence = parseRecurrenceForm(values.recurrence);
    if (!parsedRecurrence.ok) {
      nextErrors.recurrence = parsedRecurrence.fields;
    }

    setFieldErrors(nextErrors);

    if (nextErrors.name) return t("periodicErrorName");
    if (nextErrors.amount) return t("periodicErrorAmount");
    if (nextErrors.category) return t("periodicErrorCategory");
    if (nextErrors.start_date) return t("periodicErrorStartDate");
    if (nextErrors.end_date) return t("periodicErrorEndDate");
    if (nextErrors.end_amount_cap) return t("periodicErrorEndAmount");
    if (nextErrors.end_repeat_limit) return t("periodicErrorEndRepeat");
    if (!parsedRecurrence.ok) {
      return t(parsedRecurrence.errorKey as never);
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

    const parsedRecurrence = parseRecurrenceForm(values.recurrence);
    if (!parsedRecurrence.ok) {
      setError(t(parsedRecurrence.errorKey as never));
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
      recurrence: parsedRecurrence.rule,
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
    <Modal
      as="form"
      onClose={onClose}
      split
      formProps={{ onSubmit: handleSubmit }}
    >
      <ModalHeader>
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-gray-900">
            {schedule ? t("periodicEditTitle") : t("periodicCreateTitle")}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-lg px-2 py-1 text-sm text-gray-500 hover:bg-gray-50"
          >
            {t("cancel")}
          </button>
        </div>
      </ModalHeader>

      <ModalBody>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-700">{t("periodicName")}</label>
            <input
              className={fieldClass(fieldErrors.name)}
              value={values.name}
              onChange={(e) => setValues({ ...values, name: e.target.value })}
              placeholder={t("periodicNamePlaceholder")}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">{t("periodicAmount")}</label>
            <input
              type="text"
              inputMode="numeric"
              className={fieldClass(fieldErrors.amount)}
              value={values.amount}
              onChange={(e) => setValues({ ...values, amount: e.target.value })}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">{t("periodicCategory")}</label>
            <select
              className={fieldClass(fieldErrors.category)}
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
            fieldErrors={fieldErrors.recurrence}
            onChange={(recurrence) => setValues({ ...values, recurrence })}
          />

          <div>
            <label className="text-sm font-medium text-gray-700">{t("periodicStartDate")}</label>
            <IsoDateInput
              className="mt-1"
              value={values.start_date}
              invalid={fieldErrors.start_date}
              onChange={(start_date) => setValues({ ...values, start_date })}
            />
          </div>

          <EndConditionFields
            endKind={values.end_kind}
            endDate={values.end_date}
            endAmountCap={values.end_amount_cap}
            endRepeatLimit={values.end_repeat_limit}
            endDateInvalid={fieldErrors.end_date}
            endAmountCapInvalid={fieldErrors.end_amount_cap}
            endRepeatLimitInvalid={fieldErrors.end_repeat_limit}
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
      </ModalBody>
    </Modal>
  );
}
