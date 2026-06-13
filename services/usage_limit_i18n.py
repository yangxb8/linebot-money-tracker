"""Localized user-facing usage limit messages."""

from __future__ import annotations

from typing import Dict

from services.confirmation_i18n import normalize_reply_language

_STRINGS: Dict[str, Dict[str, str]] = {
    'ja': {
        'payload_too_large_text': 'テキストが長すぎます（上限 {max_words} 語）。短くして送り直してください。',
        'payload_too_large_image': '画像が大きすぎます（上限 {max_mb} MB）。小さな画像を送ってください。',
        'user_rate_limit_minute': '送信が速すぎます。少し待ってからもう一度お試しください。',
        'user_rate_limit_day': '本日の利用上限に達しました。明日またお試しください。',
        'user_quota_monthly': '今月のAI利用上限に達しました。来月までお待ちください。',
        'user_receipt_quota_monthly': '今月のレシート解析上限に達しました。来月までお待ちください。',
    },
    'en': {
        'payload_too_large_text': 'Your message is too long (limit {max_words} words). Please shorten it and try again.',
        'payload_too_large_image': 'Your image is too large (limit {max_mb} MB). Please send a smaller image.',
        'user_rate_limit_minute': 'You are sending messages too quickly. Please wait a moment and try again.',
        'user_rate_limit_day': 'You have reached today\'s usage limit. Please try again tomorrow.',
        'user_quota_monthly': 'You have reached this month\'s AI usage limit. Please try again next month.',
        'user_receipt_quota_monthly': 'You have reached this month\'s receipt analysis limit. Please try again next month.',
    },
    'zh': {
        'payload_too_large_text': '文字过长（上限 {max_words} 词）。请缩短后重试。',
        'payload_too_large_image': '图片过大（上限 {max_mb} MB）。请发送较小的图片。',
        'user_rate_limit_minute': '发送过快，请稍后再试。',
        'user_rate_limit_day': '已达到今日使用上限，请明天再试。',
        'user_quota_monthly': '已达到本月 AI 使用上限，请下月再试。',
        'user_receipt_quota_monthly': '已达到本月收据解析上限，请下月再试。',
    },
}


def usage_limit_message(language: str, key: str, **kwargs: str) -> str:
    lang = normalize_reply_language(language)
    table = _STRINGS.get(lang, _STRINGS['ja'])
    text = table.get(key, _STRINGS['ja'].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text
