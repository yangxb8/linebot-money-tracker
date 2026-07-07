"""Persona-specific predefined reply strings (v1: Judy Hopps-inspired)."""

from __future__ import annotations

from typing import Dict, Optional

from services.bot_persona import DEFAULT_PERSONA_PRESET, PersonaConfig
from services.confirmation_i18n import normalize_reply_language

# Keys align with confirmation_i18n + reply_summary + usage_limit message ids.
JUDY_HOPPS_STRINGS: Dict[str, Dict[str, str]] = {
    'ja': {
        'header': '🐰✨ 見つけた支出だよ！',
        'total': '合計: {amount}{currency}',
        'logged_by': '記録者: {name}',
        'category_guess': 'カテゴリ（推測）: {path}',
        'pick_another': '合ってるかな？違ったらここから選んでね:',
        'instructions': (
            'このメッセージに返信して編集できるよ！\n'
            '項目番号＋変更（例: 2 3800円 / 2 取消）、'
            '各項目下の 1) 2) 3) でカテゴリ変更、削除・復元もOKだよ。'
        ),
        'parse_error': (
            '🐰 うわっ、ちょっと読み取れなかったかも！\n'
            'もう一度はっきり撮ってみて？それか合計をテキストで送ってね（例: まいばすけっと 321円）✨'
        ),
        'unsupported': (
            '🐰 ごめんね、今は支出の記録だけお手伝いできるんだ！\n'
            'レシートか「ランチ 1200円」みたいに送ってね ✨'
        ),
        'error': '🐰 ごめん、うまく返せなかった…。少し待ってからもう一度試してね！',
        'retry_not_found': (
            '🐰 このメッセージからは再試行できないよ。\n'
            'エラーメッセージに返信して「もう一度」と送ってね。'
        ),
        'retry_expired': (
            '🐰 元のメッセージの保存期限が切れちゃった。\n'
            'もう一度レシートまたは金額を送ってね！'
        ),
        'retry_image_expired': (
            '🐰 元の画像を取得できなかった…。\n'
            'もう一度レシート写真を送ってね！'
        ),
        'usage_limit': (
            '🐰 AIの利用上限に達しちゃったから、レシート画像は今解析できないよ。\n'
            '少し待つか、合計金額をテキストで送ってね ✨'
        ),
        'webapp_link': '🐰 家計簿のWebページはここだよ！\n{url} ✨',
        'webapp_unavailable': (
            '🐰 今は家計簿のWebページが使えないみたい…。\n'
            '少し待ってからもう一度試してね！'
        ),
        'edit_error': '変更を保存できなかったよ。{detail}',
        'edit_no_op': '変更はなかったよ。',
        'edit_no_op_restore': '復元する項目がないみたい（すでに有効かも）。',
        'delete_all_prompt': 'この確認の支出をすべて削除するよ。YES と返信して確定してね。',
        'delete_many': '{count} 件の支出を削除したよ。',
        'delete_one': '削除したよ：{label}',
        'restore_many': '{count} 件の支出を復元したよ。',
        'restore_one': '復元したよ：{label}',
        'update_header': '更新したよ：{item}',
        'update_header_plain': '更新したよ。',
        'applied_generic': '変更を反映したよ！✨',
        'unknown_confirmation': '編集するには、ボットの支出確認メッセージに返信してね。',
        'duplicate_reply': 'この返信はもう処理済みだよ。',
        'bulk_category': '{count} 件のカテゴリを更新したよ：{category}',
        'intent_confirm_suffix': (
            '正しければ YES と返信してね。\n'
            '違う場合は、支出確認メッセージにもう一度返信して、はっきり書いてね。'
        ),
        'category_pick_header': 'カテゴリを選んでね（「{query}」）：',
        'category_pick_header_items': '第 {labels} 項目のカテゴリを選んでね（「{query}」）：',
        'category_pick_footer': '1〜3 で返信してカテゴリを選んでね。',
        'category_bulk_all': 'この確認のすべての支出のカテゴリを「{category_query}」に変えるよ！',
        'category_bulk_items': '第 {labels} 項目のカテゴリを「{category_query}」に変えるね。',
        'usage_payload_text': 'テキストが長すぎるよ（上限 {max_words} 語）。短くして送り直してね。',
        'usage_payload_image': '画像が大きすぎるよ（上限 {max_mb} MB）。小さめの画像を送ってね。',
        'usage_rate_minute': '送りすぎだよ！少し待ってからもう一度試してね。',
        'usage_rate_day': '今日の利用上限に達しちゃった。明日また試してね。',
        'usage_quota_monthly': '今月のAI利用上限に達したよ。来月まで待ってね。',
        'usage_receipt_quota_monthly': '今月のレシート解析上限に達したよ。来月まで待ってね。',
    },
    'en': {
        'header': '🐰✨ Expenses I spotted:',
        'total': 'Total: {amount}{currency}',
        'logged_by': 'Logged by: {name}',
        'category_guess': 'Category (guess): {path}',
        'pick_another': 'Does this look right? Pick another if not:',
        'instructions': (
            'Reply to this message to edit.\n'
            'Use item number + change (e.g. "2 3800" or "2 delete"), '
            'or 1) 2) 3) under each item for category. Delete/restore works too!'
        ),
        'parse_error': (
            "🐰 Hmm, I couldn't read this receipt clearly enough.\n"
            'Try a clearer photo, or send the total as text (e.g. My Basket 321 yen) ✨'
        ),
        'unsupported': (
            "🐰 Sorry—I can only help log expenses right now.\n"
            "Send a receipt image or text like 'Lunch 1200 yen' ✨"
        ),
        'error': "🐰 Sorry, I couldn't reply just now. Try again in a moment!",
        'retry_not_found': (
            "🐰 I can't retry from this message.\n"
            'Reply to the error message with "retry" or "try again".'
        ),
        'retry_expired': (
            "🐰 The original message isn't available anymore.\n"
            'Please send the receipt or amount again.'
        ),
        'retry_image_expired': (
            "🐰 I couldn't fetch the original image.\n"
            'Please send the receipt photo again.'
        ),
        'usage_limit': (
            "🐰 I've hit the AI usage limit, so I can't analyze receipt images right now.\n"
            'Try again later, or send the total as text ✨'
        ),
        'webapp_link': '🐰 Open your expense dashboard here:\n{url} ✨',
        'webapp_unavailable': (
            "🐰 The expense dashboard isn't available right now.\n"
            'Please try again later.'
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
        'update_header_plain': 'Updated.',
        'applied_generic': 'Changes applied! ✨',
        'unknown_confirmation': 'Reply to the bot expense confirmation message to make edits.',
        'duplicate_reply': 'This reply was already processed.',
        'bulk_category': 'Updated category for {count} expense(s) to: {category}',
        'intent_confirm_suffix': (
            'Reply YES if this is correct.\n'
            'If not, reply to the expense confirmation again with a clearer description.'
        ),
        'category_pick_header': 'Pick a category ("{query}"):',
        'category_pick_header_items': 'Pick a category for item(s) {labels} ("{query}"):',
        'category_pick_footer': 'Reply with 1–3 to select a category.',
        'category_bulk_all': 'Change the category to "{category_query}" for all expenses on this confirmation.',
        'category_bulk_items': 'Change the category to "{category_query}" for item(s) {labels}.',
        'usage_payload_text': 'Your message is too long (limit {max_words} words). Please shorten it.',
        'usage_payload_image': 'Your image is too large (limit {max_mb} MB). Please send a smaller one.',
        'usage_rate_minute': 'You are sending messages too quickly. Please wait a moment.',
        'usage_rate_day': "You've reached today's usage limit. Try again tomorrow.",
        'usage_quota_monthly': "You've reached this month's AI usage limit. Try again next month.",
        'usage_receipt_quota_monthly': "You've reached this month's receipt analysis limit. Try again next month.",
    },
    'zh': {
        'header': '🐰✨ 检测到的支出:',
        'total': '合计: {amount}{currency}',
        'logged_by': '记录者: {name}',
        'category_guess': '类别（推测）: {path}',
        'pick_another': '对吗？不对的话从这里选:',
        'instructions': (
            '回复此消息即可编辑。\n'
            '可用「项目编号 + 修改」（例: 2 3800円 / 2 取消），'
            '或每项下方的 1) 2) 3) 更改类别，也可删除/恢复。'
        ),
        'parse_error': (
            '🐰 唔，这张收据我看不太清楚…\n'
            '请重新拍照，或以文字发送合计金额（例: まいばすけっと 321円）✨'
        ),
        'unsupported': (
            '🐰 抱歉，目前只能帮你记录支出哦。\n'
            '请发送收据图片或文字（例: 午餐 1200円）✨'
        ),
        'error': '🐰 抱歉，暂时无法回复。请稍后再试！',
        'retry_not_found': (
            '🐰 无法从此消息重试。\n'
            '请回复错误消息并发送「重试」。'
        ),
        'retry_expired': '🐰 原始消息已过期，请重新发送收据或金额。',
        'retry_image_expired': '🐰 无法获取原始图片，请重新发送收据照片。',
        'usage_limit': (
            '🐰 AI 使用额度已达上限，暂时无法解析收据图片。\n'
            '请稍后再试，或以文字发送合计金额 ✨'
        ),
        'webapp_link': '🐰 请在此打开家计簿网页:\n{url} ✨',
        'webapp_unavailable': '🐰 家计簿网页暂时无法使用，请稍后再试。',
        'edit_error': '无法保存更改。{detail}',
        'edit_no_op': '没有进行任何更改。',
        'edit_no_op_restore': '没有可恢复的记录（可能已经是有效状态）。',
        'delete_all_prompt': '将软删除此确认中的所有支出。回复 YES 确认。',
        'delete_many': '已软删除 {count} 笔支出。',
        'delete_one': '已软删除：{label}',
        'restore_many': '已恢复 {count} 笔支出。',
        'restore_one': '已恢复：{label}',
        'update_header': '已更新：{item}',
        'update_header_plain': '已更新。',
        'applied_generic': '已应用更改！✨',
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
        'usage_payload_text': '文字过长（上限 {max_words} 词）。请缩短后重试。',
        'usage_payload_image': '图片过大（上限 {max_mb} MB）。请发送较小的图片。',
        'usage_rate_minute': '发送过快，请稍后再试。',
        'usage_rate_day': '已达到今日使用上限，请明天再试。',
        'usage_quota_monthly': '已达到本月 AI 使用上限，请下月再试。',
        'usage_receipt_quota_monthly': '已达到本月收据解析上限，请下月再试。',
    },
}

_PRESET_TABLES = {
    DEFAULT_PERSONA_PRESET: JUDY_HOPPS_STRINGS,
}


def lookup_persona_string(
    persona: PersonaConfig,
    language: str,
    key: str,
) -> Optional[str]:
    table = _PRESET_TABLES.get(persona.preset)
    if not table:
        return None
    lang = normalize_reply_language(language)
    return table.get(lang, {}).get(key) or table.get('ja', {}).get(key)
