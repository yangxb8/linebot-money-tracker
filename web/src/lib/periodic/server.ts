import { createClient } from "@/lib/supabase/server";
import { computeFirstRunDate, computeNextRunOnOrAfter } from "@/lib/periodic/recurrence";
import type {
  PeriodicScheduleResponse,
  PeriodicScheduleRow,
  RecurrenceRule,
} from "@/lib/periodic/types";
import { formatRecurrenceSummary } from "@/lib/periodic/format";
import type { Locale } from "@/lib/i18n/messages";

export async function requirePeriodicUser() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    throw new Response("Unauthorized", { status: 401 });
  }
  return supabase;
}

export async function resolveCategoryAssignment(
  tenantType: string,
  tenantId: string,
  categoryNodeId: string,
): Promise<{
  assigned_level: number;
  category_node_id: string;
  category_l1_id: string;
  category_l2_id: string | null;
}> {
  const supabase = await requirePeriodicUser();
  const { data: node, error } = await supabase
    .from("category_nodes")
    .select("id, level, parent_id")
    .eq("id", categoryNodeId)
    .eq("tenant_type", tenantType)
    .eq("tenant_id", tenantId)
    .maybeSingle();

  if (error || !node) {
    throw new Response("category_not_found", { status: 404 });
  }

  if (node.level === 1) {
    return {
      assigned_level: 1,
      category_node_id: node.id,
      category_l1_id: node.id,
      category_l2_id: null,
    };
  }

  if (node.level === 2 && node.parent_id) {
    return {
      assigned_level: 2,
      category_node_id: node.id,
      category_l1_id: node.parent_id,
      category_l2_id: node.id,
    };
  }

  throw new Response("invalid_category_level", { status: 400 });
}

export function computeInitialNextRunDate(
  recurrence: RecurrenceRule,
  startDate: string,
  timezone: string,
): string {
  return computeFirstRunDate(recurrence, startDate, timezone);
}

export function computeNextRunAfterEdit(
  recurrence: RecurrenceRule,
  startDate: string,
  timezone: string,
  fromDate: string,
): string | null {
  return computeNextRunOnOrAfter(recurrence, startDate, fromDate, timezone);
}

export async function enrichSchedules(
  rows: PeriodicScheduleRow[],
  locale: Locale = "ja",
): Promise<PeriodicScheduleResponse[]> {
  if (rows.length === 0) return [];

  const supabase = await requirePeriodicUser();
  const categoryIds = new Set<string>();
  for (const row of rows) {
    categoryIds.add(row.category_l1_id);
    if (row.category_l2_id) categoryIds.add(row.category_l2_id);
  }

  const { data: categories } = await supabase
    .from("category_nodes")
    .select("id, name_ja")
    .in("id", [...categoryIds]);

  const nameById = new Map(
    (categories ?? []).map((c: { id: string; name_ja: string }) => [c.id, c.name_ja]),
  );

  return rows.map((row) => ({
    ...row,
    recurrence: row.recurrence as RecurrenceRule,
    recurrence_summary: formatRecurrenceSummary(row.recurrence as RecurrenceRule, locale),
    category_l1_name: nameById.get(row.category_l1_id) ?? null,
    category_l2_name: row.category_l2_id
      ? (nameById.get(row.category_l2_id) ?? null)
      : null,
  }));
}

export function mapScheduleRow(row: Record<string, unknown>): PeriodicScheduleRow {
  return {
    id: String(row.id),
    tenant_type: String(row.tenant_type),
    tenant_id: String(row.tenant_id),
    name: String(row.name),
    amount: Number(row.amount),
    currency: String(row.currency),
    assigned_level: Number(row.assigned_level),
    category_node_id: String(row.category_node_id),
    category_l1_id: String(row.category_l1_id),
    category_l2_id: row.category_l2_id ? String(row.category_l2_id) : null,
    recurrence: row.recurrence as RecurrenceRule,
    start_date: String(row.start_date).slice(0, 10),
    timezone: String(row.timezone),
    end_kind: row.end_kind as PeriodicScheduleRow["end_kind"],
    end_date: row.end_date ? String(row.end_date).slice(0, 10) : null,
    end_amount_cap: row.end_amount_cap != null ? Number(row.end_amount_cap) : null,
    end_repeat_limit: row.end_repeat_limit != null ? Number(row.end_repeat_limit) : null,
    status: row.status as PeriodicScheduleRow["status"],
    pause_reason: row.pause_reason ? String(row.pause_reason) : null,
    next_run_date: row.next_run_date ? String(row.next_run_date).slice(0, 10) : null,
    occurrence_count: Number(row.occurrence_count),
    cumulative_amount: Number(row.cumulative_amount),
    created_by_line_user_id: String(row.created_by_line_user_id),
    created_at: String(row.created_at),
    updated_at: String(row.updated_at),
  };
}

export async function fetchLineUserId(supabase: Awaited<ReturnType<typeof requirePeriodicUser>>) {
  const { data, error } = await supabase
    .from("line_auth_identities")
    .select("line_user_id")
    .maybeSingle();
  if (error || !data?.line_user_id) {
    throw new Response("Unauthorized", { status: 401 });
  }
  return data.line_user_id as string;
}
