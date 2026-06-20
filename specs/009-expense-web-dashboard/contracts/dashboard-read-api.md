# Contract: Dashboard Read API

**Feature**: 009-expense-web-dashboard  
**Access**: Supabase JS client (`@supabase/supabase-js`) with user session — **no custom REST API** in MVP

## Client initialization

```typescript
const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);
```

Session attached automatically via SSR cookies after LINE auth.

## Operation: list_user_tenants

**Purpose**: Populate tenant switcher.

### Query 1 — personal (implicit)

Always available when `current_line_user_id()` is non-null:

| tenant_type | tenant_id |
| ----------- | --------- |
| `user` | `line_user_id` from `line_auth_identities` |

### Query 2 — shared tenants

```typescript
const { data } = await supabase
  .from('tenant_chat_members')
  .select('tenant_type, tenant_id, last_seen_at')
  .order('last_seen_at', { ascending: false });
```

RLS returns only rows for the signed-in user.

### Response shape (client)

```typescript
type TenantOption = {
  tenantType: 'user' | 'group' | 'room';
  tenantId: string;
  labelKey: 'personal' | 'group' | 'room'; // i18n
  shortId: string; // last 6 chars of tenant_id for display
};
```

## Operation: list_expenses

**Table/View**: `v_expenses_enriched`

```typescript
const pageSize = 20;
const { data, error } = await supabase
  .from('v_expenses_enriched')
  .select(
    'id, expense_date, description, amount, currency, ' +
    'category_name_ja, category_l1_name, category_l2_name, category_l3_name, ' +
    'logged_by_line_user_id, tenant_type, tenant_id'
  )
  .eq('tenant_type', selectedTenantType)
  .eq('tenant_id', selectedTenantId)
  .eq('currency', 'JPY')
  .is('deleted_at', null)
  .order('expense_date', { ascending: false })
  .order('created_at', { ascending: false })
  .range(offset, offset + pageSize - 1);
```

### Pagination

- Initial `offset = 0`.
- "Load more" increments `offset` by `pageSize`.
- Stop when `data.length < pageSize`.

### Row display mapping

| Column | UI field |
| ------ | -------- |
| `expense_date` | Localized date (JST) |
| `description` | Primary text |
| `amount` | `¥{amount.toLocaleString('ja-JP')}` |
| `category_name_ja` or deepest non-null `category_lN_name` | Category chip |

## Operation: get_user_locale

```typescript
const { data } = await supabase
  .from('user_language_preferences')
  .select('reply_language')
  .maybeSingle();
// fallback 'ja'
```

## Errors

| Supabase code | UI behavior |
| ------------- | ----------- |
| `PGRST116` (no rows) | Empty state |
| `401` / JWT expired | Redirect to login |
| Network error | Retry button |

## Out of scope (MVP)

- `INSERT` / `UPDATE` / `DELETE` on `expenses`
- Aggregate RPCs (`monthly_expense_total`)
- Realtime subscriptions

## Future extension point

If queries become complex (cross-tenant search, exports), add Supabase Edge Functions without changing the tenant authorization rules documented here.
