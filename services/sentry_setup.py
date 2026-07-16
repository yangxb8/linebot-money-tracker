"""Optional Sentry initialization for webhook / Cloud Run and console harness."""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def init_sentry(*, environment: Optional[str] = None) -> bool:
    """Initialize Sentry when ``SENTRY_DSN`` is set.

    Sends stdlib logging records (DEBUG and above) to Sentry Logs, keeps ERROR+
    as issue events, and enables the FastAPI/Starlette integrations when present.

    Returns True when the SDK was initialized.
    """
    dsn = (os.getenv('SENTRY_DSN') or '').strip()
    if not dsn:
        return False

    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    env = (environment or os.getenv('SENTRY_ENVIRONMENT') or os.getenv('ENV') or '').strip()
    traces_sample_rate = _float_env('SENTRY_TRACES_SAMPLE_RATE', 0.0)

    sentry_sdk.init(
        dsn=dsn,
        environment=env or None,
        enable_logs=True,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
        integrations=[
            LoggingIntegration(
                level=logging.DEBUG,
                event_level=logging.ERROR,
                sentry_logs_level=logging.DEBUG,
            ),
        ],
    )
    logger.info(
        'Sentry initialized (environment=%s traces_sample_rate=%s)',
        env or 'default',
        traces_sample_rate,
    )
    return True


def _float_env(name: str, default: float) -> float:
    raw = (os.getenv(name) or '').strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        logger.warning('Invalid %s=%r; using default %s', name, raw, default)
        return default
    return max(0.0, min(1.0, value))
