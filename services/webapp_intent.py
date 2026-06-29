"""Detect when a user asks for the expense dashboard / web app link."""

from __future__ import annotations

import os
import re
from typing import Optional

from services.confirmation_i18n import t

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


def dashboard_url() -> Optional[str]:
    url = (os.getenv('DASHBOARD_LIFF_URL') or '').strip()
    return url or None


def webapp_link_reply(language: str = 'ja') -> str:
    url = dashboard_url()
    if not url:
        return t(language, 'webapp_unavailable')
    return t(language, 'webapp_link', url=url)
