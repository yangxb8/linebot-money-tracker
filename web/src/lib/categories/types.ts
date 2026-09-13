export type CategoryNode = {
  id: string;
  code: string;
  name_ja: string;
  level: 1 | 2;
  parent_id: string | null;
  sort_order: number;
  pace_warning_enabled: boolean;
  expense_count: number;
  deletable: boolean;
};

export type CategoryTreeResponse = {
  initialized: boolean;
  nodes: CategoryNode[];
};
