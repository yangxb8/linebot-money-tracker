"""Detect and respond to how-to questions about expense reply-edits."""

from __future__ import annotations

import re
from typing import Optional

from services.confirmation_i18n import t

_HELP_RE = re.compile(
    r'(?:'
    r'how\s+(?:do\s+i|can\s+i|to)\s+(?:edit|change|update|delete|remove|restore|fix|correct)'
    r'|how\s+(?:do\s+i|can\s+i)\s+(?:change|update|set)\s+(?:the\s+)?category'
    r'|(?:what|where)\s+(?:can|do)\s+i\s+(?:edit|change|delete|fix)'
    r'|(?:edit|change|delete|restore)\s+(?:an?\s+)?expense'
    r'|(?:どう|どのように)(?:やって|すれば|したら|変更|編集|削除|直)'
    r'|(?:編集|変更|削除|取消|直し)(?:の)?(?:方法|やり方|仕方)'
    r'|(?:怎么|如何|怎样)(?:编辑|修改|更改|删除|改)'
    r')',
    re.IGNORECASE,
)


def is_help_request_obvious(text: Optional[str]) -> bool:
    if not text or not isinstance(text, str):
        return False
    normalized = text.strip()
    if not normalized:
        return False
    return bool(_HELP_RE.search(normalized))


def help_reply(language: str = 'ja') -> str:
    return t(language, 'help_edit')
