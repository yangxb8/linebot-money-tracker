from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from services.bot_persona import (
    DEFAULT_PERSONA_PRESET,
    EMOJI_LEVEL_DEFAULT,
    PersonaConfig,
    normalize_persona_config,
)
from services.supabase_client import get_supabase_client, is_supabase_configured
from services.tenant_context import TenantContext

logger = logging.getLogger(__name__)

ALLOWED_REPLY_LANGUAGE_OVERRIDES = frozenset({'en', 'ja', 'zh'})


@dataclass(frozen=True)
class TenantBotSettings:
    persona: PersonaConfig
    reply_language: Optional[str] = None


def normalize_reply_language_override(value: object) -> Optional[str]:
    """Return en/ja/zh or None (Default / invalid → unset)."""
    if value is None:
        return None
    code = str(value).strip().lower()
    if not code:
        return None
    if code in ALLOWED_REPLY_LANGUAGE_OVERRIDES:
        return code
    return None


def fetch_tenant_bot_settings(tenant: TenantContext) -> TenantBotSettings:
    """Fetch tenant-scoped bot settings (fail-open).

    Tests run without Supabase config, so this must never raise.
    """
    default = TenantBotSettings(
        persona=normalize_persona_config(preset=None, custom_text=None, emoji_level=None),
        reply_language=None,
    )
    if not is_supabase_configured():
        return default

    try:
        client = get_supabase_client()
        response = (
            client.table('tenant_settings')
            .select(
                'bot_persona_preset,bot_persona_custom_text,bot_persona_emoji_level,reply_language'
            )
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        data = rows[0] if isinstance(rows, list) and rows else {}
        persona = normalize_persona_config(
            preset=data.get('bot_persona_preset'),
            custom_text=data.get('bot_persona_custom_text'),
            emoji_level=data.get('bot_persona_emoji_level'),
        )
        return TenantBotSettings(
            persona=persona,
            reply_language=normalize_reply_language_override(data.get('reply_language')),
        )
    except Exception:
        logger.exception('fetch_tenant_bot_settings failed; falling back to defaults')
        return default


def _persona_is_customized(persona: PersonaConfig) -> bool:
    if (persona.custom_text or '').strip():
        return True
    if persona.emoji_level != EMOJI_LEVEL_DEFAULT:
        return True
    if persona.preset != DEFAULT_PERSONA_PRESET:
        return True
    return False


def resolve_effective_bot_settings(tenant: Optional[TenantContext]) -> TenantBotSettings:
    """Resolve bot-behavior settings for outbound LINE copy.

    Ledger (group/personal) settings win when explicitly customized. In shared
    ledgers, unset fields fall back to the sender's personal bot-behavior page.
    """
    default = TenantBotSettings(
        persona=normalize_persona_config(preset=None, custom_text=None, emoji_level=None),
        reply_language=None,
    )
    if tenant is None:
        return default

    ledger = fetch_tenant_bot_settings(tenant)
    if not tenant.is_shared:
        return ledger

    personal = fetch_tenant_bot_settings(TenantContext.personal(tenant.logged_by_line_user_id))
    persona = personal.persona if not _persona_is_customized(ledger.persona) else ledger.persona
    return TenantBotSettings(
        persona=persona,
        reply_language=ledger.reply_language or personal.reply_language,
    )


def resolve_tenant_reply_language(
    tenant: Optional[TenantContext],
    base_language: str,
) -> str:
    """Apply tenant reply-language override when configured; else keep base."""
    override = resolve_effective_bot_settings(tenant).reply_language
    if override:
        return override
    return base_language
