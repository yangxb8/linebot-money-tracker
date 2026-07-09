"""Tenant-scoped confirmation display preferences."""

from __future__ import annotations

import logging
from typing import Optional

from services.supabase_client import get_supabase_client, is_supabase_configured
from services.tenant_context import TenantContext

logger = logging.getLogger(__name__)


def confirmation_show_item_details(tenant: Optional[TenantContext]) -> bool:
    """Return whether confirmations should include per-item detail lines."""
    if tenant is None or not is_supabase_configured():
        return False

    try:
        client = get_supabase_client()
        response = (
            client.table('tenant_settings')
            .select('confirmation_show_item_details')
            .eq('tenant_type', tenant.tenant_type)
            .eq('tenant_id', tenant.tenant_id)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return False
        value = rows[0].get('confirmation_show_item_details')
        return bool(value)
    except Exception:
        logger.warning('confirmation_show_item_details lookup failed; defaulting to false', exc_info=True)
        return False
