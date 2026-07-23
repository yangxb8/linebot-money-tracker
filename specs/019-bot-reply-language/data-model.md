# Data Model: Bot Reply Language Override

## Entity: Tenant settings (existing, extended)

**Primary key**: (`tenant_type`, `tenant_id`)

**New field**
- `reply_language` (text, nullable): Forced bot reply language for the tenant.
  - Allowed values when set: `en`, `ja`, `zh`
  - `NULL` means Default → use system/LINE-profile personal language resolution

**Validation**
- CHECK constraint or application validation restricting non-null values to `en|ja|zh`
- Unknown values treated as unset at read time (fail-open)

**Lifecycle**
1. Unset (`NULL`) → system language
2. Set (`en`/`ja`/`zh`) → forced language for tenant replies
3. Reset to Default → `NULL`
