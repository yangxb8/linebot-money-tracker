# Data Model: Simplify LINE expense confirmation replies

**Feature**: [spec.md](./spec.md)  
**Created**: 2026-07-08

This feature primarily changes **how confirmation replies are rendered**. It introduces one new persisted preference so users/tenants can choose whether confirmations include per-item detail.

## Entities

### Bot behavior preference (confirmation display)

**Represents**: A stored preference controlling how expense confirmations are displayed in LINE.

**Attributes**:
- **Scope**: Tenant-scoped (applies to personal `user` tenants and shared `group/room` tenants).
- **Preference key**: `confirmation_show_item_details`
- **Preference value**: boolean
  - `false` (default): show compact receipt line for single item; show category subtotals for multi-item
  - `true`: include per-item detail in confirmation replies (in addition to subtotals where applicable)

**Relationships**:
- Belongs to a tenant (personal or shared).

**Validation rules**:
- Missing preference implies default behavior (`false`).
- Preference must not affect persistence or reply-edit safety; it only affects formatting.

## Derived / transient state (not persisted)

### Reply composition sections

**Represents**: Independently constructed reply sections that are joined to form the final outbound reply.

**Examples**:
- pacing/budget warning section
- compact confirmation summary section
- subtotal section (category rows)
- optional item detail section
- footer/help section

### Category guess confirmation state

**Represents**: A short-lived interaction state where an edit is not applied until the user confirms a guessed category.

**Rules**:
- Bot must present the guessed category path and require explicit confirmation (`YES`) before applying changes.
- If user does not confirm, no edit is applied.

## Notes on existing data

The feature relies on existing confirmation linkage (outbound confirmation message id + snapshot) for reply-edit safety, and on the existing category taxonomy for mapping user-entered category text to a guessed category.
