"""Persisted user reply language (LINE profile + explicit overrides)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from services.confirmation_i18n import normalize_reply_language
from services.supabase_client import get_supabase_client, is_supabase_configured

logger = logging.getLogger(__name__)

SOURCE_DEFAULT = 'default'
SOURCE_LINE_PROFILE = 'line_profile'
SOURCE_USER_REQUEST = 'user_request'

_EXPLICIT_LANGUAGE_RE = re.compile(
    r'(?:'
    r'英語で|日本語で|中国語で|中文回复|用中文|'
    r'reply\s+in\s+english|use\s+english|in\s+english|'
    r'reply\s+in\s+chinese|use\s+chinese|in\s+chinese|'
    r'reply\s+in\s+japanese|use\s+japanese|in\s+japanese|'
    r'日本語で返信|英語で返信|中文回复'
    r')',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UserLanguagePreference:
    reply_language: str
    source: str


def parse_explicit_language_request(text: str) -> Optional[str]:
    if not text or not text.strip():
        return None
    normalized = text.strip()
    if not _EXPLICIT_LANGUAGE_RE.search(normalized):
        return None
    lowered = normalized.lower()
    if any(token in lowered for token in ('english', '英語')):
        return 'en'
    if any(token in lowered for token in ('chinese', '中文', '中国語')):
        return 'zh'
    if any(token in lowered for token in ('japanese', '日本語')):
        return 'ja'
    return None


def get_user_language_preference(line_user_id: str) -> UserLanguagePreference:
    if not is_supabase_configured() or not line_user_id:
        return UserLanguagePreference(reply_language='ja', source=SOURCE_DEFAULT)

    try:
        client = get_supabase_client()
        response = (
            client.table('user_language_preferences')
            .select('reply_language, source')
            .eq('line_user_id', line_user_id)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return UserLanguagePreference(reply_language='ja', source=SOURCE_DEFAULT)
        row = rows[0]
        return UserLanguagePreference(
            reply_language=normalize_reply_language(row.get('reply_language')),
            source=str(row.get('source') or SOURCE_DEFAULT),
        )
    except Exception:
        logger.exception('get_user_language_preference failed')
        return UserLanguagePreference(reply_language='ja', source=SOURCE_DEFAULT)


def save_user_language_preference(
    line_user_id: str,
    reply_language: str,
    *,
    source: str,
    line_profile_language: Optional[str] = None,
) -> None:
    if not is_supabase_configured() or not line_user_id:
        return

    lang = normalize_reply_language(reply_language)
    try:
        client = get_supabase_client()
        client.table('user_language_preferences').upsert(
            {
                'line_user_id': line_user_id,
                'reply_language': lang,
                'source': source,
                'line_profile_language': line_profile_language,
                'updated_at': datetime.now(timezone.utc).isoformat(),
            },
            on_conflict='line_user_id',
        ).execute()
        logger.info(
            'Saved language preference user=%s lang=%s source=%s',
            line_user_id,
            lang,
            source,
        )
    except Exception:
        logger.exception('save_user_language_preference failed')


def maybe_update_from_line_profile(line_user_id: str, line_profile_language: Optional[str]) -> str:
    """Store LINE profile language on first sight; never overwrite user_request."""
    current = get_user_language_preference(line_user_id)
    if current.source == SOURCE_USER_REQUEST:
        return current.reply_language

    mapped = normalize_reply_language(line_profile_language)
    if current.source == SOURCE_DEFAULT:
        save_user_language_preference(
            line_user_id,
            mapped,
            source=SOURCE_LINE_PROFILE,
            line_profile_language=line_profile_language,
        )
        return mapped

    if current.source == SOURCE_LINE_PROFILE and line_profile_language:
        save_user_language_preference(
            line_user_id,
            mapped,
            source=SOURCE_LINE_PROFILE,
            line_profile_language=line_profile_language,
        )
        return mapped

    return current.reply_language


def maybe_update_from_user_message(line_user_id: str, text: str) -> Optional[str]:
    requested = parse_explicit_language_request(text)
    if requested is None:
        return None
    save_user_language_preference(line_user_id, requested, source=SOURCE_USER_REQUEST)
    return requested


def resolve_reply_language(line_user_id: Optional[str], text: Optional[str] = None) -> str:
    if line_user_id and text:
        explicit = maybe_update_from_user_message(line_user_id, text)
        if explicit:
            return explicit
    if line_user_id:
        return get_user_language_preference(line_user_id).reply_language
    if text:
        from services.reply_summary import detect_reply_language

        return detect_reply_language(text)
    return 'ja'
