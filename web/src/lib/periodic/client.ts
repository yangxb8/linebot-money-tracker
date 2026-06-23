import type { EndKind, PeriodicScheduleResponse, RecurrenceRule } from "@/lib/periodic/types";
import type { TenantOption } from "@/lib/dashboard/tenants";

export async function fetchPeriodicSchedules(
  tenant: TenantOption,
): Promise<PeriodicScheduleResponse[]> {
  const params = new URLSearchParams({
    tenant_type: tenant.tenantType,
    tenant_id: tenant.tenantId,
  });
  const response = await fetch(`/api/periodic-expenses?${params.toString()}`);
  if (!response.ok) {
    throw new Error("fetch_failed");
  }
  const data = await response.json();
  return data.schedules ?? [];
}

export async function createPeriodicSchedule(payload: Record<string, unknown>) {
  const response = await fetch("/api/periodic-expenses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error ?? "create_failed");
  }
  return response.json() as Promise<PeriodicScheduleResponse>;
}

export async function updatePeriodicSchedule(
  id: string,
  payload: Record<string, unknown>,
) {
  const response = await fetch(`/api/periodic-expenses/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error ?? "update_failed");
  }
  return response.json() as Promise<PeriodicScheduleResponse>;
}

export async function pausePeriodicSchedule(id: string) {
  const response = await fetch(`/api/periodic-expenses/${id}/pause`, {
    method: "POST",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error ?? "pause_failed");
  }
  return response.json();
}

export async function restartPeriodicSchedule(
  id: string,
  payload?: Record<string, unknown>,
) {
  const response = await fetch(`/api/periodic-expenses/${id}/restart`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload ?? {}),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error ?? "restart_failed");
  }
  return response.json() as Promise<PeriodicScheduleResponse>;
}

export async function deletePeriodicSchedule(id: string) {
  const response = await fetch(`/api/periodic-expenses/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error ?? "delete_failed");
  }
}

export async function previewNextRun(payload: {
  recurrence: RecurrenceRule;
  start_date: string;
  timezone: string;
  after?: string;
}) {
  const response = await fetch("/api/periodic-expenses/preview-next", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("preview_failed");
  }
  return response.json() as Promise<{
    next_run_date: string | null;
    following_run_date: string | null;
  }>;
}

export type ScheduleFormValues = {
  name: string;
  amount: string;
  category_node_id: string;
  assigned_level: 1 | 2;
  recurrence: RecurrenceRule;
  start_date: string;
  timezone: string;
  end_kind: EndKind;
  end_date: string;
  end_amount_cap: string;
  end_repeat_limit: string;
};

export function defaultFormValues(): ScheduleFormValues {
  const today = new Date().toISOString().slice(0, 10);
  return {
    name: "",
    amount: "",
    category_node_id: "",
    assigned_level: 2,
    recurrence: { kind: "monthly_days", days: [1] },
    start_date: today,
    timezone: "Asia/Tokyo",
    end_kind: "never",
    end_date: "",
    end_amount_cap: "",
    end_repeat_limit: "",
  };
}

export function scheduleToFormValues(
  schedule: PeriodicScheduleResponse,
): ScheduleFormValues {
  return {
    name: schedule.name,
    amount: String(schedule.amount),
    category_node_id: schedule.category_node_id,
    assigned_level: schedule.assigned_level as 1 | 2,
    recurrence: schedule.recurrence,
    start_date: schedule.start_date,
    timezone: schedule.timezone,
    end_kind: schedule.end_kind,
    end_date: schedule.end_date ?? "",
    end_amount_cap:
      schedule.end_amount_cap != null ? String(schedule.end_amount_cap) : "",
    end_repeat_limit:
      schedule.end_repeat_limit != null ? String(schedule.end_repeat_limit) : "",
  };
}
