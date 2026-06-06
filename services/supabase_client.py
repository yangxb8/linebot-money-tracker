import logging
import os
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

_client = None


def is_supabase_configured() -> bool:
    return bool(os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_SERVICE_ROLE_KEY'))


@lru_cache(maxsize=1)
def get_supabase_client():
    """Return a cached Supabase client using the service role key."""
    global _client
    if _client is not None:
        return _client

    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key:
        raise RuntimeError('SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set')

    from supabase import create_client

    _client = create_client(url, key)
    logger.debug('Supabase client initialized for %s', url)
    return _client


def reset_supabase_client_for_tests() -> None:
    """Clear cached client (tests only)."""
    global _client
    _client = None
    get_supabase_client.cache_clear()
