export type WishListStatus = "active" | "executed";
export type WishListSort = "priority" | "created" | "price";
export type WishListOrder = "asc" | "desc";

export type WishListExpenseSummary = {
  id: string;
  description: string;
  amount: number;
  currency: string;
  expense_date: string;
  category_node_id: string;
  category_name: string | null;
};

export type WishListItem = {
  id: string;
  name: string;
  amount: number;
  currency: string;
  category_node_id: string;
  category_name: string | null;
  product_url: string | null;
  sort_order: number;
  status: WishListStatus;
  created_at: string;
  executed_expense_id: string | null;
  expense: WishListExpenseSummary | null;
};

export type WishListFormValues = {
  name: string;
  amount: string;
  category_node_id: string;
  product_url: string;
};

export type CreateWishListPayload = {
  tenant_type: string;
  tenant_id: string;
  name: string;
  amount: number;
  category_node_id: string;
  product_url?: string | null;
};

export type UpdateWishListPayload = {
  name?: string;
  amount?: number;
  category_node_id?: string;
  product_url?: string | null;
};

export type ExecuteWishListPayload = {
  tenant_type: string;
  tenant_id: string;
  name?: string;
  amount?: number;
  category_node_id?: string;
  expense_date?: string;
};
