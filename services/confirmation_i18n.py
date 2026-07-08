"""Localized strings for expense confirmation replies."""

from __future__ import annotations

from typing import Dict, List, Optional

from services.reply_composer import compose_confirmation_reply

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
        'total': '合計: {amount}{currency}',
        'logged_by': '記録者: {name}',
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
        'retry_not_found': (
            'このメッセージから再試行できません。'
            'エラーメッセージに返信して「もう一度」と送ってください。'
        ),
        'retry_expired': (
            '元のメッセージの保存期限が切れました。'
            'もう一度レシートまたは金額を送ってください。'
        ),
        'retry_image_expired': (
            '元の画像を取得できませんでした。'
            'もう一度レシート写真を送ってください。'
        ),
        'usage_limit': (
            'AIの利用上限に達したため、レシート画像の解析ができません。'
            'しばらくしてから再度お試しいただくか、合計金額をテキストで送ってください。'
        ),
        'webapp_link': '家計簿のWebページはこちらです:\n{url}',
        'webapp_unavailable': (
            '家計簿のWebページは現在ご利用いただけません。'
            'しばらくしてからもう一度お試しください。'
        ),
        'help_edit': (
            '支出確認メッセージに返信して編集できます。'
            '例: 「3800円」「取消」「食料品」。'
            'カテゴリが曖昧な場合は推測結果を表示するので YES で確定してください。'
        ),
    },
    'en': {
        'header': 'Detected expense(s):',
        'total': 'Total: {amount}{currency}',
        'logged_by': 'Logged by: {name}',
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
        'retry_not_found': (
            "I can't retry from this message. "
            'Reply to the error message with "retry" or "try again".'
        ),
        'retry_expired': (
            'The original message is no longer available. '
            'Please send the receipt or amount again.'
        ),
        'retry_image_expired': (
            "I couldn't fetch the original image. Please send the receipt photo again."
        ),
        'usage_limit': (
            "I can't analyze receipt images right now because the AI usage limit has been reached. "
            'Please try again later, or send the total as text.'
        ),
        'webapp_link': 'Open your expense dashboard here:\n{url}',
        'webapp_unavailable': (
            'The expense dashboard is not available right now. Please try again later.'
        ),
        'help_edit': (
            'Reply to the expense confirmation message to edit. '
            'Examples: "3800", "delete", or "Groceries". '
            'If I guess the category, reply YES to confirm.'
        ),
    },
    'zh': {
        'header': '检测到的支出:',
        'total': '合计: {amount}{currency}',
        'logged_by': '记录者: {name}',
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
        'retry_not_found': (
            '无法从此消息重试。请回复错误消息并发送「重试」。'
        ),
        'retry_expired': (
            '原始消息已过期，请重新发送收据或金额。'
        ),
        'retry_image_expired': (
            '无法获取原始图片，请重新发送收据照片。'
        ),
        'usage_limit': (
            'AI 使用额度已达上限，暂时无法解析收据图片。'
            '请稍后再试，或以文字发送合计金额。'
        ),
        'webapp_link': '请在此打开家计簿网页:\n{url}',
        'webapp_unavailable': (
            '家计簿网页暂时无法使用，请稍后再试。'
        ),
        'help_edit': (
            '回复支出确认消息即可编辑。'
            '例: 「3800円」「删除」「食料品」。'
            '若类别不确定，我会给出推测结果，请回复 YES 确认。'
        ),
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
    logged_by_display_name: Optional[str] = None,
    is_shared_tenant: bool = False,
    show_item_details: bool = False,
) -> Optional[str]:
    lang = normalize_reply_language(language)
    logged_by_line: Optional[str] = None
    if is_shared_tenant and logged_by_line_user_id:
        name = (logged_by_display_name or '').strip() or logged_by_line_user_id
        logged_by_line = t(lang, 'logged_by', name=name)

    return compose_confirmation_reply(
        items,
        language=language,
        show_item_details=show_item_details,
        logged_by_line=logged_by_line,
    )
