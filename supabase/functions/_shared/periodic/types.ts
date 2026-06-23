export type ScheduleStatus = "active" | "paused" | "ended";

export type EndKind = "never" | "on_date" | "amount_cap" | "repeat_count";

export type RecurrenceKind =
  | "interval_days"
  | "monthly_days"
  | "monthly_boundary"
  | "every_n_months"
  | "every_n_weeks";

export type MonthlyBoundary = "first" | "last";

export type IntervalDaysRecurrence = {
  kind: "interval_days";
  interval: number;
};

export type MonthlyDaysRecurrence = {
  kind: "monthly_days";
  days: number[];
};

export type MonthlyBoundaryRecurrence = {
  kind: "monthly_boundary";
  boundary: MonthlyBoundary;
};

export type EveryNMonthsRecurrence = {
  kind: "every_n_months";
  interval: number;
  day: number;
};

export type EveryNWeeksRecurrence = {
  kind: "every_n_weeks";
  interval: number;
  weekdays: number[];
};

export type RecurrenceRule =
  | IntervalDaysRecurrence
  | MonthlyDaysRecurrence
  | MonthlyBoundaryRecurrence
  | EveryNMonthsRecurrence
  | EveryNWeeksRecurrence;

export type PeriodicScheduleRow = {
  id: string;
  tenant_type: string;
  tenant_id: string;
  name: string;
  amount: number;
  currency: string;
  assigned_level: number;
  category_node_id: string;
  category_l1_id: string;
  category_l2_id: string | null;
  recurrence: RecurrenceRule;
  start_date: string;
  timezone: string;
  end_kind: EndKind;
  end_date: string | null;
  end_amount_cap: number | null;
  end_repeat_limit: number | null;
  status: ScheduleStatus;
  pause_reason: string | null;
  next_run_date: string | null;
  occurrence_count: number;
  cumulative_amount: number;
  created_by_line_user_id: string;
  created_at: string;
  updated_at: string;
};

export type ProcessAction = {
  schedule_id: string;
  occurrence_date: string;
  next_run_date: string | null;
  end: boolean;
  skip_occurrence?: boolean;
};
