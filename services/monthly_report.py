"""Monthly expense report orchestration (ask, tip, prepare, deliver)."""

from __future__ import annotations

import asyncio
import logging
import re
import tempfile
from pathlib import Path
from typing import Optional

from services.bot_persona import resolve_persona_for_tenant
from services.confirmation_i18n import t
from services.gemini_client import GeminiClient
from services.message_context import BotReply, MessageContext, ReportImagePayload
from services.monthly_report_insights import generate_insight_text
from services.monthly_report_period import (
    PeriodResolveError,
    ReportPeriod,
    current_period,
    fetch_fiscal_start_day,
    resolve_report_period,
    today_jst,
)
from services.monthly_report_render import render_report_png
from services.monthly_report_repository import (
    ArtifactRecord,
    compute_data_fingerprint,
    compute_style_fingerprint,
    get_artifact,
    mark_failed,
    mark_ready,
    mark_tip_shown,
    signed_urls_for_artifact,
    tip_already_shown,
    upsert_preparing,
)
from services.monthly_report_snapshot import build_budget_snapshot
from services.tenant_context import TenantContext

logger = logging.getLogger(__name__)

SAME_TURN_BUDGET_SECONDS = 8.0

_REPORT_PHRASE_RE = re.compile(
    r'('
    r'monthly\s+report|budget\s+report|expense\s+report|spending\s+report|'
    r'show\s+(?:my\s+)?(?:monthly\s+)?report|'
    r'(?:家計|月次|月間)?レポート|まとめを?(?:見せて|ください)?|'
    r'先月のまとめ|今月のレポート|支出レポート|予算レポート|'
    r'月报|月報|报表|報告'
    r')',
    re.IGNORECASE,
)


def looks_like_monthly_report_intent(text: Optional[str]) -> bool:
    if not text or not isinstance(text, str):
        return False
    normalized = text.strip()
    if not normalized:
        return False
    return bool(_REPORT_PHRASE_RE.search(normalized))


def maybe_new_period_tip(tenant: TenantContext, language: str = 'ja') -> Optional[str]:
    """Text-only tip once per conversation after fiscal rollover. Does not start prepare."""
    as_of = today_jst()
    fiscal_start_day = fetch_fiscal_start_day(tenant)
    current_start, _ = current_period(as_of, fiscal_start_day)
    if tip_already_shown(tenant, current_start):
        return None
    # Only tip once we are past the first day of... actually tip on first message of new period
    # Always tip if not shown for this current period (conversation just entered this period).
    mark_tip_shown(tenant, current_start)
    logger.info(
        'monthly_report tip shown tenant=%s:%s period=%s',
        tenant.tenant_type,
        tenant.tenant_id,
        current_start.isoformat(),
    )
    return t(language, 'monthly_report_tip')


async def handle_monthly_report_ask(
    text: str,
    gemini: GeminiClient,
    context: Optional[MessageContext],
) -> BotReply:
    language = context.reply_language if context else 'ja'
    if context is None:
        return BotReply(text=t(language, 'monthly_report_failed'))

    tenant = context.tenant
    resolved = resolve_report_period(tenant, text, language=language)
    if isinstance(resolved, PeriodResolveError):
        key = 'monthly_report_future' if resolved.code == 'future' else 'monthly_report_failed'
        return BotReply(text=t(language, key))

    persona = resolve_persona_for_tenant(tenant)
    data_fp = compute_data_fingerprint(tenant, resolved)
    style_fp = compute_style_fingerprint(
        language=language,
        persona_preset=persona.preset,
        emoji_level=persona.emoji_level,
        custom_text=persona.custom_text or '',
    )

    existing = get_artifact(tenant, resolved.period_start)
    if (
        existing
        and existing.status == 'ready'
        and existing.data_fingerprint == data_fp
        and existing.style_fingerprint == style_fp
    ):
        return _delivery_reply(language, resolved, existing)

    if existing and existing.status == 'preparing':
        # Still running from a prior ask
        return BotReply(text=t(language, 'monthly_report_in_progress'))

    artifact = upsert_preparing(
        tenant,
        resolved,
        data_fingerprint=data_fp,
        style_fingerprint=style_fp,
    )
    logger.info(
        'monthly_report prepare start id=%s period=%s',
        artifact.id,
        resolved.period_start.isoformat(),
    )

    prepare_task = asyncio.create_task(
        _prepare_artifact(
            tenant=tenant,
            period=resolved,
            artifact_id=artifact.id,
            data_fp=data_fp,
            style_fp=style_fp,
            language=language,
            gemini=gemini,
        )
    )

    try:
        ready = await asyncio.wait_for(asyncio.shield(prepare_task), timeout=SAME_TURN_BUDGET_SECONDS)
        return _delivery_reply(language, resolved, ready)
    except asyncio.TimeoutError:
        logger.info('monthly_report same-turn timeout; ask-again path id=%s', artifact.id)
        return BotReply(text=t(language, 'monthly_report_preparing'))
    except Exception:
        logger.exception('monthly_report prepare failed')
        mark_failed(
            tenant,
            resolved,
            artifact_id=artifact.id,
            data_fingerprint=data_fp,
            style_fingerprint=style_fp,
            error_code='prepare_failed',
        )
        return BotReply(text=t(language, 'monthly_report_failed'))


async def _prepare_artifact(
    *,
    tenant: TenantContext,
    period: ReportPeriod,
    artifact_id: str,
    data_fp: str,
    style_fp: str,
    language: str,
    gemini: GeminiClient,
) -> ArtifactRecord:
    try:
        snapshot = build_budget_snapshot(tenant, period)
        insight = await generate_insight_text(language, snapshot, period.label, gemini)
        title = t(language, 'monthly_report_title')
        png = render_report_png(
            snapshot=snapshot,
            insight_text=insight,
            period_label=period.label,
            title=title,
        )
        ready = mark_ready(
            tenant,
            period,
            artifact_id=artifact_id,
            data_fingerprint=data_fp,
            style_fingerprint=style_fp,
            insight_text=insight,
            snapshot_json=snapshot,
            png_bytes=png,
        )
        logger.info('monthly_report prepare ready id=%s', artifact_id)
        return ready
    except Exception:
        logger.exception('monthly_report prepare error id=%s', artifact_id)
        return mark_failed(
            tenant,
            period,
            artifact_id=artifact_id,
            data_fingerprint=data_fp,
            style_fingerprint=style_fp,
            error_code='prepare_failed',
        )


def _delivery_reply(language: str, period: ReportPeriod, artifact: ArtifactRecord) -> BotReply:
    if artifact.status != 'ready':
        if artifact.status == 'preparing':
            return BotReply(text=t(language, 'monthly_report_in_progress'))
        return BotReply(text=t(language, 'monthly_report_failed'))

    original, preview, png = signed_urls_for_artifact(artifact)
    caption = t(language, 'monthly_report_caption', period=period.label)
    local_path = None
    if png:
        tmp = Path(tempfile.gettempdir()) / f'monthly-report-{artifact.id}.png'
        tmp.write_bytes(png)
        local_path = str(tmp)

    # Harness / offline: deliver with local bytes even without public URL
    if not original and png:
        return BotReply(
            text=caption,
            image=ReportImagePayload(
                original_url='',
                preview_url='',
                local_path=local_path,
                png_bytes=png,
            ),
        )

    if not original:
        return BotReply(text=t(language, 'monthly_report_failed'))

    return BotReply(
        text=caption,
        image=ReportImagePayload(
            original_url=original,
            preview_url=preview or original,
            local_path=local_path,
            png_bytes=png,
        ),
    )
