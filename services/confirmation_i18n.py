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
        'edit_error': '変更を保存できませんでした。{detail}',
        'edit_no_op': '変更はありませんでした。',
        'edit_no_op_restore': '復元する項目がありません（すでに有効な可能性があります）。',
        'delete_all_prompt': 'この確認の支出をすべて削除します。YES と返信して確定してください。',
        'delete_many': '{count} 件の支出を削除しました。',
        'delete_one': '削除しました：{label}',
        'restore_many': '{count} 件の支出を復元しました。',
        'restore_one': '復元しました：{label}',
        'update_header': '更新しました：{item}',
        'update_header_plain': '更新しました',
        'applied_generic': '変更を反映しました。',
        'unknown_confirmation': '編集するには、ボットの支出確認メッセージに返信してください。',
        'duplicate_reply': 'この返信はすでに処理済みです。',
        'bulk_category': '{count} 件の支出のカテゴリを更新しました：{category}',
        'intent_confirm_suffix': (
            '正しければ YES と返信してください。\n'
            '違う場合は、支出確認メッセージに再度返信して、より明確に書いてください。'
        ),
        'category_pick_header': 'カテゴリを選んでください（「{query}」）：',
        'category_pick_header_items': '第 {labels} 項目のカテゴリを選んでください（「{query}」）：',
        'category_pick_footer': '1〜3 で返信してカテゴリを選んでください。',
        'category_bulk_all': 'この確認のすべての支出のカテゴリを「{category_query}」に変更します。',
        'category_bulk_items': '第 {labels} 項目のカテゴリを「{category_query}」に変更します。',
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
        'edit_error': "Couldn't save your changes. {detail}",
        'edit_no_op': 'No changes were made.',
        'edit_no_op_restore': 'Nothing to restore — the expense may already be active.',
        'delete_all_prompt': 'This will soft-delete all expenses on this confirmation. Reply YES to confirm.',
        'delete_many': 'Soft-deleted {count} expense(s).',
        'delete_one': 'Soft-deleted: {label}',
        'restore_many': 'Restored {count} expense(s).',
        'restore_one': 'Restored: {label}',
        'update_header': 'Updated: {item}',
        'update_header_plain': 'Updated',
        'applied_generic': 'Changes applied.',
        'unknown_confirmation': 'Please reply to the bot expense confirmation message to make edits.',
        'duplicate_reply': 'This reply was already processed.',
        'bulk_category': 'Updated category for {count} expense(s) to: {category}',
        'intent_confirm_suffix': (
            'Reply YES if this is correct.\n'
            'If not, reply to the expense confirmation message again with a clearer description.'
        ),
        'category_pick_header': 'Pick a category ("{query}"):',
        'category_pick_header_items': 'Pick a category for item(s) {labels} ("{query}"):',
        'category_pick_footer': 'Reply with 1–3 to select a category.',
        'category_bulk_all': 'Change the category to "{category_query}" for all expenses on this confirmation.',
        'category_bulk_items': 'Change the category to "{category_query}" for item(s) {labels}.',
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
        'edit_error': '无法保存更改。{detail}',
        'edit_no_op': '没有进行任何更改。',
        'edit_no_op_restore': '没有可恢复的记录（可能已经是有效状态）。',
        'delete_all_prompt': '将软删除此确认中的所有支出。回复 YES 确认。',
        'delete_many': '已软删除 {count} 笔支出。',
        'delete_one': '已软删除：{label}',
        'restore_many': '已恢复 {count} 笔支出。',
        'restore_one': '已恢复：{label}',
        'update_header': '已更新：{item}',
        'update_header_plain': '已更新',
        'applied_generic': '已应用更改。',
        'unknown_confirmation': '请回复机器人发送的支出确认消息以进行编辑。',
        'duplicate_reply': '此回复已处理过。',
        'bulk_category': '已将 {count} 笔支出的类别更新为：{category}',
        'intent_confirm_suffix': (
            '如果理解正确，请回复 YES 确认。\n'
            '如果不正确，请重新回复支出确认消息并写得更清楚。'
        ),
        'category_pick_header': '请选择类别（「{query}」）：',
        'category_pick_header_items': '请为第 {labels} 项选择类别（「{query}」）：',
        'category_pick_footer': '请回复 1–3 选择类别。',
        'category_bulk_all': '将把此确认中所有支出的类别改为「{category_query}」。',
        'category_bulk_items': '将把第 {labels} 项支出的类别改为「{category_query}」。',
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
    from services.bot_persona import get_active_persona
    from services.persona_i18n import lookup_persona_string

    lang = normalize_reply_language(language)
    persona = get_active_persona()
    persona_text = lookup_persona_string(persona, lang, key)
    if persona_text is not None:
        text = persona_text
    else:
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
