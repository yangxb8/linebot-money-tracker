export type ValidationResult = { ok: true } | { ok: false; error: string };

export function isValidProductUrl(value: unknown): boolean {
  const raw = String(value ?? "").trim();
  if (!raw) return true;

  try {
    const url = new URL(raw);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function validateName(value: unknown): ValidationResult {
  if (!String(value ?? "").trim()) {
    return { ok: false, error: "name_required" };
  }
  return { ok: true };
}

function validateAmount(value: unknown): ValidationResult {
  const amount = Number(value);
  if (!Number.isFinite(amount) || amount <= 0) {
    return { ok: false, error: "invalid_amount" };
  }
  return { ok: true };
}

function validateCategory(value: unknown): ValidationResult {
  if (!String(value ?? "").trim()) {
    return { ok: false, error: "category_required" };
  }
  return { ok: true };
}

function validateProductUrl(value: unknown): ValidationResult {
  if (!isValidProductUrl(value)) {
    return { ok: false, error: "invalid_product_url" };
  }
  return { ok: true };
}

export function validateCreatePayload(
  body: Record<string, unknown>,
): ValidationResult {
  const name = validateName(body.name);
  if (!name.ok) return name;

  const amount = validateAmount(body.amount);
  if (!amount.ok) return amount;

  const category = validateCategory(body.category_node_id);
  if (!category.ok) return category;

  return validateProductUrl(body.product_url);
}

export function validateUpdatePayload(
  body: Record<string, unknown>,
): ValidationResult {
  if (body.name !== undefined) {
    const name = validateName(body.name);
    if (!name.ok) return name;
  }

  if (body.amount !== undefined) {
    const amount = validateAmount(body.amount);
    if (!amount.ok) return amount;
  }

  if (body.category_node_id !== undefined) {
    const category = validateCategory(body.category_node_id);
    if (!category.ok) return category;
  }

  return validateProductUrl(body.product_url);
}

export function validateReorderPayload(
  body: Record<string, unknown>,
): ValidationResult {
  if (!Array.isArray(body.ordered_ids) || body.ordered_ids.length === 0) {
    return { ok: false, error: "ordered_ids_required" };
  }

  if (
    body.ordered_ids.some(
      (id) => typeof id !== "string" || id.trim().length === 0,
    )
  ) {
    return { ok: false, error: "invalid_ordered_ids" };
  }

  return { ok: true };
}

export function validateExecutePayload(
  body: Record<string, unknown>,
): ValidationResult {
  if (body.name !== undefined) {
    const name = validateName(body.name);
    if (!name.ok) return name;
  }

  if (body.amount !== undefined) {
    const amount = validateAmount(body.amount);
    if (!amount.ok) return amount;
  }

  if (body.category_node_id !== undefined) {
    const category = validateCategory(body.category_node_id);
    if (!category.ok) return category;
  }

  if (body.expense_date !== undefined && !String(body.expense_date).slice(0, 10)) {
    return { ok: false, error: "expense_date_required" };
  }

  return { ok: true };
}
