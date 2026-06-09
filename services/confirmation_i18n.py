"""Localized strings for expense confirmation replies."""

from __future__ import annotations

from typing import Dict, List, Optional

ITEM_EMOJI = (
    '1️⃣',
    '2️⃣',
    '3️⃣',
    '4️⃣',
    '5️⃣',
    '6️⃣',
    '7️⃣',
    '8️⃣',
    '9️⃣',
    '🔟',
)

_STRINGS: Dict[str, Dict[str, str]] = {
    'ja': {
        'header': '検出した支出:',
        'logged_by': '記録者: {user_id}',
        'category_guess': 'カテゴリ（推測）: {path}',
        'pick_another': '確認するか、別のカテゴリを選んでください:',
        'instructions': (
            'このメッセージに返信して編集できます。'
            '項目番号＋変更（例: 2 3800円 / 2 取消）、'
            '各項目下の 1) 2) 3) でカテゴリ変更、削除・復元も可能です。'
        ),
        'parse_error': (
            'レシートを十分に読み取れませんでした。'
            '写真を撮り直すか、合計金額をテキストで送ってください（例: まいばすけっと 321円）。'
        ),
        'unsupported': (
            '申し訳ありません。現在は支出の記録のみ対応しています。'
            'レシート画像またはテキスト（例: ランチ 1200円）を送ってください。'
        ),
        'error': '応答を生成できませんでした。しばらくしてからもう一度お試しください。',
    },
    'en': {
        'header': 'Detected expense(s):',
        'logged_by': 'Logged by: {user_id}',
        'category_guess': 'Category (guess): {path}',
        'pick_another': 'Please confirm or pick another:',
        'instructions': (
            'Reply to this message to edit. '
            'Use item number + change (e.g. "2 3800" or "2 delete"), '
            'or 1) 2) 3) under each item for category. Delete/restore also supported.'
        ),
        'parse_error': (
            "I couldn't read this receipt clearly enough to log expenses. "
            'Please try a clearer photo, or send the total as text (e.g. My Basket 321 yen).'
        ),
        'unsupported': (
            'Sorry—I only accept expense submissions right now. '
            "Please send a receipt image or text like: 'Lunch 1200 yen'."
        ),
        'error': "Sorry, I couldn't generate a response right now. Please try again in a moment.",
    },
    'zh': {
        'header': '检测到的支出:',
        'logged_by': '记录者: {user_id}',
        'category_guess': '类别（推测）: {path}',
        'pick_another': '请确认或选择其他类别:',
        'instructions': (
            '回复此消息即可编辑。'
            '可用「项目编号 + 修改」（例: 2 3800円 / 2 取消），'
            '或每项下方的 1) 2) 3) 更改类别，也可删除/恢复。'
        ),
        'parse_error': (
            '无法清晰读取这张收据，无法记账。'
            '请重新拍照，或以文字发送合计金额（例: まいばすけっと 321円）。'
        ),
        'unsupported': (
            '抱歉，目前仅支持记录支出。'
            '请发送收据图片或文字（例: 午餐 1200円）。'
        ),
        'error': '暂时无法生成回复，请稍后再试。',
    },
}


def normalize_reply_language(code: Optional[str]) -> str:
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


def item_number_label(index: int) -> str:
    """1-based item index; emoji for 1–10, plain number after."""
    if 1 <= index <= len(ITEM_EMOJI):
        return ITEM_EMOJI[index - 1]
    return f'{index})'


def t(language: str, key: str, **kwargs: str) -> str:
    lang = normalize_reply_language(language)
    table = _STRINGS.get(lang, _STRINGS['ja'])
    text = table.get(key, _STRINGS['ja'].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text


def format_expense_confirmation(
    items: List[dict],
    *,
    language: str = 'ja',
    logged_by_line_user_id: Optional[str] = None,
    is_shared_tenant: bool = False,
) -> Optional[str]:
    if not items:
        return None

    lang = normalize_reply_language(language)
    lines: List[str] = [t(lang, 'header')]

    if is_shared_tenant and logged_by_line_user_id:
        lines.append(t(lang, 'logged_by', user_id=logged_by_line_user_id))

    has_category_block = any((item.get('category_alternative_paths') or []) for item in items)
    if has_category_block:
        lines.append(t(lang, 'instructions'))
        lines.append('')

    for index, item in enumerate(items, start=1):
        description = str(item.get('description', 'Expense')).strip()
        amount = item.get('amount', '')
        currency = item.get('currency', '')
        currency_text = f' {currency}' if currency else ''
        lines.append(f'{item_number_label(index)} {description}: {amount}{currency_text}')

        guess_path = item.get('category_guess_path')
        if guess_path:
            lines.append(f"  {t(lang, 'category_guess', path=guess_path)}")

        alt_paths = item.get('category_alternative_paths') or []
        if alt_paths:
            lines.append(f"  {t(lang, 'pick_another')}")
            for alt_index, alt_path in enumerate(alt_paths[:3], start=1):
                lines.append(f'  {alt_index}) {alt_path}')

    return '\n'.join(lines)
