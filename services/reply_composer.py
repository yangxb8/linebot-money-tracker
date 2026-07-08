"""Compose simplified LINE expense confirmation replies from independent sections."""

from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal
from typing import List, Optional


def _normalize_language(code: Optional[str]) -> str:
    if not code:
        return 'ja'
    lowered = code.strip().lower()
    if lowered.startswith('zh'):
        return 'zh'
    if lowered.startswith('en'):
        return 'en'
    if lowered.startswith('ja'):
        return 'ja'
    return 'ja'


def join_sections(sections: List[str]) -> str:
    """Join non-empty sections with a blank line separator."""
    parts = [section.strip() for section in sections if section and section.strip()]
    return '\n\n'.join(parts)


def _format_amount_value(amount: Decimal) -> str:
    quantized = amount.quantize(Decimal('0.01'))
    if quantized == quantized.to_integral_value():
        return str(int(quantized))
    return format(quantized, 'f').rstrip('0').rstrip('.')


def _money_prefix(currency: str) -> str:
    normalized = (currency or '').strip().upper()
    if normalized in ('', 'JPY', '¥'):
        return '¥'
    return f'{normalized} '


def format_money(amount: object, currency: str = 'JPY') -> str:
    """Format amount with a consistent currency prefix for emphasis."""
    try:
        value = Decimal(str(amount))
    except Exception:
        return str(amount)
    return f'{_money_prefix(currency)}{_format_amount_value(value)}'


def _items_total(items: List[dict]) -> tuple[Decimal, str]:
    total = Decimal('0')
    currency = ''
    for item in items:
        total += Decimal(str(item.get('amount', 0)))
        if not currency:
            raw = item.get('currency')
            if raw:
                currency = str(raw).strip()
    return total.quantize(Decimal('0.01')), currency or 'JPY'


def _category_subtotals(items: List[dict]) -> List[tuple[str, Decimal, str]]:
    buckets: OrderedDict[str, tuple[Decimal, str]] = OrderedDict()
    for item in items:
        path = str(item.get('category_guess_path') or '不明').strip() or '不明'
        amount = Decimal(str(item.get('amount', 0))).quantize(Decimal('0.01'))
        currency = str(item.get('currency') or 'JPY').strip() or 'JPY'
        if path in buckets:
            prev_amount, prev_currency = buckets[path]
            buckets[path] = (prev_amount + amount, prev_currency or currency)
        else:
            buckets[path] = (amount, currency)
    return [(path, amount, currency) for path, (amount, currency) in buckets.items()]


def _single_item_summary(item: dict, *, language: str) -> str:
    description = str(item.get('description', 'Expense')).strip() or 'Expense'
    amount = item.get('amount', '')
    currency = str(item.get('currency') or 'JPY').strip() or 'JPY'
    category = str(item.get('category_guess_path') or '').strip()
    money = format_money(amount, currency)
    if category:
        return f'✅ {description} {money} · {category}'
    return f'✅ {description} {money}'


def _multi_item_summary(items: List[dict], *, language: str) -> str:
    lang = _normalize_language(language)
    total, currency = _items_total(items)
    money = format_money(total, currency)
    count = len(items)
    if lang == 'zh':
        return f'✅ 合计 {money}（{count}件）'
    if lang == 'en':
        return f'✅ Total {money} ({count} item(s))'
    return f'✅ 合計 {money}（{count}件）'


def _subtotal_section(items: List[dict], *, language: str) -> Optional[str]:
    if len(items) <= 1:
        return None
    lines = [
        f'{path} {format_money(amount, currency)}'
        for path, amount, currency in _category_subtotals(items)
    ]
    return '\n'.join(lines) if lines else None


def _item_details_section(items: List[dict], *, language: str) -> Optional[str]:
    lines: List[str] = []
    for index, item in enumerate(items, start=1):
        description = str(item.get('description', 'Expense')).strip() or 'Expense'
        amount = item.get('amount', '')
        currency = str(item.get('currency') or 'JPY').strip() or 'JPY'
        category = str(item.get('category_guess_path') or '').strip()
        money = format_money(amount, currency)
        if category:
            lines.append(f'{index}) {description} {money} · {category}')
        else:
            lines.append(f'{index}) {description} {money}')
    return '\n'.join(lines) if lines else None


def compose_confirmation_reply(
    items: List[dict],
    *,
    language: str = 'ja',
    show_item_details: bool = False,
    logged_by_line: Optional[str] = None,
) -> Optional[str]:
    if not items:
        return None

    lang = _normalize_language(language)
    sections: List[str] = []

    if logged_by_line:
        sections.append(logged_by_line.strip())

    if len(items) == 1:
        sections.append(_single_item_summary(items[0], language=lang))
    else:
        sections.append(_multi_item_summary(items, language=lang))
        subtotals = _subtotal_section(items, language=lang)
        if subtotals:
            sections.append(subtotals)

    if show_item_details and len(items) > 1:
        details = _item_details_section(items, language=lang)
        if details:
            sections.append(details)

    return join_sections(sections)
