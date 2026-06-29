"""Detect when a user asks for the expense dashboard / web app link."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

from services.confirmation_i18n import t
from services.gemini_client import GeminiClient
from services.log_utils import truncate
from services.usage_metering import llm_operation_scope

logger = logging.getLogger(__name__)

WEBAPP_INTENT_PROMPT = """You judge whether a LINE chat message is the user asking for the expense dashboard, web app, or webpage to view their logged expenses online.
Accept: requests to open the dashboard, website, web app, view expenses online, asking for the link/URL, where to see their expenses on the web.
Accept examples: "open dashboard", "where is the website?", "家計簿のページ", "网页在哪".
Reject: expense logging (amounts, receipts, spending notes), greetings, chitchat, general knowledge questions.
When unsure, prefer false — this check runs only after the message was already judged not to be an expense log.
Reply ONLY with JSON: {{"is_webapp_request": true}} or {{"is_webapp_request": false}}

Message:
{text}"""

_WEBAPP_SHORTCUT_RE = re.compile(
    r'^(?:'
    r'(?:open|show|go\s+to|where\s+is|link\s+to|url\s+(?:for|to))?\s*'
    r'(?:the\s+)?(?:web\s*(?:app|page|site)|dashboard|website|expense\s+page)'
    r'|'
    r'家計簿(?:の)?(?:ページ|サイト|アプリ)?'
    r'|'
    r'(?:ウェブ|web)(?:ページ|サイト|アプリ)?'
    r'|'
    r'ダッシュボード'
    r'|'
    r'(?:网页|网站|網頁|儀表板)'
    r')\s*[?.!。！？?]*$',
    re.IGNORECASE,
)


def is_webapp_request_obvious(text: Optional[str]) -> bool:
    """Fast path for clear dashboard / webpage requests without an LLM call."""
    if not text or not isinstance(text, str):
        return False
    normalized = text.strip()
    if not normalized:
        return False
    return bool(_WEBAPP_SHORTCUT_RE.match(normalized))


def _parse_webapp_intent_response(response: str, source: str = 'unknown') -> bool:
    text = response.strip()
    if not text:
        logger.warning('Webapp intent check (%s): empty LLM response', source)
        return False

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            is_request = bool(data.get('is_webapp_request', False))
            logger.info(
                'Webapp intent check (%s): is_webapp_request=%s (parsed JSON)',
                source,
                is_request,
            )
            return is_request
    except json.JSONDecodeError:
        logger.debug('Webapp intent check (%s): response is not JSON, trying fallback parse', source)

    lowered = text.lower()
    if '"is_webapp_request": true' in lowered or '"is_webapp_request":true' in lowered:
        logger.info('Webapp intent check (%s): is_webapp_request=True (fallback string match)', source)
        return True
    if '"is_webapp_request": false' in lowered or '"is_webapp_request":false' in lowered:
        logger.info('Webapp intent check (%s): is_webapp_request=False (fallback string match)', source)
        return False

    logger.warning(
        'Webapp intent check (%s): could not parse response: %s',
        source,
        truncate(text, 200),
    )
    return False


def dashboard_url() -> Optional[str]:
    url = (os.getenv('DASHBOARD_LIFF_URL') or '').strip()
    return url or None


def webapp_link_reply(language: str = 'ja') -> str:
    url = dashboard_url()
    if not url:
        return t(language, 'webapp_unavailable')
    return t(language, 'webapp_link', url=url)


async def is_webapp_intent_text(text: Optional[str], gemini: GeminiClient) -> bool:
    """Use shortcuts and the LLM to judge whether the user wants the dashboard link."""
    if not text or not isinstance(text, str):
        logger.info('Webapp intent check (text): skipped (empty or invalid input)')
        return False

    normalized = text.strip()
    if not normalized:
        logger.info('Webapp intent check (text): skipped (blank after strip)')
        return False

    if is_webapp_request_obvious(normalized):
        logger.info('Webapp intent check (text): obvious request (shortcut match)')
        return True

    logger.info('Webapp intent check (text): classifying message len=%d', len(normalized))
    logger.debug('Webapp intent check (text): message=%s', truncate(normalized, 500))
    prompt = WEBAPP_INTENT_PROMPT.format(text=normalized)
    with llm_operation_scope('intent'):
        response = await gemini.generate_reply(prompt)
    return _parse_webapp_intent_response(response, source='text')
