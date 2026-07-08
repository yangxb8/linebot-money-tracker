# Contract: LINE confirmation reply composition (simplified)

**Feature**: 017-simplify-expense-reply  
**Purpose**: Define the user-visible structure of the simplified confirmation reply and how sections are composed.

## Principles

- Keep the default confirmation skimmable (receipt-style).
- Compose the final reply from independent sections, joined with clear separators.
- Do not include always-on instructions; provide help only when asked.

## Sections (ordered)

1. **Pacing warning** (optional)
2. **Confirmation summary** (required)
3. **Category subtotals** (optional; default for multi-item)
4. **Per-item details** (optional; controlled by preference)
5. **Footer/help hint** (optional; keep short)

## Separator rules

- When more than one section exists, separate sections with a blank line.
- Avoid multi-paragraph blocks; each section should be 1–4 lines.

## Confirmation summary format

### Single-item (default)

- `✅ {merchant_or_description} ¥{amount} · {category_path}`

### Multi-item (default)

- `✅ 合計 ¥{total}（{count}件）` (or localized equivalent)

## Category subtotal format (default for multi-item)

One line per category:

- `{category_path} ¥{subtotal}`

## Per-item details format (when enabled)

One line per item (compact):

- `{n}) {description} ¥{amount} · {category_path}`

## Example outputs (implemented)

Single item (ja):

```text
✅ まいばすけっと ¥3210 · 食費 > 食料品
```

Multi-item default (ja):

```text
✅ 合計 ¥5430（3件）
食費 > 食料品 ¥3210
生活 > 日用品 ¥2220
```

Multi-item with per-item details enabled (ja):

```text
✅ 合計 ¥5430（3件）
食費 > 食料品 ¥3210
生活 > 日用品 ¥2220

1) まいばすけっと ¥3210 · 食費 > 食料品
2) ドラッグストア ¥890 · 生活 > 日用品
3) コンビニ ¥1330 · 生活 > 日用品
```

## Help behavior (out of band)

Help responses are not part of confirmations. When the user asks how-to questions, return a short actionable tip (language-matched).
