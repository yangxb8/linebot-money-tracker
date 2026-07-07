from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from services.bot_persona import PersonaConfig, normalize_persona_config
from services.supabase_client import get_supabase_client, is_supabase_configured
from services.tenant_context import TenantContext

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TenantBotSettings:
    persona: PersonaConfig


def fetch_tenant_bot_settings(tenant: TenantContext) -> TenantBotSettings:
    """Fetch tenant-scoped bot settings (fail-open).

    Tests run without Supabase config, so this must never raise.
    """
    if not is_supabase_configured():
        return TenantBotSettings(persona=normalize_persona_config(preset=None, custom_text=None, emoji_level=None))

    try:
        client = get_supabase_client()
        response = (
            client.table('tenant_settings')
            .select('bot_persona_preset,bot_persona_custom_text,bot_persona_emoji_level')
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
        return TenantBotSettings(persona=persona)
    except Exception:
        logger.exception('fetch_tenant_bot_settings failed; falling back to defaults')
        return TenantBotSettings(persona=normalize_persona_config(preset=None, custom_text=None, emoji_level=None))
